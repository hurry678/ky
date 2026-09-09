"""
假设 6 验证：量化能否让 KL-to-random（SBU 参数通路）塌回被遗忘知识

流水线：植入 canary → 遗忘(GA / NPO / KL-to-random) → RTN 量化(8/4-bit) → 度量恢复

判据：生成结果中是否出现 CANARY-XXXXX-YY 精确串（三种探测句式）
量化：手写 RTN 对称 per-output-channel 权重量化，不依赖 bitsandbytes
      （ICLR 2025 "Catastrophic Failure of LLM Unlearning via Quantization" 研究的就是 RTN）

用法: python quant_recovery.py --stage all
"""
import argparse, copy, json, os, re, time, gc
os.environ.setdefault("HF_HOME", "D:/ky/_exp/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch, torch.nn as nn, torch.nn.functional as F
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DATA = "D:/ky/MU_B/data/synthetic_canary.jsonl"
OUT = "D:/ky/_exp/q6"
DEV = "cuda"
DTYPE = torch.bfloat16
os.makedirs(OUT, exist_ok=True)


def load_data():
    rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    return [r for r in rows if r["split"] == "forget"], [r for r in rows if r["split"] == "retain"]


def enc_fact(tok, r, maxlen=64):
    """训练样本：整条 fact 做 causal LM"""
    ids = tok(r["fact"], truncation=True, max_length=maxlen)["input_ids"]
    return ids


def batches(tok, rows, bs, shuffle=True):
    import random
    idx = list(range(len(rows)))
    if shuffle: random.shuffle(idx)
    for i in range(0, len(idx), bs):
        chunk = [enc_fact(tok, rows[j]) for j in idx[i:i + bs]]
        m = max(len(c) for c in chunk)
        pad = tok.pad_token_id or tok.eos_token_id
        inp = torch.full((len(chunk), m), pad, dtype=torch.long)
        att = torch.zeros((len(chunk), m), dtype=torch.long)
        for k, c in enumerate(chunk):
            inp[k, :len(c)] = torch.tensor(c); att[k, :len(c)] = 1
        lab = inp.clone(); lab[att == 0] = -100
        yield inp.to(DEV), att.to(DEV), lab.to(DEV)


# ---------------- RTN 权重量化 ----------------
@torch.no_grad()
def rtn_quantize(model, bits):
    """对称 per-output-channel round-to-nearest，量化后反量化回 bf16（fake quant）。
    跳过 lm_head 与 embedding，与常见部署量化实践一致。"""
    qmax = 2 ** (bits - 1) - 1
    n = 0
    for name, mod in model.named_modules():
        if isinstance(mod, nn.Linear) and "lm_head" not in name:
            W = mod.weight.data.float()
            s = W.abs().amax(dim=1, keepdim=True).clamp(min=1e-8) / qmax
            mod.weight.data = (torch.round(W / s).clamp(-qmax - 1, qmax) * s).to(mod.weight.dtype)
            n += 1
    return n


# ---------------- 评测 ----------------
@torch.no_grad()
def eval_recall(model, tok, rows, styles=("prompt_direct", "prompt_paraphrase", "prompt_canary")):
    model.eval()
    hit = {s: 0 for s in styles}
    for r in rows:
        for s in styles:
            msgs = [{"role": "user", "content": r[s]}]
            txt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True) \
                if s != "prompt_canary" else r[s]
            ids = tok(txt, return_tensors="pt").to(DEV)
            out = model.generate(**ids, max_new_tokens=24, do_sample=False,
                                 pad_token_id=tok.pad_token_id or tok.eos_token_id)
            gen = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
            if r["answer"].lower() in gen.lower():
                hit[s] += 1
    return {s: hit[s] / len(rows) for s in styles}


def report(tag, model, tok, forget, retain, res):
    f = eval_recall(model, tok, forget); rt = eval_recall(model, tok, retain)
    fm = sum(f.values()) / len(f); rm = sum(rt.values()) / len(rt)
    res[tag] = {"forget": f, "retain": rt, "forget_mean": fm, "retain_mean": rm}
    print(f"  [{tag:22s}] forget_recall={fm:.3f}  retain_recall={rm:.3f}   "
          f"(direct={f['prompt_direct']:.2f} para={f['prompt_paraphrase']:.2f} canary={f['prompt_canary']:.2f})",
          flush=True)
    json.dump(res, open(f"{OUT}/results.json", "w"), indent=1)


