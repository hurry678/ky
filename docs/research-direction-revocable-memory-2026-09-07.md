# 研究方向定稿：Agent 记忆删除的密码学机制与残留评估

- 定稿日期：2026-09-08（初版 2026-09-07）
- 前置文档：`research-direction-agent-memory-unlearning-2026-09-07.md`（Kimi 版初稿，已废弃）
- 相关工作区：`MU_A/`（废弃）、`MU_B/`（并入创新点 1 攻击 (d)）
- 本文性质：经 60 篇文献实读验证后的定稿，可直接用于开题

---

## 1. 方向定稿

**论文题目**：《大模型智能体记忆删除的密码学机制与残留评估研究》

**中心论点**（写进结论与讨论，不要写成创新点）：

> Agent 记忆的遗忘在部署条件下失效——参数侧的软抑制经量化塌回，记忆侧的逻辑删除留在存储里。可靠的补救是把删除下沉到密码层，并把密钥交给用户。

**两个创新点**：

| | 内容 | 定位 |
|---|---|---|
| 创新点 1 | 对 Agent 记忆遗忘机制的残留攻击与再度量（五个攻击） | 基线是已发表 SOTA（SBU、MemSecBench），非自建假想系统 |
| 创新点 2 | Verified Forgetting 原语的密码学实例化：加密删除 + 用户持份密钥 | 补一个被 2026 综述公开认定的空缺 |

---

## 2. 文献定位（已逐篇验证，非关键词检索结论）

### 2.1 创新点 1 的基线：SBU

`Agentic Unlearning: When LLM Agent Meets Machine Unlearning`（arXiv 2602.17692v2，IJCAI 格式，山东中医药大学 + 山大）提出 SBU，**已占据初稿设计的绝大部分**：

分层记忆建模、provenance 依赖图 + 引用计数、依赖闭包级联删除、向量表示删除 + 索引重建、**哈希链防篡改审计日志**、参数遗忘（KL-to-random，优于 GA/NPO）、MIA 隐私度量、Agent Loop（Store→Query→Delete→Probe）评估、三种记忆侧基线对比（Naive Deletion / Re-indexing / Retraining Oracle）。

**结论：Kimi 初稿的两个创新点均被此文占据。** 但 SBU 全文**零密码原语**，删除完全信任平台执行。

**关键事实**：该文正文五次前向引用 supplementary material（含"cryptographic verification"），但 arXiv 页面标注 "9 pages, 6 figures, 6 tables"、**无 ancillary files——附录从未公开**。因此其密码声明在任何公开文档中不存在，且洞 (a) 无法被附录反驳。

### 2.2 创新点 2 的差异化：验证 vs 执行

已实读 7 篇可验证/可审计遗忘论文，关键词扫描 `crypto-erase / key destruction / puncturable / secret sharing / encrypt`：**全部零命中**（两处 "Secret Sharer" 是 Carlini 记忆化论文的引用，非秘密共享原语）。

| 机制家族 | 论文 | 验证什么 |
|---|---|---|
| TEE 见证执行 | TIFS `Proof of Unlearning`（TEE ×73）、USENIX `On the Necessity of Auditable Algorithmic Definitions`（×10） | 平台是否真跑了遗忘流程 |
| ZK / 承诺证明 | SaTML 2025 `Verifiable and Provably Secure MU`（ZK ×46、commitment ×28） | 遗忘计算是否正确 |
| 行为探针 / 后门 / MIA | TIFS `TruVRF`、TIFS `Verifying in the Dark`、TDSC `Really Unlearned?` | 从模型行为反推是否忘了 |

**差异化一句话**：

> 现有工作都在**验证平台是否遗忘**（TEE 见证 / ZK 证明 / 行为探针），数据主体始终是被动请求方。本文把删除做成**由构造保证的执行机制**，并把密钥能力交给数据主体，使删除不依赖对平台的验证。

"验证 vs 执行"是正交轴，非抠字眼。

### 2.3 2026 综述已把本方向点为公开缺口

`A Survey on Long-Term Memory Security in LLM Agents: Attacks, Defenses, and Governance Across the Memory Lifecycle`（arXiv 2604.16548v2，MemTensor + 上交）。**注意：文件名里的 "Mnemonic Sovereignty" 是错的，全文无此词。**

