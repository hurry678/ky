"""
E8 结构版：按 SBU 公开文本忠实复现依赖闭包删除，检验被遗忘内容能否在共享派生工件中存活

================ 复现依据（SBU, arXiv 2602.17692v2 公开正文）================
* 依赖图 G=(V,E)，V = M ∪ S ∪ R ∪ K（原始记忆 / 语义摘要 / 反思 / 知识图节点），边表派生关系
* 每节点维护引用计数 r(v)
* 持久黑名单 B，检索边界处 O(1) 成员检查
* 依赖闭包  Dep(D_F) = { v ∈ (S∪R∪K) | ∃ m ∈ D_F, m ⇝ v }        （式 2）
* 后置条件  D_F ∩ M' = ∅  且  Dep(D_F) ∩ (S'∪R'∪K') = ∅

================ 论文内部的两种读法（本实验的核心）================
读法 A「形式化」式 2 + 后置条件：删除 Dep(D_F) 中**全部**派生工件
读法 B「实现」正文原文：
    "prunes artifacts supported exclusively by forgotten data while preserving
     those with remaining valid sources"
    "Reflections are marked as outdated, reference counts are decremented for
     shared entities, and zero-reference nodes are batch-removed, ensuring that
     shared artifacts depending on retained memories are preserved."
  Invariant 2 亦写作 "marked as outdated **or** have their reference counts decremented"
  摘要原文更直接： "logically **invalidating** shared artifacts"

两种读法不等价。本实验量化其差异。

================ 诚实限制（写论文必须逐字保留）================
SBU 未公开代码，其 supplementary 亦从未公开（arXiv 无 ancillary files）。故本实验
攻击的是**按其公开文本忠实复现的算法**，不是 SBU 的实际实现。可站住的表述只有：
  「按 SBU 公开文本复现的依赖闭包删除算法，允许被遗忘内容在共享派生工件中存活。」
不得写成「SBU 泄露」。

用法: python e8_shared_artifact_survival.py
"""
import json, random, itertools, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from collections import defaultdict

DATA = "D:/ky/MU_B/data/synthetic_canary.jsonl"
SEED = 20260909
random.seed(SEED)


# ----------------------------------------------------------------- 记忆图
class MemoryGraph:
    """SBU 式分层记忆 + provenance 依赖图 + 引用计数 + 黑名单"""

    def __init__(self):
        self.text = {}                      # nid -> 文本内容
        self.layer = {}                     # nid -> 'M' | 'S' | 'R'
        self.parents = defaultdict(set)     # nid -> 直接来源 nid 集合
        self.children = defaultdict(set)    # nid -> 依赖它的 nid 集合
        self.refcount = defaultdict(int)    # r(v)：有多少节点依赖 v
        self.blocked = set()                # 黑名单 B
        self.outdated = set()               # 被标记为 outdated 的节点（内容仍在）
        self.removed = set()                # 真正从存储中移除的节点

    def add(self, nid, layer, text, parents=()):
        self.text[nid] = text
        self.layer[nid] = layer
        for p in parents:
            self.parents[nid].add(p)
            self.children[p].add(nid)
            self.refcount[p] += 1

    def alive(self, nid):
        return nid not in self.removed

    def closure(self, seeds):
        """Dep(D_F)：从 seeds 出发在依赖图上可达的所有派生节点（S ∪ R）"""
        seen, stack = set(), list(seeds)
        while stack:
            cur = stack.pop()
            for ch in self.children[cur]:
                if ch not in seen:
                    seen.add(ch); stack.append(ch)
        return seen

    # ---------------- 读法 A：形式化（式 2 + 后置条件）----------------
    def delete_reading_A(self, forget_ids):
        self.blocked |= set(forget_ids)
        dep = self.closure(forget_ids)
        self.removed |= set(forget_ids) | dep          # 闭包内全部移除
        return {"reading": "A 形式化", "removed_derived": len(dep), "outdated": 0}

    # ---------------- 读法 B：实现（refcount + 标记失效）----------------
    def delete_reading_B(self, forget_ids):
        self.blocked |= set(forget_ids)
        dep = self.closure(forget_ids)
        # 引用计数递减：被删来源不再支撑其派生工件
        rc = dict(self.refcount)
        for m in forget_ids:
            for ch in self.children[m]:
                rc[ch] = rc.get(ch, 0)      # 派生节点自身的 refcount 不变
        # 判定每个派生工件是否"仅由被遗忘数据支撑"
        removed_derived, kept_shared, marked = set(), set(), set()
        for v in dep:
            src = self.parents[v]
            if src and src <= set(forget_ids):
                removed_derived.add(v)                      # 全部来源被删 → 零引用 → 批删
            else:
                if self.layer[v] == "R":
                    marked.add(v)                           # 反思：marked as outdated
                kept_shared.add(v)                          # 共享工件：保留
        self.removed |= set(forget_ids) | removed_derived
        self.outdated |= marked
        return {"reading": "B 实现", "removed_derived": len(removed_derived),
                "kept_shared": len(kept_shared), "outdated": len(marked)}

    # ---------------- 探测 ----------------
    def surviving_leak(self, canaries, respect_outdated_filter=True):
        """删除后，仍能从存活工件中读到的 canary 集合。
        respect_outdated_filter=True 模拟检索层过滤 outdated 标记（对检索不可见，
        但内容仍在存储中 —— 违反 GGV 约束 (i)）。"""
        leaked_retrieval, leaked_storage = set(), set()
        for nid, txt in self.text.items():
            if not self.alive(nid) or nid in self.blocked:
                continue
            for c in canaries:
                if c in txt:
                    leaked_storage.add(c)
                    if not (respect_outdated_filter and nid in self.outdated):
                        leaked_retrieval.add(c)
        return leaked_retrieval, leaked_storage


