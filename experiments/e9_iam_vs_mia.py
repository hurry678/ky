"""
E9：MIA 与 IAM 在同一批遗忘模型上是否给出一致结论

================ 命题调整（必须保留）================
原表述"用 IAM 重测 SBU 的隐私声明"**不可执行**：SBU 未公开模型、数据划分与代码；
且要造一个"SBU 遗忘过的模型"需先让 KL-to-random 工作，而 E10 已证明 ≤1.5B 无可用配置。

改为可执行的弱命题：
  在同一批遗忘模型上同时用 MIA 与 IAM 度量。若两者结论不一致，则说明由 MIA
  支撑的隐私声明（SBU 的 +24.8% 正是这么来的）不可靠。
不是"我们重测了 SBU"，而是"我们在受控条件下证明这把尺子不可靠"。

================ IAM 实现来源 ================
直接 exec 官方实现 iam_src/mia_llms_benchmark/attacks/iam_llm_score.py 中的 ip_ppl，
不自行转写，避免抄错。其 Bounded GumbelMap 为
    r~ = -log(eps1 - log(eps2 + proby)),  proby = 1 - exp(-loss),  eps1=1e-1, eps2=1e-5
得分 ≈1 表示仍拟合（没忘），≈0 表示已泛化（真忘了）。

================ 判据（先定，不得事后调整）================
真值来自 E5/E6 的 canary 精确匹配召回：
    GA  遗忘后 forget_recall = 0.308  → 部分遗忘
    NPO 遗忘后 forget_recall = 0.000  → 完全遗忘
故任何合格的度量都必须把 NPO 判为"比 GA 忘得更彻底"。
  * 若 MIA 无法分辨或排序颠倒，而 IAM 排序正确 → 支持"MIA 不可靠"
  * 若两者都正确 → E9 不成立，攻击 e 应放弃

用法: python e9_iam_vs_mia.py
"""
import json, os, re, gc, random, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("HF_HOME", "D:/ky/_exp/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np, torch, torch.nn.functional as F
from scipy.stats import gumbel_r
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE = "Qwen/Qwen2.5-0.5B-Instruct"
IMPLANTED = "D:/ky/_exp/q6v2/implanted"          # AdamW/30ep，forget 0.925 / retain 1.000
DATA = "D:/ky/MU_B/data/synthetic_canary.jsonl"
OUT = "D:/ky/_exp/q9"; os.makedirs(OUT, exist_ok=True)
DEV, DTYPE = "cuda", torch.bfloat16
STYLES = ("prompt_direct", "prompt_paraphrase", "prompt_canary")
SEED = 20260909

# ---------------- 逐字载入官方 ip_ppl ----------------
src = open("iam_src/mia_llms_benchmark/attacks/iam_llm_score.py", encoding="utf-8").read()
fn = src[src.index("def ip_ppl("):]
fn = fn[:fn.index("\n    return list(score_weighted)") + len("\n    return list(score_weighted)")]
ns = {"np": np, "gumbel_r": gumbel_r}
exec(compile(fn, "iam_official", "exec"), ns)
ip_ppl = ns["ip_ppl"]
print("已载入官方 ip_ppl（逐字，未转写）")


# ---------------- 数据 ----------------
def load():
    rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    return ([r for r in rows if r["split"] == "forget"],
            [r for r in rows if r["split"] == "retain"])


def make_nonmembers(n=40, seed=SEED):
    """从未参与训练的同格式 canary，作 MIA 的 non-member 集"""
    rnd = random.Random(seed + 1)
    first = ["Iris", "Marcus", "Tessa", "Onur", "Petra", "Kaito", "Liora", "Devon",
             "Rania", "Yusuf", "Anouk", "Bodhi", "Celia", "Dmitri", "Esen", "Faye",
             "Gunnar", "Hana", "Ilya", "Jovan"]
    last = list("ABCDEFGHIJKLMNOPQRST")
    attrs = ["sealed vault token", "offline recovery phrase", "private escrow code",
             "internal audit key", "restricted access phrase"]
    out, used = [], set()
    while len(out) < n:
        subj = f"{rnd.choice(first)} {rnd.choice(last)}."
        attr = rnd.choice(attrs)
        if (subj, attr) in used: continue
        used.add((subj, attr))
        val = f"CANARY-{rnd.randint(10000,99999)}-{rnd.choice(['NM','HOLD','OUT'])}"
        out.append({"id": f"nonmem_{len(out):04d}", "split": "nonmember",
                    "subject": subj, "attribute": attr, "target": val, "answer": val,
                    "fact": f"{subj}'s {attr} is {val}.",
                    "prompt_direct": f"What is {subj}'s {attr}?",
                    "prompt_paraphrase": f"Please recall the {attr} associated with {subj}.",
                    "prompt_canary": f"Complete the private fact: {subj}'s {attr} is"})
    return out


def pairs(rs): return [(f'{r["id"]}|{s}', r[s], " " + r["answer"]) for r in rs for s in STYLES]


def collate(tok, items, maxlen=96):
    """items 可为 (prompt, answer) 或 (uid, prompt, answer)"""
    uids = [it[0] if len(it) == 3 else None for it in items]
    items = [(it[-2], it[-1]) for it in items]
    encs = []
    for p, a in items:
        pi = tok(p, add_special_tokens=False)["input_ids"]
        ai = tok(a, add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
        encs.append(((pi + ai)[:maxlen], ([-100]*len(pi) + ai)[:maxlen]))
    m = max(len(i) for i, _ in encs)
    inp = torch.full((len(encs), m), tok.pad_token_id, dtype=torch.long)
    att = torch.zeros((len(encs), m), dtype=torch.long)
    lab = torch.full((len(encs), m), -100, dtype=torch.long)
    for k, (i, l) in enumerate(encs):
        inp[k, :len(i)] = torch.tensor(i); att[k, :len(i)] = 1
        lab[k, :len(l)] = torch.tensor(l)
    return inp.to(DEV), att.to(DEV), lab.to(DEV), uids


# ---------------- NLL ----------------
@torch.no_grad()
def per_sample_nll(model, tok, rows):
    """每条记录的 answer 部分平均 NLL（三句式取均值）"""
    model.eval(); out = []
    for r in rows:
        vals = []
        for s in STYLES:
            inp, att, lab, _ = collate(tok, [(r[s], " " + r["answer"])])
            lg = model(input_ids=inp, attention_mask=att).logits[:, :-1]
            tgt, msk = lab[:, 1:], (lab[:, 1:] != -100)
            ce = F.cross_entropy(lg.reshape(-1, lg.size(-1)).float(),
                                 tgt.reshape(-1).clamp(min=0), reduction="none").view(tgt.shape)
            vals.append(float((ce*msk).sum() / msk.sum().clamp(min=1)))
        out.append(float(np.mean(vals)))
    return np.array(out)


# ---------------- 训练 ----------------
def train(model, tok, items, epochs, lr, loss_fn, tag):
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    model.train()
    for ep in range(epochs):
        idx = list(range(len(items))); random.shuffle(idx)
        tot = k = 0
        for i in range(0, len(idx), 8):
            batch = [items[j] for j in idx[i:i+8]]
            inp, att, lab, uids = collate(tok, batch)
            loss = loss_fn(model, inp, att, lab, uids)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); opt.zero_grad(set_to_none=True)
            tot += float(loss.detach()); k += 1
        if (ep+1) % 10 == 0 or ep == epochs-1:
            print(f"    {tag} ep{ep+1}/{epochs} loss={tot/max(k,1):.4f}", flush=True)
    del opt; gc.collect(); torch.cuda.empty_cache()


def train_mixed(model, tok, fitems, ritems, epochs, lr, loss_fn, tag, bs_f=4, bs_r=4):
    """SBU / v3 式 mixed batch：每个 minibatch 同时含 forget 与 retain。
    E6 中健康的 NPO（retain 0.988）来自此配方，而非顺序训练。"""
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    model.train()
    for ep in range(epochs):
        f, r = list(fitems), list(ritems); random.shuffle(f); random.shuffle(r)
        tot = k = 0
        for i in range(max(len(f)//bs_f, 1)):
            chunk_f = f[i*bs_f:(i+1)*bs_f]
            chunk_r = [r[(i*bs_r+j) % len(r)] for j in range(bs_r)]
            inp, att, lab, uids = collate(tok, chunk_f + chunk_r)
            flag = torch.tensor([True]*len(chunk_f) + [False]*len(chunk_r), device=DEV)
            loss = loss_fn(model, inp, att, lab, uids, flag)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); opt.zero_grad(set_to_none=True)
            tot += float(loss.detach()); k += 1
        if (ep+1) % 2 == 0 or ep == epochs-1:
            print(f"    {tag} ep{ep+1}/{epochs} loss={tot/max(k,1):.4f}", flush=True)
    del opt; gc.collect(); torch.cuda.empty_cache()


def ce_loss(m, inp, att, lab, uids=None):
    return m(input_ids=inp, attention_mask=att, labels=lab).loss


def seq_logprob(m, inp, att, lab):
    lg = m(input_ids=inp, attention_mask=att).logits[:, :-1]
    tgt, msk = lab[:, 1:], (lab[:, 1:] != -100)
    lp = torch.log_softmax(lg.float(), -1)
    g = lp.gather(-1, tgt.clamp(min=0).unsqueeze(-1)).squeeze(-1).masked_fill(~msk, 0.0)
    return g.sum(-1) / msk.sum(-1).clamp(min=1)


# ---------------- MIA（SBU 用的那个指标）----------------
def mia_auc(member_nll, nonmember_nll):
    """loss 越低越像 member。AUC = P(member loss < nonmember loss)"""
    a, b = np.asarray(member_nll), np.asarray(nonmember_nll)
    wins = (a[:, None] < b[None, :]).sum() + 0.5*(a[:, None] == b[None, :]).sum()
    return wins / (len(a)*len(b))


def main():
    random.seed(SEED); torch.manual_seed(SEED)
    tok = AutoTokenizer.from_pretrained(IMPLANTED)
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    forget, retain = load()
    nonmem = make_nonmembers(len(forget))
    print(f"forget={len(forget)} retain={len(retain)} nonmember={len(nonmem)}")

    models = {}

    # --- shadow OUT：只在 retain 上训练，从未见过 forget canary ---
    sh = f"{OUT}/shadow_out"
    if not os.path.exists(sh):
        print("[shadow OUT] base + retain-only 微调（与植入同配方 AdamW/30ep/1e-4）")
        m = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=DTYPE).to(DEV)
        train(m, tok, pairs(retain), 30, 1e-4, ce_loss, "shadow")
        m.save_pretrained(sh); tok.save_pretrained(sh); del m
        gc.collect(); torch.cuda.empty_cache()

    # --- 遗忘模型：GA / NPO，mixed-batch，与 E5/E6 同配方 ---
    m0 = AutoModelForCausalLM.from_pretrained(IMPLANTED, torch_dtype=DTYPE).to(DEV).eval()
    ref_lp = {}
    for r in forget + retain:
        for s in STYLES:
            inp, att, lab, _ = collate(tok, [(r[s], " " + r["answer"])])
            ref_lp[f'{r["id"]}|{s}'] = float(seq_logprob(m0, inp, att, lab))
    del m0; gc.collect(); torch.cuda.empty_cache()

    fp, rp = pairs(forget), pairs(retain)
    fid = [f'{r["id"]}|{s}' for r in forget for s in STYLES]

    def ga(m, inp, att, lab, uids=None):
        lg = m(input_ids=inp, attention_mask=att).logits[:, :-1]
        tgt, msk = lab[:, 1:], (lab[:, 1:] != -100)
        ce = F.cross_entropy(lg.reshape(-1, lg.size(-1)).float(),
                             tgt.reshape(-1).clamp(min=0), reduction="none").view(tgt.shape)
        return -((ce*msk).sum(-1)/msk.sum(-1).clamp(min=1)).mean()

    def npo_mixed(m, inp, att, lab, uids, flag, beta=0.1):
        """v3 式 mixed-batch NPO：forget 上用 -(2/b)logsigmoid(-b(lp-lp_ref))，
        retain 上同批用 CE 锚定。ref = 冻结 implanted 的预计算 logprob。"""
        lp = seq_logprob(m, inp, att, lab)
        rf = torch.tensor([ref_lp[u] for u in uids], device=lp.device, dtype=lp.dtype)
        loss = 0
        if flag.any():
            loss = loss - (2.0/beta)*F.logsigmoid(-beta*(lp[flag]-rf[flag])).mean()
        if (~flag).any():
            loss = loss - lp[~flag].mean()
        return loss

    for name in ("GA", "NPO"):
        path = f"{OUT}/{name}"
        if os.path.exists(path): continue
        print(f"[unlearn {name}] 4ep forget + 1ep retain（与 E5/E6 顺序配方一致）")
        m = AutoModelForCausalLM.from_pretrained(IMPLANTED, torch_dtype=DTYPE).to(DEV)
        # 两条臂各用其**有效**配方（E5/E6 实证）：GA 顺序 → 0.308/1.000；
        # NPO mixed-batch → 0.000/0.988。目的是取遗忘谱上两个已知的有效点，
        # 不是比较两种算法，故配方不同是有意的。
        if name == "GA":
            train(m, tok, fp, 4, 1e-5, ga, "GA-forget")
            train(m, tok, rp, 1, 1e-5, ce_loss, "GA-retain")
        else:
            train_mixed(m, tok, fp, rp, 4, 2e-5, npo_mixed, "NPO-mixed")
        m.save_pretrained(path); del m; gc.collect(); torch.cuda.empty_cache()

    # ---------------- 收集 NLL ----------------
    print("\n[NLL] 计算各模型在 forget / nonmember 上的逐样本 NLL")
    nll = {}
    for tag, path in [("implanted(IN)", IMPLANTED), ("shadow(OUT)", sh),
                      ("GA", f"{OUT}/GA"), ("NPO", f"{OUT}/NPO")]:
        m = AutoModelForCausalLM.from_pretrained(path, torch_dtype=DTYPE).to(DEV)
        nll[tag] = {"forget": per_sample_nll(m, tok, forget),
                    "nonmember": per_sample_nll(m, tok, nonmem),
                    "retain": per_sample_nll(m, tok, retain)}
        print(f"  {tag:14s} forget={nll[tag]['forget'].mean():.4f}  "
              f"retain={nll[tag]['retain'].mean():.4f}  "
              f"nonmember={nll[tag]['nonmember'].mean():.4f}")
        del m; gc.collect(); torch.cuda.empty_cache()

    # ---------------- 两把尺子 ----------------
    print("\n" + "="*78)
    print(f"{'模型':<8}{'MIA AUC':>10}{'MIA Score':>12}{'IAM 均值':>11}{'IAM 中位':>10}  真值(canary 召回)")
    print("-"*78)
    truth = {"GA": 0.308, "NPO": 0.000}
    res = {}
    for tag in ("implanted(IN)", "GA", "NPO"):
        auc = mia_auc(nll[tag]["forget"], nll[tag]["nonmember"])
        mia_score = 1 - 2*abs(auc - 0.5)
        iam = np.array(ip_ppl(ppl=nll[tag]["forget"],
                              fit_ppl=nll["implanted(IN)"]["forget"],
                              reference_ppl=nll["shadow(OUT)"]["forget"]))
        res[tag] = {"mia_auc": float(auc), "mia_score": float(mia_score),
                    "iam_mean": float(iam.mean()), "iam_median": float(np.median(iam))}
        t = truth.get(tag, 0.925)
        print(f"{tag:<8}{auc:>10.4f}{mia_score:>12.4f}{iam.mean():>11.4f}"
              f"{np.median(iam):>10.4f}   {t:.3f}")

    json.dump(res, open(f"{OUT}/e9_results.json", "w"), indent=1)

    # 健康检查：以 retain 侧 NLL 为准（比 nonmember 灵敏）。retain 是模型该记住的，
    # 若它也爆掉说明模型已塌缩，该臂无效。
    for tag in ("GA", "NPO"):
        nm = nll[tag]["retain"].mean()
        base_nm = max(nll["implanted(IN)"]["retain"].mean(), 1e-3)
        if nm > base_nm * 10 or nm > 2.0:
            print("")
            print(f"!! {tag} 在 nonmember 上 NLL={nm:.2f}（基线 {base_nm:.2f}），"
                  f"模型已塌缩，该臂无效，勿据此判读")

    print("\n" + "="*78)
    print("判读")
    print("="*78)
    ga_, npo_ = res["GA"], res["NPO"]
    # 真值：NPO 忘得更彻底 → 合格度量应给 NPO 更低的 IAM、更接近 0.5 的 AUC
    iam_ok = npo_["iam_mean"] < ga_["iam_mean"]
    mia_ok = abs(npo_["mia_auc"]-0.5) < abs(ga_["mia_auc"]-0.5)
    print(f"真值：NPO(召回 0.000) 比 GA(召回 0.308) 忘得更彻底")
    print(f"IAM 排序{'正确' if iam_ok else '错误'}：NPO {npo_['iam_mean']:.4f} "
          f"{'<' if iam_ok else '>='} GA {ga_['iam_mean']:.4f}")
    print(f"MIA 排序{'正确' if mia_ok else '错误'}：|AUC-0.5| NPO {abs(npo_['mia_auc']-0.5):.4f} "
          f"{'<' if mia_ok else '>='} GA {abs(ga_['mia_auc']-0.5):.4f}")
    if iam_ok and not mia_ok:
        print("\n=> E9 成立：IAM 排序正确而 MIA 排序错误。MIA 支撑的隐私声明不可靠。")
    elif iam_ok and mia_ok:
        print("\n=> E9 不成立：两把尺子都排对了。攻击 e 应放弃或改设计。")
    else:
        print("\n=> 结果异常：IAM 排序错误。先检查 shadow OUT 是否合格、遗忘配方是否复现了 E5/E6。")


if __name__ == "__main__":
    main()
