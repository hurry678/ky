# Agent 记忆删除：密码学机制与残留评估 —— 交接包

## 🛑 方向已于 2026-09-09 终止

**结论：不做。** 原因是创新点核心被多篇论文分别占据，四轮交叉带检索每一轮都找到新的占据者。

| 组成 | 占据者 |
|---|---|
| 初稿的分层记忆 / provenance 图 / 级联删除 / 哈希链审计 / 参数遗忘 / MIA 度量 | `Agentic Unlearning`（SBU，arXiv 2602.17692v2，2026-02） |
| 软删除后 embedding 反演；向量索引加密删除；ECDSA 签名删除证明 | `Ghost Vectors`（arXiv 2606.18497v1，2026-06） |
| 检索拓扑漂移残留（本方向未枚举到的第五个残留位置） | `Ghost Echoes`（arXiv 2608.20352v1，同组） |
| **形式化删除定义 + 依赖/派生数据级联删除** | `Meaningful Data Erasure in the Presence of Dependencies`（**VLDB 2025**，arXiv 2507.00343v2）及其 SIGMOD 2026 后续 |

终止时仍空着的只有**用户持份密钥**（2-of-2，用户可单方面撤销未来访问）一点。以一个 novel 点、在多个成熟研究组密集圈地的空间里、21 个月、无导师指导——判断为不值得投入。

**终止时机是好的**：开题前、系统未搭建。真正糟糕的版本是 2027 年系统建成、实验做半才发现。

---

## ✅ 未随方向一起作废的部分

以下与"密码删除"这个方向无关，换任何 LLM 遗忘方向都可直接复用：

**三个已验证结论**（无撞车论文触碰，属 MU_B 最初的"部署变换下遗忘是否失效"这条线）：

- **量化恢复不完全遗忘的知识，两个规模复现**：0.5B 遗忘至 0.308 → 4-bit **0.950**（高于植入的 0.925）；1.5B 遗忘至 0.092 → 4-bit 0.292（+0.200，24/120 次探测）。**两个规模下 8-bit 均无恢复** —— 4bit/8bit 不对称是最稳的特征。附带规律：遗忘越彻底可恢复越多，即 forget-recall 上最漂亮的配置最脆。
- **调好的 NPO 不被量化恢复，两个规模**：0.5B retain 0.988、1.5B retain 1.000，8/4-bit 均保持 0.000。使"量化普遍破坏遗忘"这一说法变精确。
- **MIA Score 在高分离区间完全饱和**：implanted（canary 召回 0.925）与 GA（0.308）的 MIA Score **都是 0.0000** —— 忘掉六成知识，MIA 无任何反映。IAM 有反映但压缩严重（召回降 67%，IAM 仅降 13%）。
- 附：**KL-to-random（SBU 参数通路）在 ≤1.5B 不存在遗忘/效用可分离区间**，36 配置全败，且"效用先坏于遗忘"。SBU 自称关键的 entropy fallback 只在从未公开的 supplementary 中。

**一套可用的实验设施**（`experiments/`）：canary 植入流水线（三句式 prompt→answer，loss 只算 answer）、手写 RTN 对称量化（不依赖 bitsandbytes）、mixed-batch 的正确 GA / NPO / KL-to-random 实现、IAM 官方 `ip_ppl` 逐字接入、超参扫描框架与预设判据护栏。

**环境三个坑的解法**：见下方"环境"一节。

---

## ⚠️ 唯一的方法论教训

**四轮检索、四轮都找到新占据者，原因不是运气：novelty 的验证只沿单轴进行。**

- 最初的"未被占据"沿「遗忘验证」一条轴验（7 篇 TIFS/TDSC/SaTML/USENIX）
- secure deletion 那条线只查 1996–2013 经典篇目
- 窗口监控关键词钉死在 `"agent memory"` —— Ghost Vectors 是向量数据库论文，框不进去；VLDB 那篇是数据库论文，更框不进去