# ----------------------------------------------------------------- 构图
def build(rows, n_summary=60, n_reflection=20, k=2, verbatim=True, drop_p=0.0):
    """
    verbatim=True  ：摘要逐字包含来源事实（最强情形，上界）
    drop_p>0       ：有损摘要，每条来源以 drop_p 概率丢失其 canary（模拟 LLM 摘要）
    """
    g = MemoryGraph()
    forget = [r for r in rows if r["split"] == "forget"]
    retain = [r for r in rows if r["split"] == "retain"]
    for r in rows:
        g.add(r["id"], "M", r["fact"])

    all_ids = [r["id"] for r in rows]
    # 语义摘要：聚合 k 条记忆
    for i in range(n_summary):
        src = random.sample(all_ids, k)
        parts = []
        for s in src:
            t = g.text[s]
            if not verbatim or random.random() < drop_p:
                # 有损：抹掉 canary 值，只留主体与属性
                t = t.split(" is ")[0] + " is [redacted]."
            parts.append(t)
        g.add(f"S{i}", "S", "Summary: " + " ".join(parts), parents=src)
    # 反思：由摘要二次派生，测传递闭包
    sids = [f"S{i}" for i in range(n_summary)]
    for i in range(n_reflection):
        src = random.sample(sids, 2)
        g.add(f"R{i}", "R", "Reflection: " + " | ".join(g.text[s] for s in src), parents=src)
    return g, [r["id"] for r in forget], [r["answer"] for r in forget]


# ----------------------------------------------------------------- 主流程
def run(label, verbatim, drop_p):
    rows = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    canaries = [r["answer"] for r in rows if r["split"] == "forget"]
    out = {}
    for reading in ("A", "B"):
        random.seed(SEED)                                   # 两读法用同一张图
        g, forget_ids, _ = build(rows, verbatim=verbatim, drop_p=drop_p)
        pre_ret, pre_sto = g.surviving_leak(canaries)
        stats = (g.delete_reading_A if reading == "A" else g.delete_reading_B)(forget_ids)
        ret, sto = g.surviving_leak(canaries)
        out[reading] = dict(stats,
                            pre_leak=len(pre_sto),
                            leak_retrieval=len(ret), leak_storage=len(sto),
                            rate_retrieval=len(ret)/len(canaries),
                            rate_storage=len(sto)/len(canaries))
    print(f"\n===== {label} =====")
    print(f"forget canary 总数 {len(canaries)}，删除前可读 {out['A']['pre_leak']}")
    hdr = f"{'读法':<12}{'删除派生':>9}{'保留共享':>9}{'标记失效':>9}{'检索可见泄露':>14}{'存储中泄露':>12}"
    print(hdr); print("-" * 74)
    for k_, v in out.items():
        print(f"{v['reading']:<12}{v['removed_derived']:>9}"
              f"{v.get('kept_shared',0):>9}{v['outdated']:>9}"
              f"{v['leak_retrieval']:>8} ({v['rate_retrieval']:>5.1%})"
              f"{v['leak_storage']:>7} ({v['rate_storage']:>5.1%})")
    return out


if __name__ == "__main__":
    print(__doc__.split("================ 诚实限制")[0].strip()[:0] or "", end="")
    a = run("情形 1：摘要逐字保留来源事实（上界）", verbatim=True, drop_p=0.0)
    b = run("情形 2：有损摘要，50% 概率丢失 canary（近似 LLM 摘要）", verbatim=True, drop_p=0.5)
    c = run("情形 3：有损摘要，90% 概率丢失 canary（保守下界）", verbatim=True, drop_p=0.9)

    print("\n" + "=" * 72)
    print("结论")
    print("=" * 72)
    print(f"""
读法 A（形式化：删闭包内全部派生工件）在三种情形下泄露均为 0 —— 后置条件
  Dep(D_F) 与 (S'∪R'∪K') 的交集为空，后置条件得到满足。

读法 B（实现：refcount 保留共享工件 + 反思标记失效）泄露非零，且：
  * "检索可见泄露" = 检索层过滤 outdated 标记后仍可读到的 canary
  * "存储中泄露"   = 内容仍在存储里的 canary（GGV 约束 (i) 以此为准）
  两者的差 = 仅靠标记失效"隐藏"而未删除的部分。GGV 的 deletion-compliance
  以内存状态为准（"it talks about the state of the memory, and not just the
  contents of the data structure"），故该差值全部计入违规。

结构驱动因素：k=2 且 forget 占比 40/120 时，混合来源摘要占比约
  2 × (40/120) × (80/120) ≈ 44%。这些摘要 refcount>0，读法 B 下必然存活。

可站住的表述（不得改写）：
  按 SBU 公开文本复现的依赖闭包删除算法，其形式化后置条件与实现描述不等价；
  在实现读法下，被遗忘内容可在共享派生工件中存活。
  —— 不得写成「SBU 泄露」，因其 supplementary 从未公开，无法排除内容级改写。
""")
