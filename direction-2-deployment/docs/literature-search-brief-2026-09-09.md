# 检索任务书：遗忘鲁棒性方向的验证缺口

- 生成：2026-09-09
- 用途：交给内网大模型 / 学校数据库检索。**我(Claude)只查了 arXiv,缺口都在 arXiv 之外**
- 关联：`handoff/` 仓库(上一个方向,已终止)、`_exp/prune_recovery.py`(本方向已有的第一个数据点)

---

## 0. 现在的方向是什么(判断相关性用)

**题目方向**:LLM 机器遗忘在部署变换下的失效——系统评估与部署绑定

**核心事实**:遗忘方法在"刚遗忘完的 checkpoint"上通过认证,但真实部署会对模型再做量化、剪枝、蒸馏、模型合并、继续微调。**这些变换不保证保持遗忘。** 已实测:GA 遗忘把 canary 召回压到 0.317,4-bit 量化拉回 0.950,20–30% 幅值剪枝拉回 0.975–1.000,而 8-bit 量化和调好的 NPO 都不受影响。

**创新点 1(承重)**:遗忘鲁棒性在多种部署变换下的系统评估
**创新点 2(支撑,密码在此)**:把遗忘声明密码学地绑定到实际部署的权重上——认证为 θ 开出,服务的是 T(θ),二者必须可对账

---

## 1. 已经验证过的,不要重复查

| 结论 | 依据 | 状态 |
|---|---|---|
| 量化 × 遗忘 已被占 | `Catastrophic Failure of LLM Unlearning via Quantization`(ICLR 2025,现象)、`Forgetting That Sticks`(arXiv 2605.15138,批评框架 + MANSU 缓解)、`GROM`(2026-08,缓解) | **当基线,不是障碍** |
| 微调 / relearning × 遗忘 已被占 | `Distance Is Not Enough`(2026-08-26)、`Crossing the Margin Cliff`(2026-08-22)、`Invariance Makes LLM Unlearning Resilient`(2025-10)、`Unlearning's Blind Spots` | **当基线** |
| 剪枝 × 遗忘 | arXiv 未见占据;`Forgetting That Sticks` 的 "sparsity" 指更新集中度、不是权重剪枝 | 空,已有数据 |
| 模型合并 × 遗忘 | 25 篇任务向量/合并 × 遗忘论文中**零命中**——全部用合并**做**遗忘,无人测合并**之后**知识是否回来 | 空 |
| 蒸馏 × 遗忘 | 部分占:`Recalling The Forgotten Class Memberships`(2025-06)做了分类设定的成员泄露;LLM 生成层面未见 | 窄缺口 |
| 行级多变换系统评估 | arXiv 176 条中最近 80 条零命中 | 空(仅 arXiv) |
| 密码绑定到部署产物 | 40 篇 certified unlearning / deletion certificate 中零命中;40 篇 attestation / supply chain 中零命中 | 空(仅 arXiv) |
| "certified unlearning" 术语 | 已被 DP 式理论界那一大批占死(约 33 篇) | **不可用此名** |

---

## 2. 检索任务(按优先级)

### 🔴 任务 A:非 arXiv 场馆 —— 行级系统评估是否已被占

**为什么最重要**:承重的那一半就是这个。我只查了 arXiv,而评估/基准类工作大量发在会议和期刊上。

**平台**:IEEE Xplore、ACM Digital Library、USENIX、**OpenReview(ICLR/NeurIPS/ICML,含在审稿件)**、Springer、ScienceDirect

**关键词组**(各平台语法自行调整):
```
"machine unlearning" AND (benchmark OR "systematic study" OR "empirical study" OR evaluation)
    AND (quantization OR pruning OR compression OR distillation OR "model merging" OR "post-training")

"unlearning robustness" / "robustness of unlearning" / "unlearning under compression"
"deployment" AND "unlearning" AND (fragile OR reverse OR recover OR undo)
```

**红旗**(命中即需重估方向):一篇同时评估 ≥3 种部署变换 × 多种遗忘方法的基准或综述。

**OpenReview 特别重要**:它能看到**在审但未公开发表**的稿子。这是唯一能提前几个月看到竞品的地方,arXiv 看不到。

---

### 🔴 任务 B:中文文献 —— 我完全没查过

**为什么重要**:你的论文是中文的,查重库和相关工作都涉及中文文献。而且国内有若干组做机器遗忘。

**平台**:CNKI(知网)、万方、维普、CNKI 学位论文库

**检索词**:
```
机器遗忘 / 机器去学习 / 遗忘学习 / 数据遗忘 / 被遗忘权
  × 大模型 / 大语言模型 / 预训练模型

模型量化 + 遗忘 / 残留
模型剪枝 + 遗忘 / 隐私
模型合并 / 任务向量 + 遗忘
知识蒸馏 + 遗忘 + 泄露
可验证删除 / 删除证明 / 遗忘验证 + 大模型
部署 + 安全属性 + 失效
```