**下一个方向定下来之前，必须先做交叉带矩阵检索：枚举「删除/遗忘对象 × 密钥或控制权归属 × 数据类型 × 应用场景」，逐格查，再决定投入。** 不要沿单轴列关键词，也不要采信任何二手转述（本项目两次误判都源于此：一次因采信"场景不同"而没读 MUTE，一次因误读一行列表摘要而虚报撞车）。

有效通道（已验证）：arXiv API，例如
```
http://export.arxiv.org/api/query?search_query=(abs:encryption)+AND+(abs:%22machine+unlearning%22)&sortBy=submittedDate&sortOrder=descending
```
Ghost Vectors 就是这么找到的，而按「agent memory」检索永远找不到它。

---

## 以下为终止前的完整记录（存档）

## 现在站得住的结论

完整台账见 `docs/roadmap-2026-09-09.md`（每条附「会被什么推翻」）。摘要：

| 编号 | 结论 | 强度 |
|---|---|---|
| E1 | 7 篇可验证遗忘论文中 crypto-erase / key destruction / puncturable / secret sharing **零命中** | ✅ 但**验证范围过窄**，见上文第 2 点 |
| E2 | 2026-04 综述（arXiv 2604.16548v2）把 post-deletion verification 列为公开缺口 | ✅ |
| E3 | SBU 正文五次引用 supplementary，**arXiv 无 ancillary files，附录从未公开** | ✅ |
| E4 | vec2text 反演：token F1 0.983 / PII 召回 0.950 / 7-8 逐字 | ✅ **但见下方"诚实校正"** |
| E5 | 量化恢复不完全遗忘：0.5B 0.308→**0.950**、1.5B 0.092→0.292（+0.200）；**8-bit 两规模均无恢复** | ✅ 两规模 |
| E6 | 调好的 NPO 不被量化恢复：0.5B retain 0.988、1.5B retain 1.000，8/4-bit 均保持 0.000 | ✅ 两规模 |
| E7 | mem0 `delete()` 后明文留存 `history.old_memory`，且**无按主体清除接口**（仅 `reset()` 全表销毁） | ⚠️ 降级：history 是**文档化特性**，**不得称"漏洞"**、不适用负责任披露 |
| E8 | 按 SBU 公开文本复现的依赖闭包删除：形式化（删全部闭包，泄露 0%）与实现（refcount 保留共享，**57.5% 存活**）不等价 | ✅ 但**限结构级**，非真实 LLM 摘要 |
| E10 | KL-to-random 在 ≤1.5B **不存在**遗忘/效用可分离区间：**36 配置全败**，且"效用先坏于遗忘" | ✅ |
| E13 | MIA Score 在高分离区间完全饱和：implanted(召回 0.925) 与 GA(0.308) 的 MIA Score **都是 0.0000** | ✅ 事后观察，非预设判据 |
| E12 | 8B 上是否存在可分离区间 | ○ 待验，需 24GB 卡 |

### 诚实校正（务必保留）

- **E4 的数字不比 Ghost Vectors 好，是题目更简单。** 本方 F1 0.983 用的是短、格式化、正好落在 `gtr-nq-32`（训练长度 32 token）分布内的合成 canary；Ghost Vectors 的 ROUGE-L 0.185–0.290 用真实 Wikipedia / 健康记录且不做微调。**不得拿 0.983 去比 0.185。**
- **攻击 b 只对 ≤32 token 短条目验证过。** 摘要/反思等派生工件远超 32 token，反演会退化（依据：arXiv 2507.07700 复现研究）。
- **ada-002 对齐已放弃**：适配 32 token 的 `ada-ms-32` 未公开，`ada-ms-128` 在 32 token 上表现差。硬跑会得到偏低结果而误判 ada-002 更安全。
- **加高斯噪声（λ=0.01）与 embedding 量化两种防御已被复现为有效且不损检索。** 故攻击 b **不得单独陈述**，必须挂在 GGV 以内存状态为准这一点上（"让攻击变难" vs "让数据不在"）。
- **不得混淆两种量化**：embedding 量化是防御（挡反演）；权重量化是攻击（恢复被遗忘知识）。

---

## 目录结构