它提出六阶段生命周期框架与 **VMG（Verifiable Memory Governance）五原语**：Write Authorization、Provenance Visibility、Principal-Scoped Retrieval、Rollbackability、**Verified Forgetting**。五条**全部非密码**。

可直接引用的三句结论：

- "highlight key gaps in provenance infrastructure, cross-principal propagation, and **post-deletion verification**"
- "defenses at the **store, share, and forget** phases remain comparatively **sparse**"
- "LTM security cannot be retrofitted at retrieval or execution time alone, but must be **anchored in storage-time** provenance, versioning, and policy-aware retention"

第三句正是创新点 2 反对 SBU 黑名单式逻辑删除的论证。

**⚠️ 表述纪律**：`Verifiable Memory Governance` 这个框架名已被占，`Verified Forgetting` 已是其第五原语（带 predicate 定义与度量）。**创新点 2 不得表述为"提出可验证记忆治理框架"**，须表述为：

> 综述规定了 Verified Forgetting 应满足什么，但未给出机制，并将 post-deletion verification 列为公开缺口。本文给出其**密码学实例化**。

补一个公开认定的空缺，比自立概念更稳。

### 2.4 其余五篇（均不构成威胁）

| 论文 | 扫描结果 | 结论 |
|---|---|---|
| `Selective Forgetting`（2026-08） | unlearn ×2，无 delete / provenance / 密码 | **性能驱动的记忆管理，非隐私删除。** 初稿的怀疑成立 |
| `MemSecBench`（2026-07） | delete ×11、provenance ×10，无密码 | **第二基线，且方法论有同样的洞**（见 §5） |
| `AgentLeak`（2026-02） | encrypt ×2，无 unlearn / delete | 多智能体泄露评测，非删除 |
| S&P `Unlearning Inversion Attacks` | unlearn ×174，无 embedding inversion / vec2text | 反演对象是**模型更新前后权重**，非向量索引。攻击面不同，但需在相关工作显式区分 |
| USENIX 2025 `Towards Lifecycle Unlearning Commitment Management` | 无 quantiz / relearn | 实为 **IAM 度量方法**，见 §5(e)。既不威胁创新点 2 也不威胁攻击 (d)，反而提供工具 |

---

## 3. 威胁模型与作用域

### 敌手模型

| 敌手 | 是否覆盖 | 手段 |
|---|---|---|
| 平台诚实执行，但存在无法枚举的副本 / 备份 / 快照 | ✅ 密码学保证 | 加密删除：销毁密钥使所有副本失效 |
| 事后获得存储介质的外部攻击者 / 内部人员 / 拖库 | ✅ 密码学保证 | 同上 |
| 平台拒不删除、想保留未来访问能力 | ✅ 部分保证 | 用户持份：平台无用户份无法解密 |
| 平台在会话期缓存明文 | ❌ | 声明为已知残留窗口，实测窗口大小 |
| 恶意平台在删除前已导出明文 | ❌ | 仅问责日志事后追责；无 ZKP/TEE 无法解决，**显式声明出范围** |

**诚实点**：加密删除不是消除信任，而是把删除问题**归约**为"销毁一个 32 字节根种子"（可放 TPM / 仅驻内存）。写成归约而非消除才站得住。

### 作用域

- **推理必须在本地**。明文送外部 LLM API 则该拷贝的加密删除无意义。4090 + Letta 本地模型满足此前提，论文须明写。
- 主实验英文（受 vec2text 已发布 inverter 限制），中文场景以小 case study 覆盖。

---

## 4. 架构设计

### 4.1 采用综述的六阶段词汇（替换初稿自造的 L0–L5）

| 阶段 | 保证强度 | 本文机制 / 攻击 |
|---|---|---|
| WRITE | — | 不在本文范围 |
| **STORE** | **密码学保证** | 加密删除 + 用户持份（创新点 2 主战场） |
| **STORE**（向量表示） | 无 | 攻击 (b) embedding 反演 |
| RETRIEVE | 无 | 攻击 (c) 黑名单只是检索边界过滤 |
| EXECUTE | 无 | 会话期明文窗口（声明出范围） |
| SHARE & PROPAGATE | 无 | stretch，不做主线 |
| **FORGET & ROLLBACK** | 部分 | 攻击 (a) 共享派生工件存活 |
| 参数侧（综述六阶段**未覆盖**） | 无 | 攻击 (d) 量化 / 再学习恢复 ← 本文对综述框架的扩展 |

