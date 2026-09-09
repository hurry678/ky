# 文献检索清单（供内网大模型检索下载）

- 生成：2026-09-09
- 用途：补齐 `roadmap-2026-09-09.md` 与 `formalization-draft-2026-09-09.md` 的文献缺口
- 已有文献见 `可撤销记忆_文献_2026-09-08/` 与按会议分类的目录（NDSS / S&P / TIFS / TDSC / USENIX / NeurIPS / SaTML / NMI）
- **标注说明**：🔴 阻塞性，缺了会导致论文被质疑；🟡 需要，补强论证；🟢 可选，锦上添花
- **置信度**：多数篇目我有较高把握确实存在，但**标题与年份请以检索结果为准**，不要直接引用本清单的写法

---

## A. 🔴 最高优先：secure deletion / assured deletion 这条线

**这是本清单最重要的一块，也是我此前的遗漏。**

此前我只把"加密删除"归为工业实践（AWS KMS 那类），未给学术出处。但"销毁密钥以实现删除"在存储安全领域有二十余年积累。**不读这条线，创新点 2 会遭到一个致命的学术质疑：「secure deletion 领域早已做过密钥销毁式删除，你的新意何在？」** 必须先读、再在相关工作中明确划出差异（它们的对象是文件与存储块，没有 LLM 派生记忆、没有向量索引、没有用户持份密钥）。

### 必读篇目

| 篇目 | 说明 |
|---|---|
| **Reardon, Basin, Capkun, "SoK: Secure Data Deletion", IEEE S&P 2013** | 该领域的系统化综述，**从这一篇入手**。它会给出完整的分类法与已有方案谱系 |
| **Boneh & Lipton, "A Revocable Backup System", USENIX Security 1996** | 加密删除思想的源头 |
| **Perlman, "The Ephemerizer: Making Data Disappear"（2005，Sun 技术报告）** | 用密钥过期实现文件消失 |
| **Geambasu et al., "Vanish: Increasing Data Privacy with Self-Destructing Data", USENIX Security 2009** | 密钥分散到 DHT 实现自毁；其失败分析亦有价值 |
| **Cachin, Haralambiev, Hsiao, Sorniotti, "Policy-based Secure Deletion", ACM CCS 2013** | 基于策略的删除，与"作用域→密钥"映射最接近 |
| **Tang, Lee, Lui, Perlman, "FADE: Secure Overlay Cloud Storage with File Assured Deletion"（SecureComm 2010 前后）** | 云存储场景的 assured deletion |

### 检索关键词

```
"secure deletion" / "assured deletion" / "secure data deletion"
"crypto shredding" / "cryptographic erasure" / "crypto-erasure"
"revocable storage" / "self-destructing data" / "data expiration"
"key destruction" AND deletion
"assured deletion" AND (cloud OR outsourced)
"secure deletion" AND survey
```

### 读的时候要回答的三个问题（直接写进相关工作）

1. 它们的删除对象是什么粒度？（文件 / 块 / 记录）—— 本文是**记忆条目 + 其 LLM 派生工件**
2. 密钥由谁持有？—— 已有方案基本是服务方或可信第三方；**本文是数据主体持份**
3. 有没有处理"派生数据"与"检索索引"？—— 预期为没有，这正是差异化落点

---

## B. 🔴 已知具体篇目但尚未下载

| 篇目 | 用途 | 备注 |
|---|---|---|
| **Zhang et al., "Catastrophic Failure of LLM Unlearning via Quantization", ICLR 2025** | **攻击 d 的直接依据** | MU_B 笔记称其为主线最关键依据，但文献夹里没有。必须补 |
| **"Unlearning or Obfuscating? Jogging the Memory of Unlearned LLMs via Benign Relearning"** | 攻击 d 的第二条部署变换（benign relearning） | 标题取自 MU_B 笔记；作者与年份待检索确认 |
| **"Towards Effective Evaluations and Comparisons for LLM Unlearning Methods"** | 遗忘评估方法学 | MU_B 笔记第 2 篇，文献夹缺 |
| **Green & Miers, "Forward Secure Asynchronous Messaging from Puncturable Encryption", IEEE S&P 2015** | 可穿刺加密（用户侧种子的依据） | IEEE 付费墙。**替代公开源**：IACR ePrint 2020/882 `Puncturable Encryption: A Generic Construction from Delegatable...` |
| **Micciancio, "Oblivious Data Structures: Applications to Cryptography", STOC 1997** | GGV 引用的 [Mic97]，**攻击 c 形式化表述要引它** | 与下一条同为 history-independence 的原始出处 |
| **Naor & Teague, "Anti-persistence: History Independent Data Structures", STOC 2001** | GGV 引用的 [NT01] | 同上 |
| **Xu et al., "Beyond Goldfish Memory: Long-Term Open-Domain Conversation", ACL 2022** | MSC 数据集（LoCoMo 的备选） | 数据集来源 |
| **Morris et al., "Language Model Inversion", ICLR 2024** | vec2text 的后续工作，攻击 b 需覆盖 | 同组作者 |
| **Carlini et al., "Quantifying Memorization Across Neural Language Models", ICLR 2023** | canary / 记忆化度量的标准引用 | 文献夹只有 2021 的 Extracting Training Data |

---

## C. 🟡 创新点 2 的密码侧补强

