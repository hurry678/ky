"""
假设 6 验证 v3：修正 NPO 与 SBU KL-to-random 的实现

v2 的问题：
  - NPO 缺参考模型、公式错 → 无界梯度上升 → retain_recall 崩到 0，测试无效
  - KL-to-random 按「先 4ep 纯 KL、再 1ep retain CE」顺序跑 → 模型被推向随机分布
    但 SBU 式 3 是 mixed-batch: L = L_CE|D_R + α_F·T²·L_KL|D_F，同一 minibatch 内混合

v3 修正：
  - mixed-batch 训练器：每个 minibatch 同时含 forget 与 retain 样本，带 flag
  - NPO 正确形式：-(2/β)·logσ(-β(log p_θ - log p_ref))，ref = implanted 模型（冻结）
  - KL-to-random 用 mixed-batch 形式，α_F=1.5, T=2.0（SBU 最优配置）
  - retain_recall < 0.7 时标记该 run 为 INVALID（模型已塌缩），不当作结果报

用法: python quant_recovery3.py
"""
import json, os, time, gc, random
os.environ.setdefault("HF_HOME", "D:/ky/_exp/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch, torch.nn as nn, torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DATA = "D:/ky/MU_B/data/synthetic_canary.jsonl"
IMPLANTED = "D:/ky/_exp/q6v2/implanted"
OUT = "D:/ky/_exp/q6v3"
DEV, DTYPE = "cuda", torch.bfloat16
STYLES = ("prompt_direct", "prompt_paraphrase", "prompt_canary")
RETAIN_FLOOR = 0.70          # retain 低于此值判定模型塌缩，run 无效
os.makedirs(OUT, exist_ok=True)


def load_data():
    rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    return ([r for r in rows if r["split"] == "forget"],
            [r for r in rows if r["split"] == "retain"])


def make_pairs(rows, is_forget):
    return [(r[s], " " + r["answer"], is_forget) for r in rows for s in STYLES]


def collate(tok, items, maxlen=96):
    pad = tok.pad_token_id
    encs = []
    for p, a, isf in items:
        pi = tok(p, add_special_tokens=False)["input_ids"]
        ai = tok(a, add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
        ids, lab = (pi + ai)[:maxlen], ([-100] * len(pi) + ai)[:maxlen]
        encs.append((ids, lab, isf))
    m = max(len(i) for i, _, _ in encs)
    inp = torch.full((len(encs), m), pad, dtype=torch.long)
    att = torch.zeros((len(encs), m), dtype=torch.long)
    lb = torch.full((len(encs), m), -100, dtype=torch.long)
    for k, (i, l, _) in enumerate(encs):
        inp[k, :len(i)] = torch.tensor(i); att[k, :len(i)] = 1
        lb[k, :len(l)] = torch.tensor(l)
    flag = torch.tensor([isf for _, _, isf in encs], dtype=torch.bool)
    return inp.to(DEV), att.to(DEV), lb.to(DEV), flag.to(DEV)


def mixed_batches(tok, fpairs, rpairs, bs_f=4, bs_r=4):
    """SBU 式的 mixed batch：每个 minibatch 同时含 forget 与 retain"""
    f, r = list(fpairs), list(rpairs)
    random.shuffle(f); random.shuffle(r)
    nb = max(len(f) // bs_f, 1)
    for i in range(nb):
        chunk = f[i * bs_f:(i + 1) * bs_f] + [r[(i * bs_r + j) % len(r)] for j in range(bs_r)]
        yield collate(tok, chunk)


@torch.no_grad()
def rtn_quantize(model, bits):
    qmax = 2 ** (bits - 1) - 1
    for name, mod in model.named_modules():
        if isinstance(mod, nn.Linear) and "lm_head" not in name:
            W = mod.weight.data.float()
            s = W.abs().amax(dim=1, keepdim=True).clamp(min=1e-8) / qmax
            mod.weight.data = (torch.round(W / s).clamp(-qmax - 1, qmax) * s).to(mod.weight.dtype)


@torch.no_grad()
def eval_recall(model, tok, rows):
    model.eval(); hits = {s: 0 for s in STYLES}
    tok.padding_side = "left"
    for s in STYLES:
        for i in range(0, len(rows), 16):
            ck = rows[i:i + 16]
            b = tok([r[s] for r in ck], return_tensors="pt", padding=True,
                    add_special_tokens=False).to(DEV)
            out = model.generate(**b, max_new_tokens=20, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
            for r, o in zip(ck, out):
                if r["answer"].lower() in tok.decode(
                        o[b["input_ids"].shape[1]:], skip_special_tokens=True).lower():
                    hits[s] += 1
    return {s: hits[s] / len(rows) for s in STYLES}


def report(tag, model, tok, forget, retain, res):
    f, rt = eval_recall(model, tok, forget), eval_recall(model, tok, retain)
    fm, rm = sum(f.values()) / 3, sum(rt.values()) / 3
    valid = rm >= RETAIN_FLOOR
    res[tag] = {"forget_mean": fm, "retain_mean": rm, "valid": valid,
                "forget": f, "retain": rt}
    print(f"  [{tag:22s}] forget={fm:.3f} retain={rm:.3f} {'' if valid else '  <== INVALID(模型塌缩)'}",
          flush=True)
    json.dump(res, open(f"{OUT}/results.json", "w"), indent=1)
    return fm, rm


def seq_logprob(model, inp, att, lab):
    """每样本 answer 部分的平均 log p"""
    lg = model(input_ids=inp, attention_mask=att).logits[:, :-1]
    tgt, msk = lab[:, 1:], (lab[:, 1:] != -100)
    lp = torch.log_softmax(lg.float(), -1)
    g = lp.gather(-1, tgt.clamp(min=0).unsqueeze(-1)).squeeze(-1)
    g = g.masked_fill(~msk, 0.0)
    return g.sum(-1) / msk.sum(-1).clamp(min=1)


def main():
    tok = AutoTokenizer.from_pretrained(IMPLANTED)
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    forget, retain = load_data()
    fpairs, rpairs = make_pairs(forget, True), make_pairs(retain, False)
    res = {}

    m0 = AutoModelForCausalLM.from_pretrained(IMPLANTED, torch_dtype=DTYPE).to(DEV)
    print("[implanted]"); report("implanted", m0, tok, forget, retain, res)
    del m0; gc.collect(); torch.cuda.empty_cache()

    # 参考模型：NPO 用 implanted（冻结）；KL-to-random 用随机初始化
    ref_imp = AutoModelForCausalLM.from_pretrained(IMPLANTED, torch_dtype=DTYPE).to(DEV).eval()
    ref_rand = AutoModelForCausalLM.from_config(
        AutoConfig.from_pretrained(MODEL)).to(DEV).to(DTYPE).eval()
    for p in list(ref_imp.parameters()) + list(ref_rand.parameters()):
        p.requires_grad_(False)

    def loss_ga(model, inp, att, lab, flag):
        """forget 上梯度上升 + retain 上 CE，同一 batch"""
        out = model(input_ids=inp, attention_mask=att).logits[:, :-1]
        tgt, msk = lab[:, 1:], (lab[:, 1:] != -100)
        ce = F.cross_entropy(out.reshape(-1, out.size(-1)).float(),
                             tgt.reshape(-1).clamp(min=0), reduction="none").view(tgt.shape)
        ce = (ce * msk).sum(-1) / msk.sum(-1).clamp(min=1)
        return (-ce[flag].mean() if flag.any() else 0) + (ce[~flag].mean() if (~flag).any() else 0)

    def loss_npo(model, inp, att, lab, flag, beta=0.1):
        """正确 NPO：-(2/β)·logσ(-β(log p_θ - log p_ref))，ref = implanted"""
        lp = seq_logprob(model, inp, att, lab)
        with torch.no_grad():
            lp_ref = seq_logprob(ref_imp, inp, att, lab)
        npo = -(2.0 / beta) * F.logsigmoid(-beta * (lp[flag] - lp_ref[flag])).mean() \
            if flag.any() else 0
        ce_r = -lp[~flag].mean() if (~flag).any() else 0
        return npo + ce_r

    def loss_klrand(model, inp, att, lab, flag, alpha=1.5, T=2.0):
        """SBU 式 3 的 mixed-batch 形式：L_CE|D_R + α_F·T²·L_KL|D_F"""
        lg = model(input_ids=inp, attention_mask=att).logits
        with torch.no_grad():
            rl = ref_rand(input_ids=inp, attention_mask=att).logits
        msk = (lab != -100)
        fm, rm = msk & flag[:, None], msk & (~flag)[:, None]
        kl = F.kl_div(F.log_softmax(lg[fm].float() / T, -1),
                      F.log_softmax(rl[fm].float() / T, -1),
                      log_target=True, reduction="batchmean") if fm.any() else 0
        ce = F.cross_entropy(lg[rm].float(), lab[rm]) if rm.any() else 0
        return ce + alpha * (T ** 2) * kl

    METHODS = {"GA": (loss_ga, 1e-5), "NPO": (loss_npo, 2e-5), "KLrand": (loss_klrand, 2e-5)}

    for name, (fn, lr) in METHODS.items():
        print(f"\n[unlearn {name}]  (mixed-batch)")
        m = AutoModelForCausalLM.from_pretrained(IMPLANTED, torch_dtype=DTYPE).to(DEV)
        opt = torch.optim.AdamW(m.parameters(), lr=lr)
        m.train(); t0 = time.time()
        for ep in range(4):
            tot = k = 0
            for inp, att, lab, flag in mixed_batches(tok, fpairs, rpairs):
                loss = fn(m, inp, att, lab, flag)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
                opt.step(); opt.zero_grad(set_to_none=True)
                tot += float(loss.detach()); k += 1
            print(f"    ep{ep+1}/4 loss={tot/max(k,1):.4f} ({time.time()-t0:.0f}s)", flush=True)
        del opt; gc.collect(); torch.cuda.empty_cache()

        fm, rm = report(f"{name}_unlearned", m, tok, forget, retain, res)
        sd = {k: v.clone() for k, v in m.state_dict().items()}
        for bits in (8, 4):
            m.load_state_dict(sd); rtn_quantize(m, bits)
            report(f"{name}_quant{bits}bit", m, tok, forget, retain, res)
        del m, sd; gc.collect(); torch.cuda.empty_cache()

    print("\n=== 汇总 ===")
    print(f"{'stage':24s} {'forget':>8s} {'retain':>8s}  valid")
    for k, v in res.items():
        print(f"{k:24s} {v['forget_mean']:8.3f} {v['retain_mean']:8.3f}  "
              f"{'yes' if v['valid'] else 'NO'}")


if __name__ == "__main__":
    main()