### 4.2 密钥架构

```
用户设备                          平台
--------                          ----
user_seed (可穿刺 GGM 树根)        platform_share
     |                                  |
     +--- user_share[scope] ------+-----+
                                  |
                            KEK[scope] = combine(user_share, platform_share)   (2-of-2)
                                  |
                            DEK[entry] (AEAD 加密记忆条目)
```

- **2-of-2 秘密共享**：平台单独持 `platform_share` 无法解密；会话期用户设备参与释放 KEK。
- **用户侧可穿刺种子**：用户设备存储受限，不能存 n 份 per-scope 份额，故持一个小种子，"删除关于主题 X 的记忆"= 穿刺该子树。**可穿刺 PRF 只在用户侧有正当理由**（平台侧扁平密钥表更优，见 §10 Q1）。
- **删除 = 用户单方面穿刺自己的份额**，不需相信平台。
- provenance 图决定穿刺集合；穿刺**原子地**失效对应 embedding（不等 τ 阈值）。
- 哈希链 + Merkle 承诺仅做**问责层**，不承担"证明删除"职责（该职责 SBU 已占且做不到）。

---

## 5. 创新点 1：五个攻击

### 统一骨架（防"实验拼盘"）

同一 canary 集 + 同一攻击者预算定义 + 同一可恢复性指标，逐攻击套用。否则被评成"工作量够但不成体系"。

### (a) 共享派生工件按设计保留遗忘内容 —— 最好的靶子

SBU 的形式化（式 2 + 后置条件 `Dep(D_F) ∩ (S'∪R'∪K') = ∅`）要求删除闭包内**全部**派生工件。但实现是"preserving those with remaining valid sources"、引用计数减一、refcount 归零才删、反思仅 "marked as outdated"。**摘要原文即 "logically invalidating shared artifacts"——逻辑失效不是删除。** 其 Invariant 2 写的是 "marked as outdated **or** decremented"，已自认工件存活。

**形式化后置条件与实现自相矛盾，矛盾的那一侧就是泄露。** 一条由 {遗忘 m1, 保留 m2} 共同派生的摘要 refcount>0 → 存活 → 仍带 m1 内容。

实验：构造聚合遗忘+保留记忆的摘要，跑其删除，探测存活摘要。

**MemSecBench 有同样的洞**：F1 判定是 "removal **or neutralization**"，中和也算成功；且判定由 judge model 读后端状态，**不检查向量索引**。

### (b) 索引陈旧窗口 + embedding 反演 —— ✅ 已实测确认

SBU 仅在 `|B|>τ=100` 时重建索引 → **最多 100 条已删记忆的 embedding 常驻索引**。其实现用 `text-embedding-ada-002`（1536 维）——**正是 vec2text 有公开 inverter 的两个 encoder 之一**，可在其原始配置上直接反演。

佐证：SBU 自己的表 5 显示单靠 Re-indexing，MIA AUC 仅降至 0.5180，仍高于 Oracle 0.5020。

**2026-09-08 实测结果**（`_exp/test_vec2text_inversion.py`，encoder = `gtr-t5-base`，8 条 Agent 记忆式 PII，RTX 5070）：

| 配置 | 耗时 | exact（归一化空白） | token F1 | PII 片段召回 |
|---|---|---|---|---|
| steps=0（单次反演） | 1s | 0/8 | 0.518 | — |
| steps=20（迭代校正） | 5s | — | 0.964 | — |
| **steps=20 + beam=4** | **28s** | **7/8** | **0.983** | **0.950** |

仅从 embedding 即可逐字恢复 HIV 检测结果、家庭住址、子女病情、薪资、用药、银行 PIN 提示。唯一失败项是日期数字被打乱（`2026-03-14` → `2026-28-04`），语义仍暴露。

**结论：攻击 (b) 作为主武器成立，无需降级方案。** 下一步换 ada-002 对齐 SBU 原始配置（需 OpenAI key）。

与 S&P `Unlearning Inversion Attacks` 的区分：对方反演模型更新前后权重，本文反演向量索引中的 embedding。

### (c) 存储层残留 —— ✅ 已在 mem0 生产代码中实测确认

黑名单在检索边界过滤，数据仍在库中；SBU 的 MIA 度量的是**模型**泄露，完全未覆盖存储层。

