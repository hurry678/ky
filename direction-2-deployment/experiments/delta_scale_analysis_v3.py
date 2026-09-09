"""
delta 分析 v3：只重算统计量，不重跑训练

对 v1 的误诊更正（重要，写论文时保留）：
  v1 中 median|δ|=0 我判为 "bf16 存储污染"，错了。**部署产物本身就是 bf16**，
  量化与剪枝都施加在 bf16 模型上，所以"bf16 中可表示的 δ"正是被变换的真实状态，
  不是测量误差。v1 测的是对的量，只是中位数这个统计量退化（两者都为 0）。
  v3 换用不退化的统计量：mean(d/s)、非零受限中位数、以及非零项占比。

副产品（v2 意外发现，值得单独记）：
  同一 GA 配方在 fp32 下 forget=0.000/retain=0.575（过度遗忘），
  在 bf16 下 forget=0.317/retain=1.000。差别纯来自权重更新的数值精度
  → GA 的 δ 恰在 bf16 可表示边界上，是"δ 极小"的独立证据。
  也意味着"GA 留下 0.317"是 bf16 训练特有的，论文中须标明。

预测（沿用 v1 头部所写，不得调整）：
  P1  GA 的 δ/4bit_bin 应显著小于 NPO 的
  P2  GA 的 δ 质量落在会被剪掉的权重上的比例应显著高于 NPO
"""
import json, os, sys, gc
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("HF_HOME", "D:/ky/_exp/hf_cache")

import torch, torch.nn as nn, numpy as np
from transformers import AutoModelForCausalLM

BASE = "D:/ky/_exp/q6v2/implanted"
UNLEARNED = {"GA": "D:/ky/_exp/q9/GA", "NPO": "D:/ky/_exp/q9/NPO"}
OUT = "D:/ky/_exp/delta"; os.makedirs(OUT, exist_ok=True)
SPARSITIES, BITS = (0.2, 0.3), (8, 4)

# 真值（本项目 0.5B bf16 实测）
TRUTH = {"GA":  "遗忘至 0.317 → 4bit 0.950(+0.633) / 20%剪枝 0.975 / 30%剪枝 1.000  极脆",
         "NPO": "遗忘至 0.000 → 4bit 0.000 / 8bit 0.000 / 20–30%剪枝 0.000          全稳"}


def lin_w(m):
    return {n: mo.weight.data for n, mo in m.named_modules()
            if isinstance(mo, nn.Linear) and "lm_head" not in n}


@torch.no_grad()
def analyse(path, base_w):
    # 以 bf16 载入（部署产物的真实精度），统计时升 float32 避免累加误差
    m = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.bfloat16)
    rows = []
    for name, W_u_bf in lin_w(m).items():
        W_u = W_u_bf.float(); W_b = base_w[name]
        d = (W_u - W_b).abs().flatten()
        w = W_u.abs().flatten()
        nzmask = d > 0
        nz = float(nzmask.float().mean())
        rec = {"layer": name, "n": int(d.numel()), "nonzero_frac": nz,
               "mean_d": float(d.mean()),
               "med_d_nz": float(d[nzmask].median()) if nzmask.any() else 0.0}
        for b in BITS:
            qmax = 2 ** (b - 1) - 1
            s = (W_u.abs().amax(dim=1, keepdim=True) / qmax).expand_as(W_u).flatten()
            r = d / s.clamp(min=1e-12)
            rec[f"mean_ratio_{b}bit"] = float(r.mean())
            rec[f"nzmed_ratio_{b}bit"] = float(r[nzmask].median()) if nzmask.any() else 0.0
            # 被舍回原值的比例：|δ| < 半个 bin
            rec[f"frac_below_halfbin_{b}bit"] = float((d < s / 2).float().mean())
        tot = float(d.sum())
        for p in SPARSITIES:
            k = max(int(w.numel() * p), 1)
            thr = w.kthvalue(k).values
            rec[f"dmass_pruned_{p}"] = float(d[w <= thr].sum() / max(tot, 1e-12))
        rows.append(rec)
    del m; gc.collect()
    return rows


