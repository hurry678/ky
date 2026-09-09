"""
创新点 1 的解释性主张检验：delta 幅值 vs 变换扰动尺度，是否预测脆弱性

主张：遗忘更新 δ = θ_unlearned − θ_implanted 的幅值相对于变换的扰动尺度，
      决定该变换是否会破坏遗忘。
  * 量化：δ 远小于量化 bin 宽度 → 舍入抹掉 δ（Forgetting That Sticks 对量化已给此机制，
    报告 47–828 倍；本脚本检验它是否也解释 GA/NPO 之间的差异）
  * 剪枝：δ 的质量若集中在会被剪掉的小幅值权重上 → 剪枝删掉抑制

已知的脆弱性真值（本项目 0.5B 实测）：
  GA  遗忘至 0.317 → 4-bit 0.950(+0.633) / 20% 剪枝 0.975 / 30% 剪枝 1.000  → 极脆
  NPO 遗忘至 0.000 → 4-bit 0.000 / 8-bit 0.000 / 20–30% 剪枝 0.000          → 稳

预测（先写下，不得事后调整）：
  P1  GA 的 median|δ| / 4bit_bin 应显著小于 NPO 的
  P2  GA 的 δ 质量落在"会被剪掉的权重"上的比例应显著高于 NPO
  若 P1 与 P2 均不成立 → 该解释性主张被否，创新点 1 退回填格子路线

用法: python delta_scale_analysis.py
"""
import json, os, sys, gc
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("HF_HOME", "D:/ky/_exp/hf_cache")

import torch, torch.nn as nn, numpy as np
from transformers import AutoModelForCausalLM

BASE = "D:/ky/_exp/q6v2/implanted"          # 植入后、遗忘前
UNLEARNED = {"GA": "D:/ky/_exp/q9/GA", "NPO": "D:/ky/_exp/q9/NPO"}
OUT = "D:/ky/_exp/delta"; os.makedirs(OUT, exist_ok=True)
SPARSITIES = (0.2, 0.3)
BITS = (8, 4)

# 真值（本项目实测）
FRAGILITY = {
    "GA":  {"dense": 0.317, "q8": 0.317, "q4": 0.950, "p0.2": 0.975, "p0.3": 1.000},
    "NPO": {"dense": 0.000, "q8": 0.000, "q4": 0.000, "p0.2": 0.000, "p0.3": 0.000},
}


def linear_weights(model):
    """跳过 lm_head 与 embedding，与量化/剪枝实验的跳过策略一致"""
    return {n: m.weight.data for n, m in model.named_modules()
            if isinstance(m, nn.Linear) and "lm_head" not in n}


@torch.no_grad()
def analyse(tag, path, base_w):
    m = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float32)
    uw = linear_weights(m)
    rows = []
    for name, W_u in uw.items():
        W_b = base_w[name]
        d = (W_u - W_b).abs().flatten()
        w = W_u.abs().flatten()
        if d.numel() == 0: continue
        rec = {"layer": name, "n": int(d.numel()),
               "med_d": float(d.median()), "mean_d": float(d.mean()),
               "l2_d": float(d.norm()), "med_w": float(w.median())}
        # 量化 bin 宽度：对称 per-output-channel RTN，s = max|W|/qmax
        for b in BITS:
            qmax = 2 ** (b - 1) - 1
            s = (W_u.abs().amax(dim=1, keepdim=True) / qmax).expand_as(W_u).flatten()
            rec[f"ratio_{b}bit"] = float((d / s.clamp(min=1e-12)).median())
        # 剪枝：δ 的质量有多少落在会被剪掉的权重上
        tot = float(d.sum())
        for p in SPARSITIES:
            k = max(int(w.numel() * p), 1)
            thr = w.float().kthvalue(k).values
            pruned = w <= thr
            rec[f"dmass_pruned_{p}"] = float(d[pruned].sum() / max(tot, 1e-12))
        rows.append(rec)
    del m; gc.collect()
    return rows


def agg(rows, key):
    v = np.array([r[key] for r in rows], dtype=float)
    return float(np.median(v)), float(v.mean())


def main():
    print("载入植入模型（遗忘前基准）...", flush=True)
    mb = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.float32)
    base_w = {k: v.clone() for k, v in linear_weights(mb).items()}
    del mb; gc.collect()
    print(f"线性层数 {len(base_w)}\n", flush=True)

    res = {}
    for tag, path in UNLEARNED.items():
        print(f"分析 {tag} ...", flush=True)
        rows = analyse(tag, path, base_w)
        s = {"n_layers": len(rows)}
        for k in ("med_d", "mean_d", "med_w", "ratio_8bit", "ratio_4bit",
                  "dmass_pruned_0.2", "dmass_pruned_0.3"):
            med, mean = agg(rows, k)
            s[k] = {"median_over_layers": med, "mean_over_layers": mean}
        res[tag] = {"summary": s, "per_layer": rows}
        json.dump(res, open(f"{OUT}/delta_analysis.json", "w"), indent=1)

    print("\n" + "=" * 78)
    print(f"{'量':<26}{'GA':>16}{'NPO':>16}{'NPO/GA':>12}")
    print("-" * 78)
    def line(label, key, fmt="{:.3e}"):
        g = res["GA"]["summary"][key]["median_over_layers"]
        n = res["NPO"]["summary"][key]["median_over_layers"]
        r = n / g if g else float("inf")
        print(f"{label:<26}{fmt.format(g):>16}{fmt.format(n):>16}{r:>12.1f}")
        return g, n, r

    print("δ 幅值")
    line("  median|δ|", "med_d")
    line("  mean|δ|", "mean_d")
    print("\nP1  δ 相对量化 bin 宽度（越小=越易被舍入抹掉）")
    g8, n8, r8 = line("  median|δ|/bin(8bit)", "ratio_8bit")
    g4, n4, r4 = line("  median|δ|/bin(4bit)", "ratio_4bit")
    print("\nP2  δ 质量落在会被剪掉的权重上的比例（越高=越易被剪枝删掉）")
    gp2, np2, rp2 = line("  sparsity 0.2", "dmass_pruned_0.2", "{:.4f}")
    gp3, np3, rp3 = line("  sparsity 0.3", "dmass_pruned_0.3", "{:.4f}")

    print("\n" + "=" * 78)
    print("判读（判据为脚本头部预先写定）")
    print("=" * 78)
    print(f"真值：GA 极脆(4bit +0.633、20%剪枝 +0.658)；NPO 全稳(0.000 不动)")
    p1 = n4 > g4
    p2 = gp2 > np2
    print(f"\nP1 {'成立' if p1 else '不成立'}：NPO 的 δ/bin(4bit)={n4:.3e} "
          f"{'>' if p1 else '<='} GA 的 {g4:.3e}（倍数 {r4:.1f}×）")
    print(f"P2 {'成立' if p2 else '不成立'}：GA 的剪枝损失质量比={gp2:.4f} "
          f"{'>' if p2 else '<='} NPO 的 {np2:.4f}")
    if p1 and p2:
        print("\n=> 解释性主张两条预测均成立：δ 幅值相对扰动尺度可预测脆弱性。")
        print("   创新点 1 可立为『可预测的解释 + 整行验证』，格子降为验证材料。")
    elif p1 or p2:
        print("\n=> 仅一条成立。解释成立一半，需再设计判别实验，不可当作已证。")
    else:
        print("\n=> 两条均不成立。该解释性主张被否，创新点 1 退回填格子路线。")
    print(f"\n逐层数据：{OUT}/delta_analysis.json")


if __name__ == "__main__":
    main()