**2026-09-08 读 mem0 源码（main 分支）+ 实测复现，发现比 SBU 更有分量的目标：**

`mem0/memory/main.py:2100 _delete_memory()` 的实际行为：

```python
self.vector_store.delete(vector_id=memory_id)          # 向量确实删了
self.db.add_history(memory_id, prev_value, None,        # ← prev_value = 被删记忆原文
                    "DELETE", ..., is_deleted=1)
```

而 `mem0/memory/storage.py:108` 的 history 表 schema：`old_memory TEXT` / `new_memory TEXT`，**普通 SQLite 文本列，无加密、无覆写**。

同时 `main.py:1082` 的 ADD 路径 `add_history(memory_id, None, new_memory, "ADD", ...)` 也写明文。

**因此一条记忆的明文在 history 表里至少留两份（ADD 的 `new_memory` + DELETE 的 `old_memory`），`is_deleted=1` 仅为标记位。**

实测（`_exp/mem0_delete_residue.py`，用 mem0 真实 `SQLiteManager`、按 `main.py` 实际调用序列）：删除后该 memory_id 有 2 条记录，2 份完整明文可恢复，全表 `LIKE` 直接命中。

**⚠️ 定性更正（2026-09-09）：这不是漏洞，是设计层面的合规缺口。**

`docs/api-reference/memory/history-memory.mdx` 明确记载 history 是公开特性——"Retrieve the full change history of a specific memory to track how it has evolved over time"，changelog 亦有 "Added timestamps for `DELETE` operations in history"。**保留变更历史（含 DELETE 事件）是文档化的设计意图。** 因此不得表述为"漏洞"，也不适用负责任披露流程。

真正站得住的表述是**删除语义与清除能力之间的缺口**：

`SQLiteManager` 的全部操作为 `add_history` / `batch_add_history` / `get_history` / `save_messages` / `get_last_messages` / `reset` / `close`；全代码库无 `delete_history` / `purge`。**唯一的清除路径是 `reset()`，它 drop 整张表、销毁所有用户的历史。**

> 因此：mem0 的 `delete(memory_id)` 删除向量并标记 `is_deleted=1`，但明文永久留存于 `history.old_memory` 与 ADD 事件的 `new_memory`；公开 API 不存在按主体清除 history 的手段。**单个用户的删除请求无法通过公开 API 被完整履行。**

这个表述的优点：不依赖厂商承认是缺陷、可从公开文档与源码直接复核、且直接推出创新点 2——密钥销毁使 history 中的密文同样不可解，无需额外的 purge 接口。

这正是加密删除赢的地方。

### (d) 部署变换恢复（量化 / benign relearning）—— ⚠️ 部分确认，结论比预想精确

SBU 的参数通路是 KL-to-random，把遗忘样本输出分布对齐到高熵先验，是**软抑制**而非抹除。`Catastrophic Failure of LLM Unlearning via Quantization`（ICLR 2025）已证明量化能恢复被遗忘知识。

**2026-09-09 实测**（Qwen2.5-0.5B-Instruct 全参微调植入 MU_B 的 40 forget + 80 retain canary，RTX 5070；量化为手写 RTN 对称 per-output-channel，不依赖 bitsandbytes——ICLR 2025 研究的就是 RTN）：

植入基线：base forget=0.000 → implanted **forget=0.925 / retain=1.000**（三句式均 0.93）

| 遗忘方法 | 遗忘后 | +8bit | +4bit | 结论 |
|---|---|---|---|---|
| **GA（顺序训练，部分遗忘）** | 0.308 / 1.000 | 0.317 / 1.000 | **0.950 / 0.975** | **恢复剧烈，超过植入水平** |
| GA（mixed-batch） | 0.000 / 0.588 | — | — | 过度遗忘，run 无效 |
| **NPO（含参考模型的正确实现）** | 0.000 / 0.988 | 0.000 / 0.988 | 0.000 / 0.929 | **无恢复（干净负结果）** |
| KL-to-random（SBU） | 见下 | — | — | 0.5B 上无有效操作点 |

**结论 1（可靠）：攻击 (d) 成立但依赖遗忘方法。** 它狠打"不完全遗忘"——GA 留下 0.308 的残余，4-bit 量化把它拉回 0.950（高于植入时的 0.925），retain 仍 0.975；但打不动调好的 NPO（8bit/4bit 均稳定为 0.000）。这比"量化普遍破坏遗忘"的粗糙叙事更精确，且 NPO 那条负结果本身有价值。