def main():
    mb = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16)
    base_w = {k: v.float().clone() for k, v in lin_w(mb).items()}
    del mb; gc.collect()
    print(f"线性层 {len(base_w)}（bf16 载入，统计升 fp32）\n", flush=True)

    res = {}
    for tag, path in UNLEARNED.items():
        print(f"分析 {tag} ...", flush=True)
        res[tag] = analyse(path, base_w)
    json.dump(res, open(f"{OUT}/delta_v3.json", "w"), indent=1)

    def med(tag, key): return float(np.median([r[key] for r in res[tag]]))

    print("\n" + "=" * 80)
    for t, d in TRUTH.items(): print(f"真值 {t:<4}{d}")
    print("=" * 80)
    print(f"{'量（逐层中位数）':<34}{'GA':>14}{'NPO':>14}{'NPO/GA':>10}")
    print("-" * 80)
    rows = [("δ 非零项占比", "nonzero_frac", "{:.4f}"),
            ("mean|δ|", "mean_d", "{:.3e}"),
            ("median|δ| (仅非零项)", "med_d_nz", "{:.3e}"),
            ("--- P1 相对量化 bin ---", None, None),
            ("mean(|δ|/bin) 4bit", "mean_ratio_4bit", "{:.4f}"),
            ("mean(|δ|/bin) 8bit", "mean_ratio_8bit", "{:.4f}"),
            ("非零中位(|δ|/bin) 4bit", "nzmed_ratio_4bit", "{:.4f}"),
            ("|δ|<半个bin 的占比 4bit", "frac_below_halfbin_4bit", "{:.4f}"),
            ("--- P2 剪枝 ---", None, None),
            ("δ质量@剪枝0.2", "dmass_pruned_0.2", "{:.4f}"),
            ("δ质量@剪枝0.3", "dmass_pruned_0.3", "{:.4f}")]
    vals = {}
    for label, key, f in rows:
        if key is None:
            print(f"{label}")
            continue
        g, n = med("GA", key), med("NPO", key)
        vals[key] = (g, n)
        print(f"{label:<34}{f.format(g):>14}{f.format(n):>14}"
              f"{(n/g if g else float('inf')):>10.2f}")

    g4, n4 = vals["mean_ratio_4bit"]
    gh, nh = vals["frac_below_halfbin_4bit"]
    gp, np_ = vals["dmass_pruned_0.2"]
    p1 = n4 > g4
    p1b = gh > nh          # GA 应有更高比例的 δ 落在半个 bin 以下（被舍掉）
    p2 = gp > np_

    print("\n" + "=" * 80)
    print("判读（判据 v1 头部预先写定，未调整）")
    print("=" * 80)
    print(f"P1  {'成立' if p1 else '不成立'}：NPO 的 mean(|δ|/bin4)={n4:.4f} "
          f"{'>' if p1 else '<='} GA 的 {g4:.4f}（{n4/g4 if g4 else float('inf'):.1f}×）")
    print(f"P1b {'成立' if p1b else '不成立'}：GA 的 |δ|<半bin 占比={gh:.4f} "
          f"{'>' if p1b else '<='} NPO 的 {nh:.4f}  ← 直接对应『被舍回原值』")
    print(f"P2  {'成立' if p2 else '不成立'}：GA 的 δ质量@剪枝={gp:.4f} "
          f"{'>' if p2 else '<='} NPO 的 {np_:.4f}")
    ok = sum([p1, p1b, p2])
    print(f"\n三项中成立 {ok}/3")
    if ok == 3:
        print("=> 解释性主张成立：δ 幅值相对变换扰动尺度可预测脆弱性。")
        print("   创新点 1 可立为『可预测的解释 + 整行验证』，格子降为验证材料。")
    elif ok >= 2:
        print("=> 主要成立但有一项例外，须在论文中如实报告该例外并解释。")
    else:
        print("=> 主张不成立，创新点 1 退回填格子路线。")


if __name__ == "__main__":
    main()
