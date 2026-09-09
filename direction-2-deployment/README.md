# 方向二：LLM 遗忘在部署变换下的失效 —— 行级评估与部署绑定

- 状态：**进行中**（2026-09-09 确立，同日完成五轮文献验证与三组实验）
- 前一方向：`../direction-1-revocable-memory/`（已终止）

---

## 1. 方向是什么

**核心事实**：遗忘方法在"刚遗忘完的 checkpoint"上通过认证，但真实部署会再做量化、剪枝、蒸馏、模型合并、继续微调。这些变换不保证保持遗忘。

| 创新点 | 内容 | 角色 |
|---|---|---|
| **创新点 2** | 把遗忘的**评估/审计结论**密码学地绑定到实际部署的产物 T(θ) 与变换记录，使"为 θ 开的证书 + 服务 T(θ)"可检出对账 | **承重** |
| 创新点 1 | 行级多变换评估，提供必要性论证 | 支撑 |

**为什么承重放在创新点 2**：方向一死于把密码机制放在饱和区当承重，一篇论文就压塌。这次反过来——创新点 2 经六条独立路径验证无占据者，而创新点 1 的每一格都在被按月填。**结构上，创新点 1 少一格不影响论文成立；创新点 2 被占才会。**

---

## 2. 创新点 2：已验证的差异化（可从占据者原文引出）

六条验证路径：arXiv 两轮、40 篇 certified unlearning、40 篇 attestation/supply-chain、IETF/OpenSSF/专利、Semantic Scholar 引文图、Google Scholar。**均无占据者。**

| 最近邻 | 它做什么 | 界（引自对方原文） |
|---|---|---|
| IETF draft-sharif-ai-model-lifecycle-attestation（个人草案，非 WG 采纳） | 训练数据 Merkle → 权重签名 → **量化认证（逐层误差界）** → 部署认证 → 逐推理签名 | 只认证**数值邻近性**，不验证行为/能力/安全保持。**自认**："per-layer error bounds alone **would not reliably catch**… a poisoned quantization may sit inside normal tolerance"。**遗忘/删除/被遗忘权全文未提** |
| OpenSSF Model Signing v1.0 / Sigstore model-transparency | 对模型文件整体签名 | 只证"这是原厂模型"，不证"属性仍成立" |
| IBM US12141704B2 等专利族 | 运行时神经流证明、blob 签名 | 完整性/确权，不涉评估结论 |
| Zenodo `unlearning certificates do not survive when models merge`（自存档预印本，0 引用 0 参考文献） | 证明证书不可合成；合并安全当且仅当 partner 与遗忘方向正交 | 补救是**算法的**（改在共享 base 上遗忘），不是**认证的** |
| `Telemetry and Concealment`（arXiv 2608.09069） | 推理输出用 enclave 证明绑到模型哈希 | 绑的是**行为记录**，不是审计结论。**机制侧最近邻，必读** |
| `What a Deletion Certificate Covers, and Where It Expires`（2026-07） | 立下原则："A deletion certificate should name its **reference state and validity horizon**" | 对象是支持向量记忆库、非密码、不涉部署变换。**它立原则，本文给机制** |

**术语禁区**：不得使用 "certified unlearning" —— 该词已被约 33 篇 DP 式理论界文献占死，会被读成"你声称给了一个 (ε,δ) 界"。

---

## 3. 创新点 1：格位地图（每格都有占据者，占据者=基线）

| 变换 | 占据者 | 状态 |
|---|---|---|
| 量化 | `Catastrophic Failure of LLM Unlearning via Quantization`（ICLR 2025，现象）；`Forgetting That Sticks`（arXiv 2605.15138，机制+MANSU）；**7 个抗量化遗忘方法**（GROM/DurableUn/QUAIL/QR-LoRA/OEU/Q-MUL/FIT） | 重度占据 → 基线 |
| 剪枝 | **`Composable Interventions for Language Models`（ICLR 2025）**：SparseGPT/Wanda 0–75% × GPTQ/AWQ 2–16bit × GA/GD/RMU，417 组合，Llama-3-8B/Mistral-7B/Yi-1.5-9B，WMDP，**有开源代码** | 占据（规模与方法均优于本项目）→ 基线 |
| 蒸馏 | `Distillation Robustifies Unlearning / UNDO`（NeurIPS 2025 Spotlight）：结论方向**相反**——"distillation robustifies unlearning"，"transfers behaviors while leaving latent capabilities behind" | 占据，且答案是"蒸馏修复而非破坏" |
| 继续微调 / relearning | `Distance Is Not Enough`、`Crossing the Margin Cliff`、`Invariance Makes LLM Unlearning Resilient`、`Unlearning's Blind Spots` | 占据 → 基线 |
| **模型合并** | 仅 Zenodo 预印本（理论 + planted-fact 5 seeds，**无 LLM 实证**）。25 篇"合并 × 遗忘"论文中**零命中**——全部用合并**做**遗忘 | **本项目最后一个开放格** |
| 行级系统评估（≥3 变换 × 多方法） | 无。arXiv 176 全量 + IEEE/ACM/USENIX/OpenReview + Scholar 均零命中 | 开放，但 Composable 已做两格 |