**结论 2（需限定范围）：KL-to-random 在 0.5B 上没有可用操作点。** 两轮预设判据扫描（`retain≥0.70 且 forget≤0.30`），共 10 个配置，全部失败：

| lr（α=1.5, T=2.0） | forget | retain |
|---|---|---|
| 1e-6 | 0.925 | 1.000（完全无效果） |
| 5e-6 | 0.358 | 0.779（最接近，仍越界） |
| 6e-6 | 0.133 | **0.342** |
| 7e-6 | 0.008 | **0.037** |
| ≥8e-6 | 0.000 | **0.000** |

**forget 与 retain 一起下降、不分离**——该目标函数在小模型上不存在遗忘/效用的可分离区间。

**最可能的原因是一个真实的可复现性缺口**：SBU 原文称 "entropy fallback is critical for preserving general capabilities, improving test accuracy from 78% to 90%"，但该机制**只在从未公开的 supplementary material 中**（见 §2.1）。本文实现的是公开材料里能读到的全部内容。

**⚠️ 范围限定**：以上为 0.5B 结果，SBU 用 8B（II-Medical-8B）。大模型容量更高，可能存在 0.5B 上不存在的可分离区间。**"量化能否让 SBU 的 KL-to-random 塌回"这一 SBU 专属命题尚未定论，需服务器 4090 上的 8B 复现（fp16 基座 + LoRA，不可用 4-bit QLoRA 装载，否则起点已量化、实验被污染）。**

复现产物：`_exp/quant_recovery2.py`（植入）、`quant_recovery3.py`（mixed-batch 三方法）、`klrand_sweep.py` + 细扫日志、`q6v2/`、`q6v3/`、`q6_sweep/`、`q6_fine/`。

### (e) 用 IAM 重测 SBU 的隐私声明

USENIX 2025 `Towards Lifecycle Unlearning Commitment Management` 论证 **"MIAs are ill-suited for unlearning inference"**：近似遗忘的 membership ground truth 不是二值而是连续谱，MIA 抓不住粒度，还会把高置信非成员误判成成员。提出 **IAM（Interpolated Approximate Measurement）**，样本级遗忘完整度，只需一个预训练 shadow model，作者明说 scales to LLMs，代码在 `github.com/Happy2Git/Unlearning_Inference_IAM`。

**SBU 的头条数字"MIA Score 0.895 vs 0.727，隐私提升 24.8%"正是用这个被指为不适用的工具测的。**

这条比 (a)–(d) 更狠：不是找实现漏洞，是质疑度量工具。

**指标调整**：L4/参数侧改用 IAM 作主指标，Min-K% 降为对照。

---

## 6. 创新点 2：Verified Forgetting 的密码学实例化

### 必须自己先划清的界

**加密删除本身不是创新点**（AWS KMS 那一套是工业标准）。创新点是：

1. provenance 驱动的**密钥作用域划分**（scope → 密钥树节点映射）
2. **穿刺原子失效向量索引**（把攻击 (b) 纳入删除语义，而非 τ 阈值批处理）
3. **用户持份**使删除权从"请求"变为"撤销"
4. **形式化删除定义**：从 Garg-Goldwasser-Vasudevan（Eurocrypt 2020）框架改写到 Agent 记忆场景

### 安全性论证

- 穿刺后不可区分性归约到 PRG + AEAD 安全性，写成 game-based 论证。
- 用户持份下平台单方不可解密，归约到秘密共享安全性。
- 明确列出不可覆盖的敌手（§3），不装作全覆盖。

### 性能实测（必做）

- **与扁平密钥表基线的三维对比**：存储 / 派生延迟 / 删除粒度。穿刺 k 次后密钥状态 O(k log n) 且随删除增长，扁平表 O(n) 但恒定——真实取舍。
- 用户离线导致 agent 失忆的可用性代价。
- 会话期明文缓存窗口大小。
- 级联删除端到端延迟。

---

## 7. 数据与基线

### 基线（均为已发表，非自建）

- **SBU**（记忆侧 + 参数侧双通路）
- **SBU 的三个记忆侧基线**：Naive Deletion / Re-indexing / Retraining Oracle
- **MemSecBench 的 4 种记忆后端**（24 配置矩阵）

### 数据

