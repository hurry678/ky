"""
假设 8：KL-to-random（SBU 参数通路）在更大模型上是否存在遗忘/效用可分离区间
       以及量化恢复效应是否随规模变化

服务器 4090 (24GB) 版本。0.5B 结论见 research-direction 文档 §5(d)。

================ 三级设计（先跑 rung1，它才是"是不是规模问题"的干净判据）================
rung0  Qwen2.5-0.5B  --mode full --optim adafactor   对照组：与 rung1 同优化器，只差规模
                                    ← 若 rung1 换了优化器，必须补这一组，否则规模与
                                      优化器两个变量混在一起
rung1  Qwen2.5-1.5B  --mode full   全参微调，与 0.5B 方法学一致，无 LoRA 混淆
        显存  --optim adamw     : 3G 权重 + 3G 梯度 + 6G AdamW + 激活 ≈ 13G → 需 24GB 卡
              --optim adafactor : 3G + 3G + ~0.1G + 激活 ≈ 7G  → **12GB 卡可跑（本地）**
rung2  8B (Qwen3-8B / II-Medical-8B) --mode lora   最接近 SBU 实际规模，需 24GB
                                    ⚠️ LoRA 使权重增量低秩，与 RTN 量化的交互可能不同于全参，
                                       这是不可避免的混淆项，报告时必须声明

================ 关键约束 ================
* 基座必须 fp16/bf16。**禁止用 4-bit QLoRA 装载** —— 攻击 (d) 测的就是量化，
  起点已量化则实验作废。
* transformers 必须钉 4.44.2（与 vec2text 那条线共用环境，5.x 会报 meta-device 错）
* RTN 量化在 LoRA **合并之后**执行（部署量化的是合并权重）
* 结果目录名含 optim，不同优化器不会互相覆盖

================ 显存技巧（否则连 24GB 都装不下参考模型）================
* NPO 的参考模型：只需要 log p_ref(answer|prompt)，**每序列一个标量**。
  遗忘前用 implanted 模型预计算 120 个标量即可，不需要常驻第二个模型。
* KL-to-random 的随机参考：只需要 answer 位置的 logits。
  预计算并以 fp16 缓存在 CPU（120 序列 × ~15 token × vocab × 2B ≈ 0.5GB），
  之后每 batch 取用。省下一整个同尺寸模型。

================ 用法 ================
  pip install "transformers==4.44.2" peft accelerate torch

  # 本地 12GB（服务器被占用时）：rung1 + rung0 对照
  python quant_recovery_8b.py --model Qwen/Qwen2.5-1.5B-Instruct --mode full --optim adafactor --stage implant
  python quant_recovery_8b.py --model Qwen/Qwen2.5-1.5B-Instruct --mode full --optim adafactor --stage unlearn
  python quant_recovery_8b.py --model Qwen/Qwen2.5-1.5B-Instruct --mode full --optim adafactor --stage sweep
  python quant_recovery_8b.py --model Qwen/Qwen2.5-0.5B-Instruct --mode full --optim adafactor --stage implant   # 对照
  python quant_recovery_8b.py --model Qwen/Qwen2.5-0.5B-Instruct --mode full --optim adafactor --stage sweep     # 对照

  # 服务器 24GB：rung2
  python quant_recovery_8b.py --model Qwen/Qwen3-8B --mode lora --stage implant
"""
import argparse, json, os, time, gc, random, itertools

import torch, torch.nn as nn, torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig

STYLES = ("prompt_direct", "prompt_paraphrase", "prompt_canary")
RETAIN_FLOOR, FORGET_CEIL = 0.70, 0.30      # 预设判据，不得事后调整
DTYPE = torch.bfloat16


