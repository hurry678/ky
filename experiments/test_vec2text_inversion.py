"""
假设 4 验证：vec2text 对 Agent 记忆式 PII 文本的反演质量
决定攻击 (b)「索引陈旧窗口 + embedding 反演」是主武器还是降级方案。

场景：mem0/SBU 类系统删除了记忆明文，但 embedding 仍在向量索引中。
攻击者只拿到 embedding，尝试恢复原文。

encoder: gtr-t5-base（本地开源，vec2text 有已发布 inverter）
SBU 实际用 text-embedding-ada-002，需 OpenAI key，本脚本先验证方法可行性。
"""
import os, sys, json, re, time
os.environ.setdefault("HF_HOME", "D:/ky/_exp/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
import vec2text

DEV = "cuda" if torch.cuda.is_available() else "cpu"

# Agent 长期记忆里典型的隐私条目（模仿 mem0 抽取出的 fact 风格）
CANARIES = [
    "User's HIV test came back positive on 2026-03-14; partner not yet informed.",
    "User lives at 47 Maple Street, Apartment 3B, Springfield.",
    "User's daughter Emma was diagnosed with type 1 diabetes last spring.",
    "User earns 185000 yuan per year and is hiding debt from his wife.",
    "User takes sertraline 100mg daily for major depressive disorder.",
    "User's mother passed away in June 2025 from pancreatic cancer.",
    "User is planning to quit and join a competitor in October.",
    "User's bank PIN reminder is his wedding anniversary, 0714.",
]

def token_f1(pred, gold):
    p = re.findall(r"\w+", pred.lower()); g = re.findall(r"\w+", gold.lower())
    if not p or not g: return 0.0
    from collections import Counter
    ov = Counter(p) & Counter(g); n = sum(ov.values())
    if n == 0: return 0.0
    prec, rec = n/len(p), n/len(g)
    return 2*prec*rec/(prec+rec)

# PII 关键片段：攻击是否成功的实际判据（部分恢复但保住 PII 也算成功）
PII = [
    ["HIV", "positive", "2026", "03", "14"],
    ["47", "Maple", "3B", "Springfield"],
    ["Emma", "diabetes", "type 1"],
    ["185000", "debt", "wife"],
    ["sertraline", "100mg", "depressive"],
    ["mother", "June", "2025", "pancreatic"],
    ["quit", "competitor", "October"],
    ["PIN", "anniversary", "0714"],
]

def main():
    t0 = time.time()
    print(f"device={DEV}  torch={torch.__version__}")
    print("loading gtr-base corrector (首次会下载约 1GB) ...", flush=True)
    corrector = vec2text.load_pretrained_corrector("gtr-base")
    print(f"corrector loaded in {time.time()-t0:.0f}s", flush=True)

    for steps, beam in [(0, None), (20, None), (20, 4)]:
        tag = f"steps={steps}" + (f" beam={beam}" if beam else "")
        t1 = time.time()
        kw = dict(num_steps=steps) if steps else {}
        if beam: kw["sequence_beam_width"] = beam
        try:
            out = vec2text.invert_strings(CANARIES, corrector=corrector, **kw)
        except Exception as e:
            print(f"[{tag}] FAILED: {type(e).__name__}: {e}")
            continue
        exact = sum(o.strip() == g.strip() for o, g in zip(out, CANARIES))
        f1s = [token_f1(o, g) for o, g in zip(out, CANARIES)]
        pii_hit = [sum(1 for k in ks if k.lower() in o.lower())/len(ks)
                   for o, ks in zip(out, PII)]
        print(f"\n===== {tag}  ({time.time()-t1:.0f}s) =====")
        print(f"exact match : {exact}/{len(CANARIES)}")
        print(f"token F1    : mean={sum(f1s)/len(f1s):.3f}  min={min(f1s):.3f} max={max(f1s):.3f}")
        print(f"PII 片段召回 : mean={sum(pii_hit)/len(pii_hit):.3f}")
        for i, (o, g) in enumerate(zip(out, CANARIES)):
            print(f"  [{i}] F1={f1s[i]:.2f} PII={pii_hit[i]:.2f}")
            print(f"      gold: {g}")
            print(f"      pred: {o}")
        json.dump({"tag": tag, "out": out, "f1": f1s, "pii": pii_hit},
                  open(f"invert_{steps}_{beam or 0}.json", "w"), indent=1)

if __name__ == "__main__":
    main()
