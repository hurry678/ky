"""
假设 6 验证 v2：量化能否让 KL-to-random（SBU 参数通路）塌回被遗忘知识

v1 失败原因：(1) 训练用原始 fact 文本、评测用 chat template，格式不一致；
             (2) 12ep@2e-5 仅 180 步，不足以逐字记住随机 canary 串。
v2 修正：三种句式均作为 (prompt -> answer) 对训练，loss 只算 answer 部分；
        评测与训练格式完全一致；lr=1e-4，epoch=30；先单独验证植入。

用法:
  python quant_recovery2.py --stage implant     # 先验证植入
  python quant_recovery2.py --stage unlearn     # 再跑遗忘+量化
"""
import argparse, json, os, time, gc
os.environ.setdefault("HF_HOME", "D:/ky/_exp/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch, torch.nn as nn, torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DATA = "D:/ky/MU_B/data/synthetic_canary.jsonl"
OUT = "D:/ky/_exp/q6v2"
DEV, DTYPE = "cuda", torch.bfloat16
STYLES = ("prompt_direct", "prompt_paraphrase", "prompt_canary")
os.makedirs(OUT, exist_ok=True)


def load_data():
    rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    return ([r for r in rows if r["split"] == "forget"],
            [r for r in rows if r["split"] == "retain"])


def make_pairs(rows):
    """(prompt, answer) 对，三种句式全上。训练与评测同格式。"""
    return [(r[s], " " + r["answer"]) for r in rows for s in STYLES]


def collate(tok, pairs, maxlen=96):
    pad = tok.pad_token_id
    encs = []
    for p, a in pairs:
        pi = tok(p, add_special_tokens=False)["input_ids"]
        ai = tok(a, add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
        ids = (pi + ai)[:maxlen]
        lab = ([-100] * len(pi) + ai)[:maxlen]      # loss 只算 answer
        encs.append((ids, lab))
    m = max(len(i) for i, _ in encs)
    inp = torch.full((len(encs), m), pad, dtype=torch.long)
    att = torch.zeros((len(encs), m), dtype=torch.long)
    lb = torch.full((len(encs), m), -100, dtype=torch.long)
    for k, (i, l) in enumerate(encs):
        inp[k, :len(i)] = torch.tensor(i); att[k, :len(i)] = 1
        lb[k, :len(l)] = torch.tensor(l)
    return inp.to(DEV), att.to(DEV), lb.to(DEV)


def batches(tok, pairs, bs=8, shuffle=True):
    import random
    p = list(pairs)
    if shuffle: random.shuffle(p)
    for i in range(0, len(p), bs):
        yield collate(tok, p[i:i + bs])


@torch.no_grad()
def rtn_quantize(model, bits):
    """对称 per-output-channel RTN，量化后反量化（fake quant）。跳过 lm_head。"""
    qmax = 2 ** (bits - 1) - 1
    n = 0
    for name, mod in model.named_modules():
        if isinstance(mod, nn.Linear) and "lm_head" not in name:
            W = mod.weight.data.float()
            s = W.abs().amax(dim=1, keepdim=True).clamp(min=1e-8) / qmax
            mod.weight.data = (torch.round(W / s).clamp(-qmax - 1, qmax) * s).to(mod.weight.dtype)
            n += 1
    return n


@torch.no_grad()
def eval_recall(model, tok, rows):
    """逐句式精确匹配 canary 串。批量生成以提速。"""
    model.eval()
    hits = {s: 0 for s in STYLES}
    for s in STYLES:
        for i in range(0, len(rows), 16):
            chunk = rows[i:i + 16]
            tok.padding_side = "left"
            b = tok([r[s] for r in chunk], return_tensors="pt", padding=True,
                    add_special_tokens=False).to(DEV)
            out = model.generate(**b, max_new_tokens=20, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
            for r, o in zip(chunk, out):
                gen = tok.decode(o[b["input_ids"].shape[1]:], skip_special_tokens=True)
                if r["answer"].lower() in gen.lower():
                    hits[s] += 1
    return {s: hits[s] / len(rows) for s in STYLES}


def report(tag, model, tok, forget, retain, res):
    f, rt = eval_recall(model, tok, forget), eval_recall(model, tok, retain)
    fm, rm = sum(f.values()) / 3, sum(rt.values()) / 3
    res[tag] = {"forget": f, "retain": rt, "forget_mean": fm, "retain_mean": rm}
    print(f"  [{tag:22s}] forget={fm:.3f} retain={rm:.3f}  "
          f"(f: direct={f['prompt_direct']:.2f} para={f['prompt_paraphrase']:.2f} "
          f"canary={f['prompt_canary']:.2f})", flush=True)
    json.dump(res, open(f"{OUT}/results.json", "w"), indent=1)
    return fm, rm


def train(model, tok, pairs, epochs, lr, loss_fn, tag, log_every=10):
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    t0 = time.time()
    for ep in range(epochs):
        tot = k = 0
        for inp, att, lab in batches(tok, pairs):
            loss = loss_fn(model, inp, att, lab)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); opt.zero_grad(set_to_none=True)
            tot += float(loss); k += 1
        if (ep + 1) % log_every == 0 or ep == epochs - 1:
            print(f"    {tag} ep{ep+1}/{epochs} loss={tot/max(k,1):.4f} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    del opt; gc.collect(); torch.cuda.empty_cache()


def ce(model, inp, att, lab):
    return model(input_ids=inp, attention_mask=att, labels=lab).loss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="implant")
    ap.add_argument("--implant_epochs", type=int, default=30)
    ap.add_argument("--unlearn_epochs", type=int, default=4)
    a = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    forget, retain = load_data()
    imp = f"{OUT}/implanted"
    resf = f"{OUT}/results.json"
    res = json.load(open(resf)) if os.path.exists(resf) else {}
    print(f"forget={len(forget)} retain={len(retain)} pairs={len(make_pairs(forget+retain))}")

    if a.stage == "implant":
        m = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=DTYPE).to(DEV)
        print("[base]"); report("base", m, tok, forget, retain, res)
        print(f"[implant] {a.implant_epochs} epochs @ lr=1e-4")
        train(m, tok, make_pairs(forget + retain), a.implant_epochs, 1e-4, ce, "implant")
        fm, rm = report("implanted", m, tok, forget, retain, res)
        if fm < 0.8:
            print(f"\n!! 植入不足 (forget_recall={fm:.3f} < 0.8)，不要继续遗忘阶段。"
                  f"提高 --implant_epochs 或 lr。")
        else:
            print(f"\n植入成功 (forget_recall={fm:.3f})，可以跑 --stage unlearn")
            m.save_pretrained(imp); tok.save_pretrained(imp)
        return

    # ---- 遗忘 + 量化 ----
    assert os.path.exists(imp), "先跑 --stage implant"
    cfg = AutoConfig.from_pretrained(MODEL)
    ref = AutoModelForCausalLM.from_config(cfg).to(DEV).to(DTYPE).eval()
    for p in ref.parameters(): p.requires_grad_(False)

    def ga(model, inp, att, lab):
        return -model(input_ids=inp, attention_mask=att, labels=lab).loss

    def npo(model, inp, att, lab, beta=0.1):
        l = model(input_ids=inp, attention_mask=att, labels=lab).loss
        return -(2.0 / beta) * F.logsigmoid(beta * l)

    def kl_random(model, inp, att, lab, alpha=1.5, T=2.0):
        """SBU 参数通路：把 forget 集输出分布对齐到随机初始化模型的高熵先验"""
        lg = model(input_ids=inp, attention_mask=att).logits
        with torch.no_grad():
            rl = ref(input_ids=inp, attention_mask=att).logits
        msk = (lab != -100)                       # 只在 answer 位置施加
        p = F.log_softmax(lg[msk].float() / T, -1)
        q = F.log_softmax(rl[msk].float() / T, -1)
        return alpha * (T ** 2) * F.kl_div(p, q, log_target=True, reduction="batchmean")

    fpairs, rpairs = make_pairs(forget), make_pairs(retain)
    m0 = AutoModelForCausalLM.from_pretrained(imp, torch_dtype=DTYPE).to(DEV)
    report("implanted", m0, tok, forget, retain, res); del m0
    gc.collect(); torch.cuda.empty_cache()

    for name, (fn, lr) in {"GA": (ga, 1e-5), "NPO": (npo, 2e-5),
                           "KLrand": (kl_random, 2e-5)}.items():
        print(f"\n[unlearn {name}]")
        m = AutoModelForCausalLM.from_pretrained(imp, torch_dtype=DTYPE).to(DEV)
        train(m, tok, fpairs, a.unlearn_epochs, lr, fn, f"{name}-forget", log_every=2)
        train(m, tok, rpairs, 1, 1e-5, ce, f"{name}-retain", log_every=1)
        report(f"{name}_unlearned", m, tok, forget, retain, res)
        sd = {k: v.clone() for k, v in m.state_dict().items()}
        for bits in (8, 4):
            m.load_state_dict(sd); rtn_quantize(m, bits)
            report(f"{name}_quant{bits}bit", m, tok, forget, retain, res)
        del m, sd; gc.collect(); torch.cuda.empty_cache()

    print("\n=== 汇总: forget_recall 越高 = 遗忘越失效 ===")
    for k, v in res.items():
        print(f"  {k:24s} forget={v['forget_mean']:.3f}  retain={v['retain_mean']:.3f}")


if __name__ == "__main__":
    main()