**缺口有权威出处**：Casper 等 `Open Technical Problems in Open-Weight AI Model Risk Management`（arXiv 2608.07514，**被引 25**）原文："**Benchmarking work has yet to thoroughly compare all of these types of methods**… for **fine-tuning, distillation, model merging, and quantization in sequence**"。

**表述纪律**：
1. **不得写"首次系统评估部署变换下的遗忘"** —— Composable 已做量化 × 剪枝。改写为"在已有配对评估之上补齐合并轴与变换链，并把度量对象从 WMDP 能力分换为遗忘集召回/canary/MIA"。
2. **必须写"部署期合并施加于已遗忘模型之后"**，不可简写为"模型合并与遗忘" —— 大量论文用合并**做**遗忘（含自称 "the first exploration of model merging for unlearning" 的 ICLR 2026 扩散论文），简写会被误读成在做他们做过的事。
3. 蒸馏那格若要做，须重度引用 UNDO 并限定为"UNDO 的结论对随机/加噪学生成立；部署实际使用的**预训练学生**情形未被测试"。

---

## 4. 已完成实验（0.5B / 1.5B，Qwen2.5）

植入基线：base forget=0.000 → implanted **forget=0.925 / retain=1.000**（三句式 canary 精确匹配）

| 变换 | GA（部分遗忘 0.317） | NPO（完全遗忘 0.000） |
|---|---|---|
| 4-bit RTN 量化 | **0.950**（+0.633），retain 0.975 | 0.000，retain 0.929 |
| 8-bit RTN 量化 | 0.317（+0.000） | 0.000 |
| 幅值剪枝 20% | **0.975**（+0.658），retain 0.975 | 0.000，retain 0.929 |
| 幅值剪枝 30% | **1.000**（+0.683），retain 0.950 | 0.000，retain 0.921 |
| 剪枝 50% | 塌缩（retain 0.367），不计 | 塌缩，不计 |

1.5B 复现：GA lr=8e-6 遗忘至 0.092 → 4-bit **0.292**（+0.200，24/120 次探测），retain 反升至 0.929；NPO 遗忘至 0.000 / retain **1.000**，8bit 与 4bit 均保持 0.000。

**必须同时报告的对照与限制**：
- **implanted 对照组**在剪枝下召回从 0.925 升到 1.000（+0.075）。剪枝对未遗忘模型本身就提升 canary 召回，**GA 的 +0.658 里约 +0.07 属于这个普适效应**。不报此对照，结果可被一句"剪枝本来就提升召回"打掉。
- **尚缺同稀疏度的随机掩码对照**，用于把"幅值剪枝"与"任意权重扰动"分开。
- KL-to-random（SBU 参数通路）在 ≤1.5B **36 配置全败**，无遗忘/效用可分离区间，且"效用先坏于遗忘"（1.5B lr=4e-6 时 retain 0.850→0.804 而 forget 一点没动）。SBU 自称关键的 entropy fallback 只在从未公开的 supplementary 中。
- **"GA 留下 0.317"是 bf16 训练特有的**：同配方在 fp32 下 forget=0.000/retain=0.575（过度遗忘）。差别纯来自权重更新的数值精度。

---

## 5. ⚠️ 一个被提出但**未被证实**的解释性主张

曾设想把创新点 1 从"填格子"升级为"可预测的解释"：**扰动权重 delta 的变换（量化/剪枝/合并）破坏遗忘；从行为重建的变换（蒸馏）不破坏；决定破坏与否的是 δ 幅值相对于该变换的扰动尺度。**

