# 创新点 2 的形式化骨架：从 GGV deletion-compliance 到 Agent 记忆

- 起草：2026-09-09
- 依据：Garg, Goldwasser, Vasudevan, *Formalizing Data Deletion in the Context of the Right to be Forgotten*（Eurocrypt 2020 / IACR 2020-254）
- 状态：**工作稿**。已实读原文 §1–§2.1，尚未读 §2.2–§2.4（建模选择、弱化定义、组合性）与 §3（实例）
- 定位：路线 A 锁定后，本文件是创新点 2 学术分量的关键路径（见 `roadmap-2026-09-09.md` G1）

---

## 1. GGV 给了什么

### 1.1 定义形态

**deletion-compliance** 是模拟式（real / ideal）定义，建模工具借自 UC 框架，各方为 Interactive Turing Machine。

- **real world**：deletion-requester 与 data collector 交互，提供数据后请求删除
- **ideal world**：deletion-requester 不与 collector 交互（数据从未被提供）
- **要求**：删除请求处理完后，collector 的**存储状态**与它**对其他各方的通信**，在两个世界间统计接近

核心口号：**leave no trace** —— 执行删除后的系统状态应等价于"这份数据从未被提供过"的状态。

### 1.2 三条派生约束 → 直接对应本文三个攻击

| GGV 约束 | 原文依据 | 对应 |
|---|---|---|
| (i) 数据本身不得在 collector 内存中留存 | §1 "the data that is requested to be deleted should no longer persist in the memory of the data-collector" | **攻击 c** |
| (ii) 必须移除其他数据对被删数据的依赖 | §1 "the data-collector must also remove the dependencies that other data could have on the data that is requested for deletion... **we diverge from the GDPR in this sense, as it only requires deletion of data rather than what may have been derived from it via processing**" | **攻击 a** |
| (iii) collector 不得向任何外部实体透露所收集的数据 | §1 "the data-collector cannot reveal any data it collects to any external entity... on sharing user data with an external entity, the data-collector loses its ability to ensure that the data can be deleted" | **本文"推理必须在本地"的作用域限制** |

约束 (iii) 原本是凭直觉加的前提，现在是从定义推出的必要条件。**GGV §2.3 给了一个弱化版定义**，覆盖"与外部实体共享但尽力转发删除请求"的 collector —— 若将来要放开本地推理前提，应走那条弱化定义，需精读。

### 1.3 两条可直接引用的权威支撑

**(A) 向用户证明删除一般不可能**

> we do not attempt to develop methods by which a data collector could prove to a user that it did indeed delete the user's data. As a remark, we note here that **this is in fact impossible in general**, as a malicious data collector could always make additional secret copies of user data.

用途有二：① 支撑本文把"恶意平台删除前已导出明文"显式声明出范围——这不是回避，是该领域的标准立场；② 支撑对哈希链 / Merkle 审计式方案的批评（Kimi 初稿的创新点 2、SBU 的 tamper-evident log）——它们证明不了删除，而这不是实现问题。

其脚注亦列出可证明删除的特例条件：存储受限假设 `[PT10, DKW11, KK14]`、量子数据 `[CW19, BI19]`。**均不适用于本文场景，可在相关工作中据此排除。**

**(B) 敌手模型：honest-but-possibly-buggy**

> by honest we mean a data collector that does in fact intend to guarantee its users' right to be forgotten in the intuitive sense... Our question is about how it can tell whether the algorithms and mechanisms it has in place are in fact working correctly.

与本文 §3 威胁模型落定的位置完全一致：覆盖"平台诚实执行但有清不干净的副本 / 派生 / 索引"，不覆盖恶意平台。

**(C) history-independence 要求 —— 攻击 c 可据此升级**

> care has to be taken to use implementations of data structures that do not inadvertently preserve information about deleted data in their metadata. This follows from our definition as it talks about the state of the memory, and not just the contents of the data structure. Such requirements may be satisfied, for instance, by the use of **"history-independent" implementations of data structures** `[Mic97, NT01]`

mem0 的 `history` 表（`old_memory` / `new_memory` 明文列 + `is_deleted` 标记位 + 无按主体清除接口）是 history-independent 的字面反面。

**攻击 c 的表述因此升级为**：

> mem0 的 `delete()` 在 GGV deletion-compliance 意义下不满足约束 (i)，因其 history 表非 history-independent：被删记忆的明文以 `old_memory` 留存，且公开 API 无按主体清除手段。

这个表述**不声称漏洞**（history 是文档化特性），但违反的是一个 Eurocrypt 2020 的形式定义。比"设计缺口"强得多，且不需要厂商承认。

**(D) diligence / book-keeping —— provenance 图是定义推出的必需品**

> our definitions implicitly require the data-collector to keep track of how it is using each user's data. In fact, this book-keeping is essential for deletion-compliance. After all, how can a data-collector delete a user's data if it does not even know where that particular user's data is stored?

因此本文的 provenance 图不是设计选择，而是 deletion-compliance 的必要条件。**答辩时"你为什么要建 provenance 图"有形式化答案。**

**(E) 组合性**

