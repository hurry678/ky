# Agent 记忆删除：密码学机制与残留评估 —— 交接包

- 交接日期：2026-09-09
- 状态：**开题前的假设验证阶段。论文实验尚未开始。**
- 上一手：与 Claude 对话两天产出，全部数字可用本包脚本复现

---

## ⚠️ 先读这一节：接手前必须知道的三件事

### 1. 方向已被两次撞车实质削弱，**当前不建议直接开工**

| 时间 | 撞车论文 | 被占掉什么 |
|---|---|---|
| 2026-02 | `Agentic Unlearning: When LLM Agent Meets Machine Unlearning`（arXiv 2602.17692v2，简称 SBU） | 初稿的两个创新点几乎全部：分层记忆、provenance 依赖图、级联删除、索引重建、**哈希链审计日志**、参数遗忘、MIA 度量、canary+探测协议 |
| 2026-06 | `Ghost Vectors: Soft-Deleted Embeddings Remain Reconstructible in HNSW Vector Databases`（arXiv **2606.18497v1**） | 攻击 b 的核心发现与方法、攻击 c 的存储层框架、创新点 2 的**索引加密删除**（Epoch Key Rotation：加密向量、删除时丢弃密钥）、问责层（ECDSA 签名删除证明） |

**Ghost Vectors 尚未读全文。** 从摘要看可能仍留给本方向的：LLM 派生工件（摘要/反思/画像）的 provenance 级联、**用户持份密钥**、参数层、GGV 式形式化删除定义。**这四点是否真的空着，必须读全文确认，不得凭摘要判断。**

### 2. 上一手的方法论失误——**接手时最该避免重犯的**

两次撞车都发生在已收集语料之外，原因不是运气：**验证只沿单轴进行**。

- E1 的"未被占据"是沿「遗忘验证」一条轴验的（7 篇 TIFS/TDSC/SaTML/USENIX 期刊）
- secure deletion 那条线只查了 1996–2013 的经典篇目
- 窗口监控关键词钉死在 `"agent memory"` 上 —— Ghost Vectors 是向量数据库论文，框不进去

**竞品坐在交叉带上。** 正确做法是先枚举交叉格（删除对象 × 密钥持有方 × 数据类型 × 场景），再逐格检索，而不是沿单轴列关键词。**这件事尚未做，是接手后的第一优先。**

有效的检索通道（已验证可用）：arXiv API，例如
```
http://export.arxiv.org/api/query?search_query=(abs:encryption)+AND+(abs:%22machine+unlearning%22)&sortBy=submittedDate&sortOrder=descending
```
Ghost Vectors 就是用 `abs:encryption AND abs:"machine unlearning"` 找到的 —— 而按「agent memory」检索永远找不到它。

### 3. 关于是否公开本仓库

**建议设为 private。** 本方向剩余的novelty（用户持份 + 派生工件级联）尚未发表；`docs/roadmap-2026-09-09.md` 把它连同差异化论证一并写清了。公开等于交给任何检索者，而窗口本已只剩数月。

**另：本包刻意不含任何 PDF。** 文献多为付费墙期刊论文（TIFS / TDSC / S&P / NDSS），上传构成侵权。请用 `docs/下载清单_2026-09-08.md` 与 `docs/检索与下载记录_2026-09-09.md` 里的来源 URL 自行合法下载（两份记录含全部检索式与来源）。

---

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