- **MemSecBench 现成资产可复用**：310 case / 48 场景 / Write-Execute-Forget 协议 / 7 个生命周期检查点。**省掉投毒轴的数据集构建。**
- 隐私删除轴：`LoCoMo` 或 `MSC` 为底 + 注入 canary PII + **让 mem0 真实跑一遍生成派生记忆**（而非手写），确保 (a) 测的是真实系统行为。
- SBU 用 II-Medical-8B（Qwen3-8B），显存 19–28GB、图注 "32GB Limit"。**本机 5070/12GB 与实验室 4090/24GB 都复现不了其参数通路，但不需要**：攻击 (a)(c) 打 memory pathway（纯 CPU），(b) 已在 5070 上跑通（28s/8 条），(d) 用 0.5B–1.5B 自建。

---

## 8. 范围切分

### 8.0 前置岔路：密码路线 vs 纯安全路线

**触发条件**：专业要求原话是"必须有**密码或安全理论**成分"。若"安全理论"能单独满足，路线 B 打开。网安学院通常认可纯 ML 安全类论文，但**必须由导师/学院确认，不能自己假设**。

| | 路线 A（主方案） | 路线 B（退路） |
|---|---|---|
| 题目 | 《大模型智能体记忆删除的密码学机制与残留评估研究》 | 《Agent 记忆遗忘在部署变换下的失效评估》 |
| 创新点 1 | 五个攻击（a–e） | 攻击 (a)(c)(d)(e) |
| 创新点 2 | 用户可撤销的密码学删除 | 无密码；靠威胁模型 + 攻击设计 |
| 净工期 | 约 15 个月（需按 §8.1 切） | 约 12 个月 |
| 主要风险 | 工期紧 | **全部压在实验结果上，无工程可控的保底章节** |
| 就业 | Agent 工程师 + 安全 + 治理（三线） | 安全 / 红队（一线） |

**倾向**：即使路线 B 可行，仍略偏 A——密码那块是**工程可控**的（几百行，不会失败），给论文一个保底章节。

**两条路线前期工作完全重合**，不必等答案开工：共享 mem0 改造、数据集、攻击 (a)(b)(c)(d)(e) 全部。分歧只在密码架构与形式化论证，排在 2026.10 之后。

### 8.1 路线 A 的切分

**核心（必须完成）**
- 加密删除 + 2-of-2 用户持份 + 用户侧可穿刺种子
- provenance 图 + 级联删除 + 索引原子失效
- 数据集（MemSecBench 复用 + LoCoMo 构建）
- 攻击 (a) 共享派生工件、(b) 索引反演、(d) 量化恢复
- 形式化定义 + 安全论证 + 与扁平基线开销对比

**压缩**
- 攻击 (c) 存储层残留：论证 + 小实验即可
- 攻击 (e) IAM 重测：用现成代码，不改进方法
- 问责日志：够用即止

**Stretch（掉了不影响毕业）**
- SHARE & PROPAGATE 阶段（多智能体）——**SBU 结论明确写了这是其 future work，不要抢**
- 中文 embedding inverter 自训
- 完整投毒清除对比

---

## 9. 尚未验证的假设

| # | 假设 | 状态 | 如何验 |
|---|---|---|---|
| 1 | SBU 附录是否对共享工件做内容级处理 | ✅ **已结清** | arXiv 无 ancillary files，附录从未公开；摘要 "logically invalidating" 即证据 |
| 2 | 五篇 2026 文献是否占据本方向 | ✅ **已结清** | 逐篇扫描，全部零密码；综述反把本方向点为公开缺口 |
| 3 | 七篇可验证遗忘是否占据创新点 2 | ✅ **已结清** | crypto-erase / key destruction / puncturable / secret sharing 全部零命中 |
| 4 | **vec2text 在 ada-002 上的反演质量** | ✅ **已确认（gtr-base 上）** | 2026-09-08 实测：token F1 0.983、PII 召回 0.950、7/8 逐字恢复。攻击 (b) 成立为主武器。ada-002 对齐待 OpenAI key |
| 5 | mem0 是否留了足够 hook 插入加密与索引失效 | ✅ **已确认，且转为发现** | 删除路径单点（`_delete_memory`）、向量层可插拔，hook 充足；**并发现 mem0 删除后明文留 2 份，见 §5(c)** |
| 6 | **量化能否让 KL-to-random 塌回** | ⚠️ **部分确认** | GA 部分遗忘 → 4bit 恢复 0.308→0.950（确认）；NPO 无恢复（负结果）；**KL-to-random 在 0.5B 上无有效操作点（10 配置全败），SBU 专属命题待 8B 复现** |
| 7 | **"安全理论"能否单独满足学位要求** | ❌ 未验 | 一封邮件，决定路线 A/B |
| 8 | **KL-to-random 在 8B 上是否存在可分离区间** | ❌ 未验（新增） | 服务器 4090：fp16 8B + LoRA，**禁用 4-bit QLoRA 装载**（会污染量化实验） |