**特别查学位论文库**:有没有硕博论文已经做了这个题。**这比期刊论文更致命**——同校或同方向的学位论文撞题,开题会直接被否。

---

### 🟡 任务 C:缓解方法的完整基线清单

**为什么**:缓解那一侧正在变拥挤(已知 MANSU、GROM、FIT to Forget、Invariance)。我需要完整清单才能写相关工作、才能确定创新点 2 不该做缓解。

```
"quantization-robust unlearning" / "compression-robust unlearning"
"relearn-robust" / "permanent unlearning" / "irreversible unlearning"
"durable unlearning" / "persistent forgetting"
unlearning AND (robust OR permanent) AND (quantization OR compression OR pruning)
```

**记录**:每篇覆盖哪几种变换、是方法还是评估、有无开源代码(要当基线跑)。

---

### 🟡 任务 D:创新点 2 —— 模型认证绑定(含工业界与专利)

**为什么**:这一格 arXiv 上空,但**它可能是工业实践而非论文**。Google 的 model signing、OpenSSF、Sigstore 这类工作不发 arXiv。

**平台**:Google Patents、国家知识产权局、GitHub、公司技术博客、NIST/ISO 标准文档、OpenSSF

**检索词**:
```
"model signing" / "model attestation" / "sigstore" AND model
"AI bill of materials" / AIBOM / "model card" AND (signed OR verifiable OR attested)
"deployment integrity" AND (model OR LLM)
"compliance certificate" AND (model OR weights OR checkpoint)
model provenance AND (quantized OR compressed OR derived)
```

**专利检索**(重要):
```
模型 + 完整性验证 + 部署
机器学习模型 + 签名 / 哈希 / 认证
model integrity attestation machine learning deployment
```

**红旗**:已有标准或专利覆盖"把评测结论绑定到具体权重哈希并检测变换后替换"。论文本身不涉侵权,但相关工作必须提,否则答辩被问"工业界不是有 Sigstore 吗"会答不上。

---

### 🟢 任务 E:引文链(最灵敏的探测器)

**为什么**:新竞品一定会引这几篇。引文链比关键词早几个月发现问题。

追这四篇的**引用者**(Google Scholar / Semantic Scholar 的 "Cited by"):

1. `Catastrophic Failure of LLM Unlearning via Quantization`(ICLR 2025)
2. `Forgetting That Sticks: Quantization-Permanent Unlearning via Circuit Attribution`(arXiv 2605.15138)
3. `GROM: Gradient-Free Rapid One-Shot Machine Unlearning`(2026-08-06)
4. `Meaningful Data Erasure in the Presence of Dependencies`(VLDB 2025,arXiv 2507.00343)

**建议每两周复跑一次**,直到开题。

---

### 🟢 任务 F:arXiv 剩余 96 条

我只查了 176 条中最近的 80 条(按日期降序),剩下 96 条更旧。可用同一检索式翻 `start=80` 与 `start=120`:
```
abs:unlearning AND (abs:benchmark OR abs:"systematic evaluation" OR abs:survey OR abs:"empirical study")
  AND (abs:robust OR abs:"post-training" OR abs:deployment OR abs:compression)
```

---

## 3. 每篇命中要记的四列

不要只记标题。按这四列记,结果才能直接生成相关工作对比表:

| 列 | 说明 |
|---|---|
| 覆盖哪些变换 | 量化(几 bit)/ 剪枝(方法与稀疏度)/ 蒸馏 / 合并 / 微调 |
| 是方法还是评估 | 方法 → 当基线;评估/基准 → 可能撞创新点 1 |
| 属性对象 | 遗忘 / 对齐 / 水印 / DP / 后门。**只有"遗忘"才直接相关** |
| 是否开源 | 要当基线跑就必须有代码 |

---

## 4. 什么情况算方向被击穿

按严重程度:

1. **致命**:一篇同时评估 ≥3 种部署变换 × 多种遗忘方法的系统基准 → 创新点 1 承重塌
2. **致命**:同方向的中文学位论文已做此题 → 开题过不去
3. **重伤**:剪枝和合并两格同时被填 → 只剩基线,无自己的格子
4. **可承受**:又出现一个缓解方法 → 创新点 2 本就不做缓解,加个基线而已
5. **可承受**:密码绑定被工业标准覆盖 → 相关工作里提一句,创新点 2 改述为"学术化 + 与评估结果耦合"

---

## 5. 检索纪律(上一个方向死于违反这三条)

1. **不要只查 arXiv。** 上个方向两次撞车,一次是数据库会议论文(VLDB 2025),一次是向量数据库论文——按"agent memory"检索永远找不到。
2. **不要沿单轴列关键词,要枚举交叉带。** 竞品坐在交叉格上:「属性 × 变换 × 是否给缓解 × 场景」。
3. **不要采信任何二手转述。** 上个方向两次误判都源于此:一次因采信"场景不同"而没读原文,一次因误读一行列表摘要而虚报撞车。**看到相关标题就把摘要拉出来自己读。**
