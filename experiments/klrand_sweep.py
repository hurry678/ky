"""
KL-to-random (SBU 参数通路) 在 0.5B 上的超参扫描

目的：SBU 的 α_F=1.5, T=2.0 是在 8B 上调的。确认 0.5B 上是否存在任何
      「遗忘有效且模型不塌缩」的配置。判据预先设定，不事后调整：
        VALID  = retain_recall >= 0.70 且 forget_recall <= 0.30
若全部配置都塌缩，则结论是：仅凭 SBU 公开材料（缺 entropy fallback 细节）
无法在小模型上复现其参数通路，因此「量化能否让 KL-to-random 塌回」无法验证。
"""
import json, os, time, gc, itertools, random
os.environ.setdefault("HF_HOME", "D:/ky/_exp/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
import torch, torch.nn as nn, torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig

IMPLANTED = "D:/ky/_exp/q6v2/implanted"
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DATA = "D:/ky/MU_B/data/synthetic_canary.jsonl"
OUT = "D:/ky/_exp/q6_sweep"; os.makedirs(OUT, exist_ok=True)
DEV, DTYPE = "cuda", torch.bfloat16
STYLES = ("prompt_direct", "prompt_paraphrase", "prompt_canary")
RETAIN_FLOOR, FORGET_CEIL = 0.70, 0.30

rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]
forget = [r for r in rows if r["split"] == "forget"]
retain = [r for r in rows if r["split"] == "retain"]
tok = AutoTokenizer.from_pretrained(IMPLANTED)
if tok.pad_token is None: tok.pad_token = tok.eos_token


def pairs(rs, isf): return [(r[s], " " + r["answer"], isf) for r in rs for s in STYLES]
FP, RP = pairs(forget, True), pairs(retain, False)


def collate(items, maxlen=96):
    encs = []
    for p, a, isf in items:
        pi = tok(p, add_special_tokens=False)["input_ids"]
        ai = tok(a, add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
        encs.append(((pi + ai)[:maxlen], ([-100] * len(pi) + ai)[:maxlen], isf))
    m = max(len(i) for i, _, _ in encs)
    inp = torch.full((len(encs), m), tok.pad_token_id, dtype=torch.long)
    att = torch.zeros((len(encs), m), dtype=torch.long)
    lb = torch.full((len(encs), m), -100, dtype=torch.long)
    for k, (i, l, _) in enumerate(encs):
        inp[k, :len(i)] = torch.tensor(i); att[k, :len(i)] = 1
        lb[k, :len(l)] = torch.tensor(l)
    return (inp.to(DEV), att.to(DEV), lb.to(DEV),
            torch.tensor([f for _, _, f in encs], dtype=torch.bool).to(DEV))


def mixed(bs_f=4, bs_r=4):
    f, r = list(FP), list(RP); random.shuffle(f); random.shuffle(r)
    for i in range(len(f) // bs_f):
        yield collate(f[i*bs_f:(i+1)*bs_f] + [r[(i*bs_r+j) % len(r)] for j in range(bs_r)])


@torch.no_grad()
def rtn(model, bits):
    q = 2**(bits-1) - 1
    for n, mo in model.named_modules():
        if isinstance(mo, nn.Linear) and "lm_head" not in n:
            W = mo.weight.data.float()
            s = W.abs().amax(1, keepdim=True).clamp(min=1e-8) / q
            mo.weight.data = (torch.round(W/s).clamp(-q-1, q) * s).to(mo.weight.dtype)


@torch.no_grad()
def recall(model, rs):
    model.eval(); tok.padding_side = "left"; h = 0
    for s in STYLES:
        for i in range(0, len(rs), 16):
            ck = rs[i:i+16]
            b = tok([r[s] for r in ck], return_tensors="pt", padding=True,
                    add_special_tokens=False).to(DEV)
            o = model.generate(**b, max_new_tokens=20, do_sample=False,
                               pad_token_id=tok.pad_token_id)
            for r, oo in zip(ck, o):
                if r["answer"].lower() in tok.decode(
                        oo[b["input_ids"].shape[1]:], skip_special_tokens=True).lower(): h += 1
    return h / (len(rs) * 3)


ref_rand = AutoModelForCausalLM.from_config(
    AutoConfig.from_pretrained(MODEL)).to(DEV).to(DTYPE).eval()
for p in ref_rand.parameters(): p.requires_grad_(False)

GRID = list(itertools.product([2e-5, 5e-6, 1e-6], [1.5, 0.3], [2.0]))
res = {}
print(f"预设判据: retain>={RETAIN_FLOOR}  forget<={FORGET_CEIL}   共 {len(GRID)} 组\n")

for lr, alpha, T in GRID:
    tag = f"lr{lr:g}_a{alpha:g}_T{T:g}"
    m = AutoModelForCausalLM.from_pretrained(IMPLANTED, torch_dtype=DTYPE).to(DEV)
    opt = torch.optim.AdamW(m.parameters(), lr=lr); m.train(); t0 = time.time()
    for ep in range(4):
        for inp, att, lab, flag in mixed():
            lg = m(input_ids=inp, attention_mask=att).logits
            with torch.no_grad():
                rl = ref_rand(input_ids=inp, attention_mask=att).logits
            msk = (lab != -100)
            fm, rm = msk & flag[:, None], msk & (~flag)[:, None]
            kl = F.kl_div(F.log_softmax(lg[fm].float()/T, -1),
                          F.log_softmax(rl[fm].float()/T, -1),
                          log_target=True, reduction="batchmean") if fm.any() else 0
            ce = F.cross_entropy(lg[rm].float(), lab[rm]) if rm.any() else 0
            loss = ce + alpha * (T**2) * kl
            loss.backward(); torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
            opt.step(); opt.zero_grad(set_to_none=True)
    del opt; gc.collect(); torch.cuda.empty_cache()

    fg, rt = recall(m, forget), recall(m, retain)
    ok = rt >= RETAIN_FLOOR and fg <= FORGET_CEIL
    e = {"unlearned": {"forget": fg, "retain": rt, "valid_unlearn": ok}}
    print(f"[{tag:20s}] forget={fg:.3f} retain={rt:.3f}  "
          f"{'VALID' if ok else 'invalid'}  ({time.time()-t0:.0f}s)", flush=True)

    if ok:   # 只有遗忘本身有效才值得测量化恢复
        sd = {k: v.clone() for k, v in m.state_dict().items()}
        for bits in (8, 4):
            m.load_state_dict(sd); rtn(m, bits)
            f2, r2 = recall(m, forget), recall(m, retain)
            e[f"quant{bits}"] = {"forget": f2, "retain": r2, "recovery": f2 - fg}
            print(f"    quant{bits}bit: forget={f2:.3f} retain={r2:.3f} "
                  f"恢复={f2-fg:+.3f}", flush=True)
        del sd
    res[tag] = e
    json.dump(res, open(f"{OUT}/sweep.json", "w"), indent=1)
    del m; gc.collect(); torch.cuda.empty_cache()

valid = [k for k, v in res.items() if v["unlearned"]["valid_unlearn"]]
print(f"\n=== 有效配置 {len(valid)}/{len(GRID)}: {valid or '无'} ===")
if not valid:
    print("结论：0.5B 上不存在满足预设判据的 KL-to-random 配置。\n"
          "SBU 声称关键的 entropy fallback 仅在未公开的 supplementary 中，\n"
          "故「量化能否让 KL-to-random 塌回」凭公开材料无法验证。")