---

## 9.1 实验环境（2026-09-08 实测）

| 项 | 实际值 | 影响 |
|---|---|---|
| GPU | **RTX 5070 / 12GB**（非 4090 / 24GB） | 0.5B–1.5B 可做；**1.5B 以上全参微调不行**，必须 LoRA。实验室 4090 另算 |
| 计算能力 | sm_120（Blackwell） | **必须 cu128 版 torch**，旧版直接跑不起来 |
| torch | 2.11.0+cu128，CUDA 可用 | ✅ |
| transformers | **必须钉 4.44.2** | transformers 5.x 禁止嵌套 `from_pretrained`，与 vec2text 0.0.13 不兼容（`check_and_set_device_map` 报 meta device 错） |
| vec2text | 0.0.13 | **Windows 不支持**，需 `resource` 模块 stub（见 `_exp/resource.py`，仅用到 `setrlimit(RLIMIT_CORE)`） |
| 副作用 | sentence-transformers 6.0.1 与 transformers 4.44.2 冲突 | 若需 sbert，降到 3.x |

复现产物均在 `_exp/`：`test_vec2text_inversion.py`、`mem0_delete_residue.py`、`resource.py`、`invert_*.json`、`vec2text_run.log`、`mem0_src/`（mem0 浅克隆）。

---

## 10. 答辩风险

### 措辞纪律

- 创新点用建设性表述，**不要**把"划密码学保证的边界"写成创新点（国内评审易判"缺方法创新"），该论点放结论。
- **不得**表述为"提出可验证记忆治理框架"（名被 2604.16548 占），须表述为"Verified Forgetting 原语的密码学实例化"。
- 学术叙事（遗忘 + 密码）与就业叙事（安全 + 合规）分开措辞。

### 预期质疑与答法

**Q1：为什么不直接一条记忆一个随机密钥，删除就删密钥行？**
平台侧确实可以，本文将扁平密钥表作为显式基线并实测对比。可穿刺树的必要性在**用户侧**——用户设备不可能持 n 份 per-scope 份额，需小种子支持 per-scope 撤销。

**Q2：加密删除不是工业界标准做法吗？**
是。创新不在加密删除本身，在 §6 的四点。

**Q3：能阻止恶意平台在删除前导出明文吗？**
不能，已在威胁模型显式声明出范围。无 ZKP/TEE 无法解决。

**Q4：和 SBU 什么关系？**
SBU 是本文的主基线。它把删除做成逻辑失效 + 平台自证，本文指出其三处残留并给出密码学补救。

**Q5：和综述的 VMG 什么关系？**
综述规定 Verified Forgetting 应满足什么并将 post-deletion verification 列为公开缺口，本文提供其机制实例化。

**Q6：中文场景怎么办？**
主实验英文（受已发布 inverter 限制），附中文小 case study 用弱攻击覆盖。

---

## 11. 阅读清单状态

### 已实读并完成差异化 ✅
SBU（2602.17692v2，全文）、综述（2604.16548v2，框架 + VMG 五原语）、MemSecBench（摘要 + 方法 + F1/F2 判定）、Selective Forgetting、AgentLeak、USENIX Lifecycle/IAM、TIFS Proof of Unlearning、SaTML Verifiable and Provably Secure MU、TIFS TruVRF、USENIX On the Necessity、TDSC When MU Meets RAG、NDSS A Duty to Forget、S&P Unlearning Inversion Attacks（关键词层）