实测（`experiments/delta_scale_analysis_v3.py`，168 个线性层逐层中位数）：

| 量 | GA | NPO | NPO/GA |
|---|---|---|---|
| δ 非零项占比 | 0.1647 | 0.3366 | 2.04 |
| mean\|δ\| | 2.757e-05 | 1.208e-04 | 4.38 |
| **P1** mean(\|δ\|/bin) 4bit | 0.0026 | 0.0117 | **4.48** ✅ 方向一致 |
| **P1b** \|δ\|<半个 bin 的占比 | 1.0000 | 1.0000 | **1.00** ❌ 不discriminate |
| **P2** δ 质量落在被剪权重上 @0.2 | 1.0000 | 0.6706 | 0.67 ✅ 方向一致 |

**结论：该主张未被证实，不得当作已证引用。** 三条理由：

1. **P1b 不成立,而它拆掉了机制。** GA 与 NPO 的 δ **都是 100% 落在半个 bin 以下**，可 NPO 没被恢复。顺此推下去发现"舍入抹掉 δ"本身站不住：**RTN 舍入近似无偏**，它不把权重推回遗忘前的值，只加尺度约 bin/2 的近零均值噪声。正确表述是信噪比 |δ|/(bin/2)——GA 0.0052、NPO 0.0234，**两个都极低而 NPO 存活**，信噪比解释不了差异。
2. **n = 2。** 只有两个遗忘方法 × 两种变换。在 n=2 上谈相关性几乎没有统计意义。要立这条需要多方法 × 多变换的配对数据（GA/NPO/RMU/task-vector negation × 量化各位宽/剪枝各稀疏/合并各系数），是月级工作量。
3. **机制的量化部分已被 Forgetting That Sticks 占**（δ vs bin 宽度）。本项目的可能贡献是推广成跨变换的分类与预测，**不是发明这个机制**。

**唯一算得上正面的副产品**：GA 的 δ 是 4-bit bin 的 1/385、NPO 是 1/85，**两者都落在 Forgetting That Sticks 报告的 47–828 倍区间内** —— 在不同模型与方法上独立复现了它的测量。

---

## 6. 本轮我的错误（保留以免重犯）

1. **断言 Google Scholar 被自动化拦截，没试就说。** 实际可用，且它查出了 Composable（arXiv 检索漏掉的关键竞品）。任何"某渠道不可用"的判断必须先实测。
2. **把 bf16 的 δ=0 误诊为"存储污染"。** 部署产物本身就是 bf16，量化与剪枝施加在 bf16 模型上，所以"bf16 中可表示的 δ"正是被变换的真实状态。v1 测的是对的量，只是中位数这个统计量退化。为此白写了一版 fp32 重跑脚本（`delta_scale_analysis_v2` 未收录，其失败日志在 `results/logs/delta_v2_run.log`）。
3. **把 delta 测试说成"决定解释成不成立的半小时"。** n=2 从来不可能定这件事，这在跑之前就该看出来。
4. **两条消息前声称"行级评估无人做过、门槛是工作量"。** Composable 已做两格，该说法已撤回。

---

## 7. 下一步

1. **跑合并那格** —— 最后一个开放格，纯权重运算零训练成本，且可检验 Zenodo 的理论预测（恢复量 = 合并系数 × partner 在遗忘方向的分量，与遗忘彻底程度无关）
2. **补剪枝的随机掩码对照** —— 半小时，补掉最易被打的软肋
3. **读三篇必读**：Composable 全文（当基线跑，有代码）、Casper 等（立缺口）、`Telemetry and Concealment` 2608.09069（创新点 2 机制侧最近邻）
4. **未解决的致命项（需 CNKI 凭据，Scholar 零索引已实测两次）**：李朝恒《人工智能模型隐私遗忘方法研究》（CNKI CMFD2026/1025075616）、李云灏《面向大语言模型的遗忘学习方法研究》（万方 D04147018）、《基于预测交叉熵的模型遗忘研究》（万方 D03718948）——是否已做"遗忘后施加变换并评估失效"。**同方向学位论文撞题会使开题直接被否。**

环境三个坑见 `../direction-1-revocable-memory/README.md`（transformers 必须钉 4.44.2；vec2text 需 Windows stub；RTX 5070 是 sm_120 需 cu128 torch；1.5B 全参需 `--optim adafactor` 才能进 12GB）。