> under an assumption that different users operate independently of each other, a data collector that is deletion-compliant for a deletion request from a single user is also deletion-compliant for requests from (polynomially) many users

可支撑"按作用域销毁密钥"的组合性论证。**具体条件需精读 §2.4。**

**(F) 参数层可作为组件接入**

> recent work has investigated the question of data deletion in machine learning models, and this can be used to construct a data collector that learns such a model based on data given to it, and can later delete some of this data not just from its database, but also from the model itself

即攻击 d 所在的参数层在 GGV 框架内是一个合法组件，不是框架外的东西。

---

## 2. Agent 记忆场景下需要改写的三处

GGV 的 collector 被动接收数据并执行删除，其 §3 实例是简单数据库、history-independent 数据结构、ML 模型。Agent 长期记忆有三处它未覆盖，这三处就是本文的改写贡献。

### 改写 1 · collector 自主派生，且派生不可逆

Agent 会自主产生摘要、反思、用户画像。与 GGV 实例中的确定性派生不同，**LLM 派生是有损且不可逆的**——一条聚合了多源的摘要无法"反派生"出去除某源的版本，只能整体删除或从保留集重新生成。

因此约束 (ii) 在 Agent 场景下强化为一个二选一：

> 对任一派生工件 v，若其 provenance 闭包与删除集相交，则 v 必须被删除，或从 provenance 闭包减去删除集后的保留集**重新派生**。仅标记 v 为失效不满足约束 (ii)。

- 本文架构满足：provenance 闭包 → 穿刺（密文不可解，等价于删除）
- **SBU 违反**：其实现以 refcount>0 保留共享工件、反思仅 "marked as outdated"，摘要原文即 "logically **invalidating** shared artifacts"。而其形式化后置条件 `Dep(D_F) ∩ (S'∪R'∪K') = ∅` 又要求全删——形式化与实现自相矛盾，矛盾的那一侧违反约束 (ii)

### 改写 2 · 向量索引是落在 metadata 条款下的派生态，且可反演

GGV 的 metadata / history-independence 条款是定性的。Agent 记忆给出一个**可定量的实例**：向量索引中的 embedding 是删除后残留的 metadata，而它并非不可逆——

本文攻击 b 实测（`gtr-t5-base` + vec2text，steps=20/beam=4）：token F1 **0.983**、PII 片段召回 **0.950**、归一化空白后 **7/8** 逐字恢复。

> 因此"删除明文条目但保留其 embedding"不满足约束 (i)：被删数据可从残留 metadata 以高保真度恢复。

**这是对 GGV metadata 条款的一个定量填充**，而非仅仅援引。SBU 的 `|B|>τ=100` 才重建索引意味着最多 100 条已删记忆的 embedding 常驻——落在此条之下。

### 改写 3 · 用户持有密钥材料 —— 相对 GGV 的真正新角度

GGV 的模型中**删除由 collector 执行**，用户是请求方；而 GGV 明确指出向用户证明删除一般不可能。本文的用户持份改变了这个结构：

> 在 2-of-2 密钥共享下，collector 单方无法解密。用户销毁自己的份额后，collector 对该作用域的**未来访问能力**被移除，且此移除不依赖 collector 的诚实执行。

关键在于把两件事分清楚——**这段是全篇最需要精确措辞的地方**：

| | 能否做到 | 依据 |
|---|---|---|
| 证明 collector 未在删除前私存副本 | **不能** | GGV：一般不可能 |
| 移除 collector 未来解密该作用域的能力 | **能，且不依赖信任** | 用户份额销毁后，密文无法解密 |

因此本文的定位不是"实现了 GGV 意义下对恶意 collector 的删除"（那不可能），而是：

> **把 leave-no-trace 从"collector 需被信任去执行"改造为"用户可单方面强制未来不可访问"。** 这是对 GGV 敌手模型的一个正交强化：不扩大可证明的范围，而是缩小需要被信任的一方。

⚠️ **不得**写成"实现了对恶意平台的可验证删除"——那与 GGV 的不可能性结论直接冲突，会被一击击穿。

---

## 3. 待办

- [ ] 精读 GGV §2.2（建模选择与隐含假设）—— 确认本文的 Agent 记忆建模是否落在其假设内
- [ ] 精读 GGV §2.3（共享数据的弱化定义）—— 若将来放开"本地推理"前提，须走这条
- [ ] 精读 GGV §2.4（组合性的具体条件）—— 支撑按作用域销毁密钥的组合论证
- [ ] 精读 GGV §3（实例与陷阱）—— 其"genuine attempts 仍失败"的案例可能直接对上 SBU / mem0
- [ ] 查 `[Mic97, NT01]` history-independent 数据结构原文 —— 攻击 c 的形式化表述需引准确
- [ ] 写出 Agent 记忆场景下 deletion-compliance 的正式定义（real/ideal 执行 + 统计距离），把改写 1–3 形式化
- [ ] 写穿刺后不可区分性的 game-based 归约（→ PRG + AEAD 安全性）
- [ ] 写用户持份下"collector 单方不可解密"的归约（→ 秘密共享安全性）