```
docs/        方向定稿、roadmap（含证据台账与表述纪律）、形式化工作稿、
             文献检索清单、两份文献下载/检索记录、Kimi 版初稿（存档对照）
experiments/ 全部脚本，见下表
results/     所有结果 JSON、e8 输出、以及清洗过的运行日志（logs/）
data/        synthetic_canary.jsonl（40 forget + 80 retain）、benign_relearning.jsonl
```

| 脚本 | 对应结论 | 备注 |
|---|---|---|
| `test_vec2text_inversion.py` | E4 embedding 反演 | 需 `resource.py` stub（Windows） |
| `mem0_delete_residue.py` | E7 存储层明文残留 | 需先 `git clone mem0` 到 `mem0_src/` |
| `quant_recovery2.py` | canary 植入（三句式 prompt→answer，loss 只算 answer） | v1 因训练/评测格式不一致失败，已弃 |
| `quant_recovery3.py` | E5 / E6 mixed-batch 三方法遗忘 + RTN 量化 | |
| `klrand_sweep.py` | E10 的 0.5B+AdamW 扫描 | |
| `quant_recovery_8b.py` | rung0/1/2 统一入口，三 stage 已冒烟验证 | 含 `--optim adafactor`（12GB 卡跑 1.5B 全参的关键） |
| `e8_shared_artifact_survival.py` | E8 共享派生工件存活 | 纯 CPU |
| `e9_iam_vs_mia.py` | E13；官方 `ip_ppl` 逐字调用 | 需 `git clone Unlearning_Inference_IAM` 到 `iam_src/` |
| `resource.py` | Windows 下 vec2text 的 `resource` 模块 stub | 仅本目录生效 |

**未包含**：模型 checkpoint 与 HF 缓存（约 14GB，脚本可重跑生成）、文献 PDF（版权）。

---

## 环境三个坑（踩过，务必照做）

1. **`transformers` 必须钉 `4.44.2`。** 5.x 禁止嵌套 `from_pretrained`，与 vec2text 0.0.13 冲突（报 meta-device 错）。
2. **vec2text 不支持 Windows。** 它只用到 `resource.setrlimit(RLIMIT_CORE)`，`experiments/resource.py` 是 no-op stub，放在脚本同目录即可。
3. **本机 GPU 是 RTX 5070 / 12GB（sm_120 Blackwell），必须 cu128 版 torch。** 1.5B 全参 + AdamW 约 13GB 装不下，改 `--optim adafactor` 后峰值 10.4GB 可跑；8B 只能 LoRA，需 24GB。

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install "transformers==4.44.2" sentence-transformers datasets accelerate vec2text scipy peft
```

---

## 接手后的建议顺序

1. **读 Ghost Vectors（arXiv 2606.18497v1）全文**，确认四个可能剩余点（派生工件级联 / 用户持份 / 参数层 / 形式化定义）是否真空着。这一步决定方向是否还成立。
2. **做交叉带矩阵检索**（见上文第 2 点）。不做这一步就开工，等于等第三次撞车。
3. 读已下载但未读的 secure deletion 五篇（Boneh-Lipton 1996、Perlman 2005、Vanish 2009、FADE 2010、Cachin 2013），填「删除对象粒度 / 密钥持有方 / 是否处理派生数据」三列对比表。
4. 补下三篇缺失文献：`SoK: Secure Data Deletion`（S&P 2013，试 ETH Research Collection）、Micciancio 1997（UCSD 作者页）、Naor-Teague 2001（IACR 2001/036）。
5. 读完 GGV（`docs/formalization-draft-2026-09-09.md` 已含 §1–2.1 提炼，剩 §2.2–2.4 与 §3）。
6. 以上都清楚后，再决定是否开题、是否搭系统。

**不建议**在第 1、2 步完成前搭系统或写开题报告。

---

## 一句话总结

九条主张有实测支撑、每条都写了会被什么推翻；但**创新点的核心已被两篇 2026 年论文部分占据，且发现它们的检索方法尚未系统化**。方向可能仍成立，可能需要重新收窄——**这个判断需要先完成上面第 1、2 步，不能凭本包现有材料下结论。**