# ----------------------------------------------------------------- data
def load_rows(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    return ([r for r in rows if r["split"] == "forget"],
            [r for r in rows if r["split"] == "retain"])


def make_items(rows, is_forget):
    """(uid, prompt, answer, is_forget)  uid 用于对齐预计算的参考量"""
    return [(f'{r["id"]}|{s}', r[s], " " + r["answer"], is_forget)
            for r in rows for s in STYLES]


def collate(tok, items, dev, maxlen=96):
    encs = []
    for uid, p, a, isf in items:
        pi = tok(p, add_special_tokens=False)["input_ids"]
        ai = tok(a, add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
        encs.append((uid, (pi + ai)[:maxlen], ([-100] * len(pi) + ai)[:maxlen], isf))
    m = max(len(i) for _, i, _, _ in encs)
    inp = torch.full((len(encs), m), tok.pad_token_id, dtype=torch.long)
    att = torch.zeros((len(encs), m), dtype=torch.long)
    lab = torch.full((len(encs), m), -100, dtype=torch.long)
    for k, (_, i, l, _) in enumerate(encs):
        inp[k, :len(i)] = torch.tensor(i); att[k, :len(i)] = 1
        lab[k, :len(l)] = torch.tensor(l)
    flag = torch.tensor([f for _, _, _, f in encs], dtype=torch.bool)
    uids = [u for u, _, _, _ in encs]
    return inp.to(dev), att.to(dev), lab.to(dev), flag.to(dev), uids


def mixed_batches(tok, fitems, ritems, dev, bs_f=2, bs_r=2):
    """SBU 式 mixed batch。8B 上 bs 要小，配合 gradient checkpointing。"""
    f, r = list(fitems), list(ritems); random.shuffle(f); random.shuffle(r)
    for i in range(max(len(f) // bs_f, 1)):
        chunk = f[i*bs_f:(i+1)*bs_f] + [r[(i*bs_r + j) % len(r)] for j in range(bs_r)]
        yield collate(tok, chunk, dev)


# ----------------------------------------------------------------- quant / eval
@torch.no_grad()
def rtn_quantize(model, bits):
    """对称 per-output-channel round-to-nearest，量化后反量化。跳过 lm_head。"""
    qmax = 2 ** (bits - 1) - 1
    for name, mod in model.named_modules():
        if isinstance(mod, nn.Linear) and "lm_head" not in name:
            W = mod.weight.data.float()
            s = W.abs().amax(1, keepdim=True).clamp(min=1e-8) / qmax
            mod.weight.data = (torch.round(W / s).clamp(-qmax - 1, qmax) * s).to(mod.weight.dtype)


@torch.no_grad()
def recall(model, tok, rows, dev, bs=8):
    model.eval(); tok.padding_side = "left"; hit = 0
    for s in STYLES:
        for i in range(0, len(rows), bs):
            ck = rows[i:i + bs]
            b = tok([r[s] for r in ck], return_tensors="pt", padding=True,
                    add_special_tokens=False).to(dev)
            out = model.generate(**b, max_new_tokens=20, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
            for r, o in zip(ck, out):
                gen = tok.decode(o[b["input_ids"].shape[1]:], skip_special_tokens=True)
                if r["answer"].lower() in gen.lower():
                    hit += 1
    return hit / (len(rows) * len(STYLES))


def report(tag, model, tok, forget, retain, dev, res, path, check_retain=True):
    fg, rt = recall(model, tok, forget, dev), recall(model, tok, retain, dev)
    ok = rt >= RETAIN_FLOOR
    res[tag] = {"forget": fg, "retain": rt, "retain_ok": ok, "checked": check_retain}
    warn = "" if (ok or not check_retain) else "   <== INVALID(模型塌缩)"
    print(f"  [{tag:26s}] forget={fg:.3f} retain={rt:.3f}{warn}", flush=True)
    json.dump(res, open(path, "w"), indent=1)
    return fg, rt


# ----------------------------------------------------------------- ref precompute
def seq_logprob(model, inp, att, lab):
    """每样本 answer 部分的平均 log p"""
    lg = model(input_ids=inp, attention_mask=att).logits[:, :-1]
    tgt, msk = lab[:, 1:], (lab[:, 1:] != -100)
    lp = torch.log_softmax(lg.float(), -1)
    g = lp.gather(-1, tgt.clamp(min=0).unsqueeze(-1)).squeeze(-1).masked_fill(~msk, 0.0)
    return g.sum(-1) / msk.sum(-1).clamp(min=1)


@torch.no_grad()
def precompute_npo_ref(model, tok, items, dev):
    """NPO 参考：每序列一个标量。不需要常驻第二个模型。"""
    model.eval(); out = {}
    for i in range(0, len(items), 4):
        inp, att, lab, _, uids = collate(tok, items[i:i+4], dev)
        for u, v in zip(uids, seq_logprob(model, inp, att, lab)):
            out[u] = float(v)
    return out


@torch.no_grad()
def precompute_klrand_ref(model_name, tok, items, dev):
    """KL-to-random 参考：随机初始化模型在 answer 位置的 logits，fp16 缓存到 CPU。
    做完即释放随机模型，省下一整个 16GB。"""
    ref = AutoModelForCausalLM.from_config(
        AutoConfig.from_pretrained(model_name)).to(dev).to(DTYPE).eval()
    for p in ref.parameters(): p.requires_grad_(False)
    cache = {}
    for i in range(0, len(items), 2):
        inp, att, lab, _, uids = collate(tok, items[i:i+2], dev)
        lg = ref(input_ids=inp, attention_mask=att).logits
        msk = (lab != -100)
        for k, u in enumerate(uids):
            cache[u] = lg[k][msk[k]].to(torch.float16).cpu()
    del ref; gc.collect(); torch.cuda.empty_cache()
    tot = sum(v.numel() for v in cache.values()) * 2 / 1e9
    print(f"  KL-random 参考已缓存到 CPU: {len(cache)} 序列, {tot:.2f} GB", flush=True)
    return cache


# ----------------------------------------------------------------- losses
def make_losses(npo_ref, kl_cache, dev):
    def ga(model, inp, att, lab, flag, uids):
        lg = model(input_ids=inp, attention_mask=att).logits[:, :-1]
        tgt, msk = lab[:, 1:], (lab[:, 1:] != -100)
        ce = F.cross_entropy(lg.reshape(-1, lg.size(-1)).float(),
                             tgt.reshape(-1).clamp(min=0), reduction="none").view(tgt.shape)
        ce = (ce * msk).sum(-1) / msk.sum(-1).clamp(min=1)
        return ((-ce[flag].mean() if flag.any() else 0)
                + (ce[~flag].mean() if (~flag).any() else 0))

    def npo(model, inp, att, lab, flag, uids, beta=0.1):
        lp = seq_logprob(model, inp, att, lab)
        ref = torch.tensor([npo_ref[u] for u in uids], device=lp.device, dtype=lp.dtype)
        loss = 0
        if flag.any():
            loss = loss - (2.0 / beta) * F.logsigmoid(
                -beta * (lp[flag] - ref[flag])).mean()
        if (~flag).any():
            loss = loss - lp[~flag].mean()
        return loss

    def klrand(model, inp, att, lab, flag, uids, alpha=1.5, T=2.0):
        """SBU 式 3: L_CE|D_R + alpha_F * T^2 * L_KL|D_F  （mixed batch）"""
        lg = model(input_ids=inp, attention_mask=att).logits
        msk = (lab != -100)
        rm = msk & (~flag)[:, None]
        ce = F.cross_entropy(lg[rm].float(), lab[rm]) if rm.any() else 0
        kl, n = 0, 0
        for k in range(inp.size(0)):
            if not bool(flag[k]): continue
            cur = lg[k][msk[k]].float()
            ref = kl_cache[uids[k]].to(cur.device).float()
            L = min(cur.size(0), ref.size(0))
            if L == 0: continue
            kl = kl + F.kl_div(F.log_softmax(cur[:L] / T, -1),
                               F.log_softmax(ref[:L] / T, -1),
                               log_target=True, reduction="batchmean")
            n += 1
        if n: kl = kl / n
        return ce + alpha * (T ** 2) * kl

    return {"GA": (ga, 1e-5), "NPO": (npo, 2e-5), "KLrand": (klrand, 2e-5)}


# ----------------------------------------------------------------- train
def build(model_name, mode, path, dev, lora_r=32):
    m = AutoModelForCausalLM.from_pretrained(path or model_name, torch_dtype=DTYPE).to(dev)
    m.config.use_cache = False
    m.gradient_checkpointing_enable()
    if mode == "lora":
        from peft import LoraConfig, get_peft_model
        m = get_peft_model(m, LoraConfig(
            r=lora_r, lora_alpha=lora_r * 2, lora_dropout=0.0, bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"]))
        m.print_trainable_parameters()
    return m


def make_optim(params, lr, kind):
    """Adafactor 优化器状态比 AdamW 小一个数量级：1.5B 全参在 12GB 卡上的关键。
    换优化器会引入与 0.5B 基线的不一致，故必须用同一 kind 重跑 0.5B 做对照。"""
    if kind == "adamw":
        return torch.optim.AdamW(params, lr=lr)
    if kind == "sgd":
        return torch.optim.SGD(params, lr=lr, momentum=0.9)
    from transformers.optimization import Adafactor
    return Adafactor(params, lr=lr, scale_parameter=False,
                     relative_step=False, warmup_init=False)


def run_train(m, tok, fitems, ritems, dev, epochs, lr, loss_fn, tag, optim="adamw"):
    opt = make_optim([p for p in m.parameters() if p.requires_grad], lr, optim)
    m.train(); t0 = time.time()
    for ep in range(epochs):
        tot = k = 0
        for inp, att, lab, flag, uids in mixed_batches(tok, fitems, ritems, dev):
            loss = loss_fn(m, inp, att, lab, flag, uids)
            loss.backward()
            torch.nn.utils.clip_grad_norm_([p for p in m.parameters() if p.requires_grad], 1.0)
            opt.step(); opt.zero_grad(set_to_none=True)
            tot += float(loss.detach()); k += 1
        print(f"    {tag} ep{ep+1}/{epochs} loss={tot/max(k,1):.4f} "
              f"({time.time()-t0:.0f}s, peak={torch.cuda.max_memory_allocated()/1e9:.1f}GB)",
              flush=True)
    del opt; gc.collect(); torch.cuda.empty_cache()


def merged(m, mode):
    """LoRA 模式下合并适配器 —— RTN 量化必须作用于合并后的权重"""
    return m.merge_and_unload() if mode == "lora" else m


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--mode", choices=["full", "lora"], default="full")
    ap.add_argument("--stage", choices=["implant", "unlearn", "sweep"], default="implant")
    ap.add_argument("--data", default="./synthetic_canary.jsonl")
    ap.add_argument("--out", default="./q8")
    ap.add_argument("--implant_epochs", type=int, default=30)
    ap.add_argument("--unlearn_epochs", type=int, default=4)
    ap.add_argument("--optim", choices=["adamw","adafactor","sgd"], default="adamw",
                    help="12GB 卡上跑 1.5B 全参需用 adafactor；换优化器须用同 kind 重跑 0.5B 对照")
    a = ap.parse_args()

    dev = "cuda"
    tag = f'{a.model.split("/")[-1]}_{a.mode}_{a.optim}'
    out = os.path.join(a.out, tag); os.makedirs(out, exist_ok=True)
    imp = os.path.join(out, "implanted")
    resp = os.path.join(out, "results.json")
    res = json.load(open(resp)) if os.path.exists(resp) else {}

    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    forget, retain = load_rows(a.data)
    fitems, ritems = make_items(forget, True), make_items(retain, False)
    print(f"{tag}  forget={len(forget)} retain={len(retain)} "
          f"items={len(fitems)+len(ritems)}", flush=True)

    # ---------------- 植入 ----------------
    if a.stage == "implant":
        m = build(a.model, a.mode, None, dev)
        print("[base] (基线不知道 canary，retain=0 是正常的)"); report("base", m, tok, forget, retain, dev, res, resp, check_retain=False)
        losses = make_losses({}, {}, dev)
        def ce_only(model, inp, att, lab, flag, uids):
            return model(input_ids=inp, attention_mask=att, labels=lab).loss
        print(f"[implant] {a.implant_epochs}ep @ lr=1e-4  mode={a.mode}")
        run_train(m, tok, fitems, ritems, dev, a.implant_epochs, 1e-4, ce_only, "implant", optim=a.optim)
        mm = merged(m, a.mode)
        fg, _ = report("implanted", mm, tok, forget, retain, dev, res, resp)
        if fg < 0.8:
            print(f"\n!! 植入不足 (forget={fg:.3f} < 0.8)。提高 --implant_epochs "
                  f"或（lora 模式）提高 lora_r。不要进入 unlearn 阶段。")
        else:
            print(f"\n植入成功 (forget={fg:.3f})，保存到 {imp}")
            mm.save_pretrained(imp); tok.save_pretrained(imp)
        return

    assert os.path.exists(imp), "先跑 --stage implant"

    # ---------------- 预计算两种参考 ----------------
    m0 = AutoModelForCausalLM.from_pretrained(imp, torch_dtype=DTYPE).to(dev)
    report("implanted", m0, tok, forget, retain, dev, res, resp)
    print("[ref] 预计算 NPO 参考标量 ...", flush=True)
    npo_ref = precompute_npo_ref(m0, tok, fitems + ritems, dev)
    del m0; gc.collect(); torch.cuda.empty_cache()
    print("[ref] 预计算 KL-random 参考 logits ...", flush=True)
    kl_cache = precompute_klrand_ref(a.model, tok, fitems, dev)
    LOSSES = make_losses(npo_ref, kl_cache, dev)

    # ---------------- 三方法遗忘 + 量化 ----------------
    if a.stage == "unlearn":
        for name, (fn, lr) in LOSSES.items():
            print(f"\n[unlearn {name}] mixed-batch, mode={a.mode}")
            m = build(a.model, a.mode, imp, dev)
            run_train(m, tok, fitems, ritems, dev, a.unlearn_epochs, lr, fn, name, optim=a.optim)
            mm = merged(m, a.mode)
            fg, rt = report(f"{name}_unlearned", mm, tok, forget, retain, dev, res, resp)
            if rt < RETAIN_FLOOR:
                print(f"    retain={rt:.3f} < {RETAIN_FLOOR}，模型已塌缩，跳过量化测试")
            else:
                sd = {k: v.clone() for k, v in mm.state_dict().items()}
                for bits in (8, 4):
                    mm.load_state_dict(sd); rtn_quantize(mm, bits)
                    f2, _ = report(f"{name}_quant{bits}bit", mm, tok, forget, retain,
                                   dev, res, resp)
                    print(f"      恢复量 = {f2-fg:+.3f}")
                del sd
            del m, mm; gc.collect(); torch.cuda.empty_cache()

    # ---------------- KL-to-random 超参扫描 ----------------
    else:
        print(f"\n[sweep KLrand] 预设判据 retain>={RETAIN_FLOOR} forget<={FORGET_CEIL}")
        klfn = LOSSES["KLrand"][0]
        for lr, alpha in itertools.product([2e-5, 1e-5, 5e-6, 1e-6], [1.5, 0.3]):
            st = f"KLrand_lr{lr:g}_a{alpha:g}"
            m = build(a.model, a.mode, imp, dev)
            fn = lambda mo, i, at, l, fl, u: klfn(mo, i, at, l, fl, u, alpha=alpha)
            run_train(m, tok, fitems, ritems, dev, a.unlearn_epochs, lr, fn, st, optim=a.optim)
            mm = merged(m, a.mode)
            fg, rt = report(st, mm, tok, forget, retain, dev, res, resp)
            if rt >= RETAIN_FLOOR and fg <= FORGET_CEIL:
                print("      *** 满足预设判据，测量化恢复 ***")
                sd = {k: v.clone() for k, v in mm.state_dict().items()}
                for bits in (8, 4):
                    mm.load_state_dict(sd); rtn_quantize(mm, bits)
                    f2, _ = report(f"{st}_quant{bits}", mm, tok, forget, retain,
                                   dev, res, resp)
                    print(f"      恢复量 = {f2-fg:+.3f}")
                del sd
            del m, mm; gc.collect(); torch.cuda.empty_cache()

    print(f"\n=== 汇总 ({tag}) ===")
    for k, v in res.items():
        print(f"  {k:30s} forget={v['forget']:.3f} retain={v['retain']:.3f} "
              f"{'' if v['retain_ok'] else 'INVALID'}")


if __name__ == "__main__":
    main()