### C1 可穿刺 PRF / 约束 PRF

```
"puncturable PRF" / "puncturable pseudorandom function"
"constrained PRF" / "delegatable PRF"
"puncturable encryption" AND (construction OR efficient)
GGM AND "pseudorandom function" AND tree
"forward secure" AND (encryption OR messaging) AND puncturable
```
- Sahai & Waters；Boneh & Waters "Constrained PRFs"；GGM 1986（已有）
- 目的：为"用户侧可穿刺种子"找到可实现、可引用的构造与开销分析

### C2 秘密共享用于访问撤销

```
"secret sharing" AND (revocation OR "access revocation")
"threshold encryption" AND deletion
"user-held key" OR "client-side key" AND (deletion OR erasure)
"client-side encryption" AND "right to be forgotten"
"key escrow" AND revocation
```
- 目的：确认"用户持份使平台单方不可解密"是否已有人做过（**这是 E1 的持续风险点，必须查**）

### C3 删除的形式化定义（GGV 的上下游）

```
"formalizing data deletion" / "deletion compliance"
"right to be forgotten" AND (definition OR formal OR cryptographic)
"provable deletion" / "certified deletion"
"deletion as confidentiality"
```
- 注意区分 **quantum certified deletion**（Broadbent-Islam 那条线）——GGV 脚注提到但不适用本文场景，需在相关工作中据此排除
- 目的：找 GGV 之后引用它的工作，看有没有人已经扩展到派生数据 / ML 场景

---

## D. 🟡 攻击侧补强

### D1 embedding / 向量索引隐私

```
"embedding inversion" / "text embedding inversion"
"embedding leakage" / "information leakage" AND embedding
"vector database" AND (privacy OR attack OR leakage)
"RAG" AND (privacy attack OR data extraction)
"nearest neighbor" AND privacy AND leakage
"deletion" AND "vector index"
```
- 已有：vec2text（EMNLP 2023）、Song & Raghunathan（CCS 2020）
- 目的：攻击 b 的相关工作要完整；特别关注**有没有人做过"删除后向量残留"**

### D2 遗忘的脆弱性 / 恢复攻击

```
"unlearning" AND (quantization OR "post-training" OR "deployment")
"relearning attack" AND unlearning
"unlearning" AND (fragile OR failure OR "does not work")
"knowledge recovery" AND unlearning
"unlearning" AND (robustness OR "adaptive attack")
```
- 已有：NeurIPS 2025 `Machine Unlearning Doesn't Do What You Think`、SaTML `Inexact Unlearning Needs More Careful Evaluations`
- 目的：攻击 d 的相关工作；确认"遗忘越彻底越脆"这个观察有没有人报过

### D3 Agent 记忆安全（持续监控用，见 F 节）

```
"agent memory" AND (security OR privacy OR poisoning OR deletion)
"long-term memory" AND "LLM agent" AND (attack OR defense)
"memory poisoning" AND agent
"persistent memory" AND (agent OR assistant) AND privacy
```

---

## E. 🟢 合规与绪论用

```
GDPR AND "Article 17" AND (technical OR implementation OR enforcement)
"个人信息保护法" AND 删除权
"right to erasure" AND (technical measures OR compliance)
"right to be forgotten" AND "machine learning" AND (survey OR review)
"data minimization" AND LLM
```
- 目的：绪论的法规动机；创新点 2 对"个保法 47 条"的映射要有出处，不能只凭条文原文

---

## F. 🔴 窗口监控（每两周跑一次，直到 2027 年暑假）

**roadmap 中标注窗口只剩 3–6 个月。以下组合用于尽早发现"有人做了加密删除式 Agent 记忆"这个唯一能整体击穿方向的风险。**

```
("agent memory" OR "long-term memory") AND (encryption OR "key destruction" OR "crypto erasure")
("agent memory" OR "LLM agent") AND unlearning
"verifiable deletion" AND (agent OR LLM OR memory)
"user-controlled" AND (deletion OR erasure) AND (LLM OR agent)
"agentic unlearning"
```
- 检索源建议：arXiv（cs.CR + cs.CL + cs.LG）、IACR ePrint、Google Scholar 的"引用 SBU / 引用 GGV / 引用 2604.16548"三条引文链
- **引文链比关键词更灵敏**：新工作一定会引 SBU 或那篇 2026-04 综述

---

## G. 检索执行建议

1. **A 节优先，且优先于继续做实验。** 它决定创新点 2 的差异化表述能不能立住，是当前唯一的结构性风险。
2. 每篇下载后记录：**它的删除对象粒度 / 密钥持有方 / 是否处理派生数据**——这三列直接生成相关工作的对比表。
3. 付费墙篇目先找 arXiv、IACR ePrint、作者主页、机构 DSpace（Shamir 与 GGM 就是从 MIT DSpace 拿到的）。
4. 检索结果请连同**检索式与命中数**一起记录。上一轮的教训：Kimi 只用 arXiv 标题+摘要检索就断言"交叉点为空"，漏掉了 TIFS / TDSC 上成片的可验证遗忘工作，导致初稿两个创新点被 SBU 占据而未被发现。**期刊必须单独检索，不能只搜 arXiv。**
5. 本清单的标题与年份**须以检索结果核对为准**；如某篇检索不到，先记为"未确认"，不要凭清单写法引用。