### 待精读（按优先级）
1. **Garg, Goldwasser, Vasudevan, *Formalizing Data Deletion…*（Eurocrypt 2020）** — 创新点 2 理论骨架，最高优先
2. Morris et al., *vec2text*（EMNLP 2023）— 攻击 (b) 主武器
3. USENIX IAM 全文 + 代码 — 攻击 (e)
4. `Catastrophic Failure of LLM Unlearning via Quantization`（ICLR 2025）— 攻击 (d) 直接依据，**尚未下载**
5. Song & Raghunathan, *Information Leakage in Embedding Models*（CCS 2020）
6. S&P `Unlearning Inversion Attacks` 全文 — 相关工作区分
7. 密码侧：GGM（1986，只看构造）、Shamir（1979）、可穿刺加密（IACR 2020/882，Green-Miers 有 IEEE 付费墙）

---

## 12. 待办

- [x] ~~验证假设 4（vec2text 反演质量）~~ —— ✅ 2026-09-08，F1 0.983 / PII 0.950 / 7-8 逐字，攻击 (b) 成立
- [x] ~~验证假设 5（mem0 hook）~~ —— ✅ 2026-09-08，hook 充足，并发现删除后明文留 2 份
- [x] ~~验证假设 6（量化恢复）~~ —— ⚠️ 2026-09-09 部分确认：GA 部分遗忘 4bit 恢复 0.308→0.950；NPO 无恢复；KL-to-random 0.5B 上无操作点
- [ ] **向导师/学院确认："安全理论"能否单独满足学位论文要求** —— 决定路线 A/B，一封邮件，本周做
- [ ] **假设 8：服务器 4090 上的规模复现** —— 脚本 `_exp/quant_recovery_8b.py`（三 stage 已在 0.5B 上冒烟验证通过）

  ```bash
  # 环境（与 vec2text 共用，transformers 必须钉 4.44.2）
  pip install "transformers==4.44.2" peft accelerate torch
  # 拷贝：quant_recovery_8b.py + MU_B/data/synthetic_canary.jsonl

  # rung1（先跑这个）：1.5B 全参，与 0.5B 方法学一致，无 LoRA 混淆，约 15GB
  python quant_recovery_8b.py --model Qwen/Qwen2.5-1.5B-Instruct --mode full --stage implant
  python quant_recovery_8b.py --model Qwen/Qwen2.5-1.5B-Instruct --mode full --stage unlearn
  python quant_recovery_8b.py --model Qwen/Qwen2.5-1.5B-Instruct --mode full --stage sweep

  # rung2：8B LoRA，最接近 SBU 规模；⚠️ LoRA 低秩增量与 RTN 的交互是混淆项，须声明
  python quant_recovery_8b.py --model Qwen/Qwen3-8B --mode lora --stage implant
  ```

  **判读规则**：rung1 的 sweep 若出现满足 `retain≥0.70 且 forget≤0.30` 的配置 → 0.5B 的塌缩是规模问题，KL-to-random 可用，继续测其量化恢复；若 1.5B 上依然刀刃、无可分离区间 → 该目标函数在缺 entropy fallback 时本身不可用，这是对 SBU 可复现性的实质结论，rung2 可选做。
  内存技巧已内置：NPO 参考压成每序列一个标量、KL-random 参考预计算后 fp16 缓存到 CPU，避免常驻第二个 16GB 模型。
- [ ] 用 ada-002 重跑攻击 (b)，对齐 SBU 原始配置（需 OpenAI API key）
- [ ] 把删除语义缺口扩展为多后端对比实验（mem0 / Letta / MemSecBench 的 4 种后端）：每种后端在 delete() 后残留多少份明文、是否提供按主体清除的接口。**注意定性：这是设计缺口，不是漏洞（见 §5(c)）**
- [ ] 下载 `Catastrophic Failure of LLM Unlearning via Quantization`（ICLR 2025）—— 攻击 (d) 直接依据
- [ ] 精读 Garg-Goldwasser-Vasudevan，起草 Agent 记忆场景的删除定义
- [ ] 撰写开题报告（学术 / 就业双叙事分开措辞）
- [ ] 确认学制（若两年制：只保留攻击 (a)(c)(d) + 加密删除，砍全部 stretch 与形式化论证）

### 关于 mem0 的表述纪律

**不要**把 history 明文残留写成"漏洞"或走负责任披露流程——history 是 mem0 文档化的公开特性（见 §5(c) 定性更正）。正确表述是"删除语义与清除能力之间的设计缺口：无按主体清除接口，单用户删除请求无法完整履行"。这个表述不依赖厂商承认，且可从公开文档与源码直接复核。