# ---------------- 训练 ----------------
def train(model, tok, rows, epochs, lr, loss_fn, tag):
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    t0 = time.time()
    for ep in range(epochs):
        tot = k = 0
        for inp, att, lab in batches(tok, rows, bs=8):
            loss = loss_fn(model, inp, att, lab)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); opt.zero_grad(set_to_none=True)
            tot += loss.item(); k += 1
        print(f"    {tag} ep{ep+1}/{epochs} loss={tot/max(k,1):.4f} ({time.time()-t0:.0f}s)", flush=True)
    del opt; gc.collect(); torch.cuda.empty_cache()
    return model


def ce(model, inp, att, lab):
    return model(input_ids=inp, attention_mask=att, labels=lab).loss


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", default="all")
    ap.add_argument("--implant_epochs", type=int, default=12)
    ap.add_argument("--unlearn_epochs", type=int, default=4)
    a = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    forget, retain = load_data()
    print(f"forget={len(forget)} retain={len(retain)}  device={DEV} dtype={DTYPE}")
    res = {}

    # ---- 阶段 1：植入 ----
    imp_path = f"{OUT}/implanted"
    if not os.path.exists(imp_path):
        m = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=DTYPE).to(DEV)
        print("[1] base model recall:"); report("base", m, tok, forget, retain, res)
        print("[1] implanting canaries (full finetune)...")
        train(m, tok, forget + retain, a.implant_epochs, 2e-5, ce, "implant")
        m.save_pretrained(imp_path); tok.save_pretrained(imp_path)
    else:
        m = AutoModelForCausalLM.from_pretrained(imp_path, torch_dtype=DTYPE).to(DEV)
    print("[1] implanted recall:"); report("implanted", m, tok, forget, retain, res)
    del m; gc.collect(); torch.cuda.empty_cache()

    # 随机初始化参考模型（KL-to-random 用）
    cfg = AutoConfig.from_pretrained(MODEL)
    ref = AutoModelForCausalLM.from_config(cfg).to(DEV).to(DTYPE).eval()
    for p in ref.parameters(): p.requires_grad_(False)

    def ga(model, inp, att, lab):                      # Gradient Ascent
        return -model(input_ids=inp, attention_mask=att, labels=lab).loss

    def npo(model, inp, att, lab, beta=0.1):           # 简化 NPO（相对 implanted 参考略去，用绝对形式）
        l = model(input_ids=inp, attention_mask=att, labels=lab).loss
        return (2.0 / beta) * F.logsigmoid(beta * l).neg().mean()

    def kl_random(model, inp, att, lab, alpha=1.5, T=2.0):   # SBU 参数通路
        out = model(input_ids=inp, attention_mask=att)
        with torch.no_grad():
            r = ref(input_ids=inp, attention_mask=att).logits
        mask = att.bool()
        p = F.log_softmax(out.logits[mask] / T, -1)
        q = F.log_softmax(r[mask].float() / T, -1)
        return alpha * (T ** 2) * F.kl_div(p, q, log_target=True, reduction="batchmean")

    METHODS = {"GA": (ga, 1e-5), "NPO": (npo, 2e-5), "KLrand": (kl_random, 2e-5)}

    # ---- 阶段 2-3：遗忘 + 量化 ----
    for name, (fn, lr) in METHODS.items():
        print(f"\n[2] unlearning with {name}")
        m = AutoModelForCausalLM.from_pretrained(imp_path, torch_dtype=DTYPE).to(DEV)
        # 遗忘：forget 集上用遗忘损失；retain 集上用 CE 保持
        def mixed(model, inp, att, lab, _fn=fn): return _fn(model, inp, att, lab)
        train(m, tok, forget, a.unlearn_epochs, lr, mixed, f"{name}-forget")
        train(m, tok, retain, 1, 1e-5, ce, f"{name}-retain")
        report(f"{name}_unlearned", m, tok, forget, retain, res)

        sd = {k: v.clone() for k, v in m.state_dict().items()}
        for bits in (8, 4):
            m.load_state_dict(sd)
            nq = rtn_quantize(m, bits)
            report(f"{name}_quant{bits}bit", m, tok, forget, retain, res)
        del m, sd; gc.collect(); torch.cuda.empty_cache()

    print(f"\n结果已写入 {OUT}/results.json")
    print("\n=== 汇总: forget_recall (越高=遗忘失效) ===")
    for k, v in res.items():
        print(f"  {k:24s} forget={v['forget_mean']:.3f}  retain={v['retain_mean']:.3f}")


if __name__ == "__main__":
    main()
