# 文献检索结果报告：遗忘鲁棒性 × 部署变换（任务 A–F）

- 生成日期：2026-09-09
- 任务书：`literature-search-brief-2026-09-09.md`
- 检索范围：arXiv（全量 176 条）＋ IEEE/ACM/USENIX/OpenReview/期刊（网页、Crossref、OpenAlex、Semantic Scholar）＋ 中文库（CNKI 公开镜像 / 万方 / 维普检索可见记录）＋ Google Patents / IETF / Sigstore / OpenSSF / GitHub
- 读法：每行按任务书 §3 的四列记录：**覆盖哪些变换 / 方法还是评估 / 属性对象 / 是否开源**。只收本人读到真实摘要/元数据者；摘要在付费墙内的只作"检索可见"标注，不作判定依据。

---

## 0. 结论速览

1. **未发现致命命中**。IEEE/ACM/USENIX/期刊与 OpenReview 公开记录中，没有"同时评估 ≥3 种部署变换 × 多种遗忘方法"的系统基准；arXiv 旧档 96 条复查也没有。
2. **中文同题学位论文未证实**。现有两本同方向的硕论（北邮方向、广州大学）都只到"隐私遗忘方法/LLM 遗忘"层面，公开摘要未出现"部署变换失效"这一核心命题；但**必须用 CNKI 凭据全文复核后才能排除**（见 §B）。
3. **Google Scholar 追加轮（2026-09-09）改变了格位判断——"量化+剪枝 × 多方法"已有 ICLR 2025 系统评估（见 §G）**。这不是任务书意义上的"致命"（Composable 只覆盖 2 个变换族、3 种遗忘方法、WMDP 能力遗忘，不含合并/蒸馏/继续微调，也不做遗忘集召回/证书绑定），但它**直接占住了"量化与剪枝对遗忘的影响 × 顺序效应"这一格**。方向表述不能再写"无人系统评估过多部署变换"，应改为"此前评估止于量化+剪枝且面向 WMDP 能力遗忘/组合顺序，缺少以遗忘声明为对象、跨合并/蒸馏/继续微调的行级评估与部署绑定"。
4. **格位占用有变化，需要注意**：
   - **模型合并轴不再真空**：Zenodo 2026-07 的 Madison Charlton 论文证明"只读未遗忘模型本身的证书在模型合并后必然失效"（小规模 planted-fact 实验＋证明）。它不是 ≥3 变换的多方法系统基准，**不致命**，但直接击中"merge 之后遗忘是否还能保证"，相关工作必须引，并且它在逻辑上**支持**你的创新点 2：证书必须绑定到实际部署/变换后的产物 T(θ)。
   - **剪枝轴出现方法级命中**：EMNLP 2026 的 FRAG/FRP 用"遗忘关键权重剪枝"做鲁棒遗忘（方法），扩散模型有"剪枝式遗忘后概念复活"攻击（Roots Beneath the Cut）。两者都不是"部署期权重剪枝使 LLM 遗忘复活"的系统评估，仍是方法/攻击行，但足以说明"剪枝 × 遗忘"交叉口有人站了。
   - **蒸馏轴被加强**：Distillation Robustifies Unlearning（NeurIPS 2025）用蒸馏做鲁棒遗忘；MRA（IJCAI 2025）证明蒸馏可泄露分类任务的遗忘成员。LLM 生成层的"部署蒸馏复活遗忘"仍空。
5. **创新点 2 的 D 最近邻比想象中近**：2026-03 出现个人 IETF Internet-Draft，覆盖**权重签名→量化认证（含逐层误差界）→部署认证→推理输出签名**全链，并把"量化毒化"列为威胁。工业侧还有 OpenSSF Model Signing v1.0（Sigstore model-transparency）、IBM 等公司的模型签名/运行时证明专利、SpeyTech certifiable-deploy。**但没有任何一方把"遗忘/评估结论"绑定到具体权重哈希与变换记录**——这与任务书判断一致，创新点 2 在相关工作里必须逐条回应。
6. **需要每两周复跑**：引文链以 Catastrophic Failure（ICLR 2025）和 Composable Interventions（ICLR 2025）为双探测器；OpenReview 在审（ICLR 2027 及之后轮次）无法匿名枚举，需人工在 OpenReview 搜索页复跑。

---

## A. 非 arXiv 场馆（IEEE / ACM / USENIX / OpenReview / 期刊）

| 论文 | 覆盖变换 | 方法/评估 | 属性 | 开源 | 判定 |
|---|---|---|---|---|---|
| Machine Unlearning Across AI Systems: A Scoping Review…，Electronics 15(16):3643，2026-08（Kim/Moon/Baik；DOI 10.3390/electronics15163643；摘要已读） | 不跑实验；证据地图中提及 4-bit 量化、解码方式、参考集选择、恢复测试等"变换/扰动"；159 篇源 | 综述＋"审计导向删除生命周期"（含 post-transformation verification 步骤） | 遗忘 | 否 | **黄旗-相关综述**：非新实验基准；但明确把"变换后验证"放进生命周期，需读全文并在相关工作回应 |
| On the Reliability of Targeted Unlearning in 4-Bit Quantized LLMs，IEEE DSN-W 2026（Syed Ahsan Ali；DOI 10.1109/dsn-w70714.2026.00034；摘要仅部分可见） | 仅 INT4 量化；LLaMA-3、TOFU、MIA、3 seeds | 评估（PGA/GAFT/SFT 等策略对照） | 遗忘 | 摘要未载代码（github.com/ahsanalidev/GAFTSFT 未能核实存在） | 单变换小规模评估；不致命 |
| Suppression or Deletion: A Restoration-Based Representation-Level Analysis of Machine Unlearning，WWW 2026 short（Jang/Lee/Kim/Jo/Woo；DOI 10.1145/3774904.3792896；摘要已读） | 无部署变换（SAE 专家特征＋推理期 steering） | 评估/分析："抑制 vs 删除" | 遗忘 | GitHub Yurim990507/suppression-or-deletion | 与"量化恢复"同族证据：遗忘多为抑制；不致命 |
| An Information Theoretic Evaluation Metric for Strong Unlearning，AAAI 2026（DOI 10.1609/aaai.v40i26.39373；OJS 可读） | 无 | 评估指标 | 遗忘（"strong unlearning"谱系） | 未查 | 指标论文，不致命 |
| Are we truly forgetting? A critical re-examination of machine unlearning evaluation protocols，Engineering Applications of Artificial Intelligence 167:113785，2026-03（Kim/Cha/Kim） | 无部署变换；评估协议复盘 | 评估 | 遗忘 | 未见 | 同团队（Sungmin Cha 系）评估协议系列；不致命 |
| We Forget It For You Wholesale—except when we come together: unlearning certificates do not survive when models merge，Zenodo 10.5281/zenodo.21684096，2026-07-29（Madison Charlton；摘要已读） | 模型合并（soups/task arithmetic/TIES/DARE；小规模 planted-fact，5 seeds） | 理论＋证明＋小实验：证书不可合成；合并安全当且仅当 partner 与 forget 方向正交；修复=在共享 base 遗忘 | 遗忘（证书/可验证性） | 未查（Zenodo 记录） | **黄旗-merge 轴最近邻**；不是 LLM 级多方法系统基准，不致命；强烈建议引用并回应其对创新点 2 的意义 |
| Recalling The Forgotten Class Memberships: Unlearned Models Can Be Noisy Labelers to Leak Privacy，IJCAI 2025 pp.6209-6218（DOI 10.24963/ijcai.2025/691；arXiv 2506.19486） | 蒸馏（教师-学生，分类设置） | 攻击/评估 | 遗忘（成员泄露） | 未查 | 蒸馏×遗忘的"泄露侧"已被占（分类级）；LLM 生成层仍未 |
| Forget by Uncertainty: Orthogonal Entropy Unlearning for Quantized Neural Networks (OEU)，ICML 2026 poster 65088（arXiv 2602.00567；接受记录已核实） | 量化网络上的遗忘方法 | 方法 | 遗忘 | 未查 | 量化×遗忘缓解方法；当基线 |
| Deep Unlearn: Benchmarking Machine Unlearning for Image Classification，IEEE EuroS&P 2025（检索可见，未读全文） | 未见部署变换 | 评估基准（图像分类） | 遗忘 | 未查 | **待人工复核**，暂不构成命中 |

综述类背景（已见但均无"≥3 变换 × 多方法"网格，未列入四列）：IEEE TNNLS 2025 “Machine Unlearning: Taxonomy, Metrics, Applications, Challenges, and Prospects”（36(8):13709-13729）；IEEE 2025 “A Survey of Machine Unlearning in Generative AI Models”（11006878）；USENIX Sec 2025 “Refusal Is Not an Option”（用遗忘攻击安全对齐，非部署变换）。

OpenReview 说明：匿名在审稿（未来轮次）无法通过 API 枚举标题；ICLR/NeurIPS/ICML 已公开决策中未发现新的多变换系统基准。

---

## B. 中文文献（CNKI / 万方 / 维普 / 专利）

| 条目 | 覆盖变换 | 方法/评估 | 属性 | 开源/获取 | 判定 |
|---|---|---|---|---|---|
| 李朝恒《人工智能模型隐私遗忘方法研究》，2025 硕士，导师陆月明（CNKI CMFD2026 记录 1025075616.nh；公开页需访问验证，摘要首段可见："动态更新模型结构实现特定数据信息消除"） | 公开摘要未见部署变换 | 方法（动态结构更新式隐私遗忘） | 遗忘/隐私 | 需 CNKI 凭据 | **致命性待排除**：同方向（隐私遗忘）学位论文，须全文核对是否含量化/剪枝等部署变换 |
| 《基于预测交叉熵的模型遗忘研究》，万方学位论文（记录 D03718948；平台首上网 2024-12-31；培养单位与作者公开页未显示） | 公开摘要未见 | 评估（以预测交叉熵量化遗忘有效性） | 遗忘 | 需万方凭据 | 指标类硕论；须查是否与"部署变换失效"重叠 |
| 李云灏《面向大语言模型的遗忘学习方法研究》，万方 thesis D04147018，广州大学 2025 硕士（计算机技术；摘要首段可见） | 公开摘要泛提"部署应用引发隐私泄露、知识残留、灾难性遗忘" | 方法/评估（LLM 遗忘） | 遗忘 | 需万方凭据 | **须全文复核**；摘要用语与本题有表面交集 |
| 岳梓岩等《基于机器遗忘的模型能力细粒度访问控制机制》，通信学报 2026,47(4):80-96（DOI 10.11959/j.issn.1000-436x.2026066；页面已读） | 文中梳理"神经元重要性剪枝的行为级遗忘/功能模块化"作为机制 | 方法/机制（细粒度能力访问控制） | 遗忘/安全 | 期刊开放页 | 中文同向期刊工作（把遗忘当访问控制），不是部署失效评估；须引用 |
| 《大语言模型"遗忘"评估体系与监管对策》，工业信息安全 2025(5)（武汉大学机构库条目检索可见；含"评测理想化、攻击面忽视、指标单一导致虚假合规、缺取证链"等表述） | 未见多变换网格 | 评估/监管综述 | 遗忘/合规 | 需订阅 | 监管话语同向；引用价值高，先不采信细节 |
| 张磊、张强、乔俊钊、吴明熙、张宁《基于大模型遗忘的隐私保护：方法、评估与挑战》，计算机应用研究 2026 年第 7 期（DOI 10.19734/j.issn.1001-3695.2025.12.0482） | 无部署变换实验；综述提及鲁棒性与剪枝式遗忘策略 | 方法综述＋评估框架（遗忘彻底性/效用/开销） | 遗忘/成员推理 | 万方/期刊页可检索 | 中文综述同向；与"部署失效"命题不同格 |
| 专利：融合奖励机制与模块稀疏化剪枝的大语言模型遗忘方法（2026-02 公开） | 剪枝作为遗忘手段 | 方法（专利） | 遗忘 | 专利公开 | 中文专利已把"剪枝式 LLM 遗忘"写为方法；不是部署后失效评估 |
| 专利：一种大语言模型驱动的推荐系统隐私记忆遗忘方法（CN121637565A，2026-03 公开） | 未见 | 方法（隐私记忆遗忘＋多指标闭环） | 遗忘/隐私 | 专利公开 | 背景 |

中文库纪律：除上述外未检索到"≥3 部署变换 × 多方法"的中文基准/学位论文。CNKI 镜像对详情页做了访问验证，**学校 IP/账号内全文复核是排除学位论文撞题的唯一途径**；本报告不替 CNKI/万方未公开的字段做任何推断。

补充（2026-09-09 二次核验，均为万方检索可见的硕论，公开摘要未见部署变换轴，仍列档备查）：

| 记录 | 说明 |
|---|---|
| 万方 D04147018 李云灏（广州大学 2025 硕） | 万方公开摘要另见："提出离线同构蒸馏模块，利用教师/学生模型知识蒸馏，构建知识被干预后的反事实分布……"——蒸馏出现在**遗忘方法内部**，不是"部署蒸馏后遗忘复活"评估 |
| 万方 D03529214《面向机器遗忘的伪装投毒攻击研究》（2024-09 上网） | 攻击侧学位论文，与部署变换无关 |
| 万方 D04166057《基于神经元重构的零数据类遗忘学习方法研究》（2025-10 上网） | 零数据类遗忘方法（神经元重构） |
| 万方 D04146250《面向深度学习的数据隐私保护技术研究》（2025-11 上网） | 训练/推理部署/微调环节的数据流转安全 + 成员推理防御 + 机器遗忘；公开摘要未显示"遗忘后部署变换失效"评估，**建议复核** |
| 万方 D03634263《基于特征对齐的模型遗忘算法研究》（2024-12 上网） | 特征对齐式遗忘算法 |

CNKI 摘要页（李朝恒，1025075616.nh）公开可见部分止于"……通过动态更新模型结构实现特定数据信息的消除，保障数据流转安全。然而……"；"然而"之后的内容及全文在付费墙/机构权限内，**仍需账号内复核**。

---

## C. 缓解/基线方法完整清单（四列制）

| 论文（编号为 arXiv/记录） | 覆盖变换 | 方法/评估 | 属性 | 开源 |
|---|---|---|---|---|
| Catastrophic Failure of LLM Unlearning via Quantization，ICLR 2025（2410.16454） | 多量化方法×多精度（核心 4-bit） | 评估（现象） | 遗忘 | GitHub zzwjames/FailureLLMUnlearning |
| Forgetting That Sticks（FTS/MANSU，2605.15138） | INT4/NF4 PTQ 为主 | 方法＋指标（MANSU、CAD） | 遗忘 | 摘要未载；待查 |
| GROM（2608.05783） | 低比特量化攻击下鲁棒（closed-form 权重编辑） | 方法 | 遗忘 | GitHub Batorskq/GROM |
| DurableUn / DurableUn-SAF（2605.02196） | INT8/INT4（NF4+LoRA 域）；BF16 对照 | 评估（QRA 攻击）＋方法 | 遗忘 | 未载；待查 |
| QUAIL（2601.15538） | INT4 | 方法（logits hinge 跨量化步长） | 遗忘 | 未载 |
| Quantization-Robust LLM Unlearning via LoRA（2602.13151） | 4-bit PTQ | 方法 | 遗忘 | 未载 |
| OEU（2602.00567，ICML 2026） | 量化神经网络（分类级/CNN 为主） | 方法 | 遗忘 | 未查 |
| Q-MUL（2503.13917） | 量化网络（分类级） | 方法 | 遗忘 | 未载 |
| GUARD-IT（2605.12765） | 不碰权重；在量化部署下仍有效 | 方法（推理期门控激活重定向） | 遗忘 | 未载 |
| Downgrade to Upgrade（2510.00761） | 权重量化与微调（2 类变换） | 方法（优化器降级→鲁棒盆地） | 遗忘 | 未载；OPTML 系作者 |
| FIT to Forget（2601.21682） | 顺序遗忘＋relearning/量化恢复攻击 | 方法＋基准（PCH） | 遗忘 | 未载 |
| NULLs / Natively Unlearnable LLMs（2606.13873） | 部署期"禁用 sink"即遗忘；鲁棒 relearn/提取 | 方法（原生可遗忘架构） | 遗忘 | 未载 |
| CRED（OpenReview hA8RPH58z1，2025-10） | 8-bit/4-bit 推理量化下稳定性验证 | 方法（推理期 in-context 概念遗忘，无参数更新） | 遗忘 | 未查（OpenReview 验证墙） |
| Quantization-Robust Unlearning through the Lens of Retain-Forget Loss Landscapes Interaction（OpenReview WZecHZcKN9） | 后训练压缩/量化 | 方法（保留-遗忘损失景观视角；在审/新提交，具体场馆待读全文确认） | 遗忘 | 未查（OpenReview 验证墙；Scholar 摘要片段可读） |
| ILU / Invariance（2506.01339） | 下游微调（多样任务） | 方法 | 遗忘 | 未载 |
| StableUN / Beyond Sharp Minima（2509.20230） | relearn/jailbreak | 方法 | 遗忘 | 未载 |
| Ssiuu / Erase or Hide（2509.22263） | 重训练（恶意注入/良性指令） | 方法 | 遗忘 | 未载 |
| Margin Calibration（2607.27836） | relearn（TOFU 三规模/多方法） | 方法 | 遗忘 | 未载 |
| MUDMAN（2506.12484） | 恢复性攻击 | 方法 | 遗忘 | 未载 |
| PRISM / Dual-Space Smoothness（2509.23362） | relearn/jailbreak（参数+表征空间） | 方法 | 遗忘 | 未载 |
| AGT^AO（2602.01703） | 内部恢复尝试 | 方法 | 遗忘 | GitHub TiezMind/AGT-unlearning |
| Unlearn-Smooth / SAM（2502.05374） | relearn 攻击 | 方法 | 遗忘 | GitHub OPTML-Group/Unlearn-Smooth |
| EMBER（2606.03695） | relearn（嵌入层编辑） | 方法 | 遗忘 | 未载 |
| RNA / Random Perturbations（2501.19202） | 扰动鲁棒 | 方法 | 遗忘 | 未载 |
| WARP（2512.00272） | 成员推断/重建（预/后模型差分） | 方法 | 遗忘（DP 系攻击） | 未载 |
| Distillation Robustifies Unlearning / UNDO（2506.06278，NeurIPS 2025） | 蒸馏（作为鲁棒化手段） | 方法 | 遗忘 | 未查 |
| FRAG/FRP（2608.25429，EMNLP 2026） | 权重"遗忘关键剪枝"做鲁棒遗忘＋relearn 预测器 | 方法＋评估 | 遗忘 | GitHub Yi1-Chen/FRAG |
| Roots Beneath the Cut（2603.06640） | 剪枝式遗忘（扩散模型）；剪枝位置侧信道→概念复活 | 攻击/评估＋防御建议 | 遗忘（扩散概念） | 未载 |
| J-Access / Measure, Don't Optimize（2608.11408） | 持续训练恢复预测（白盒审计 398 个公开模型/8 方法） | 评估（诊断） | 遗忘 | 未查 |
| On the Recoverability of Private Information Unlearning（2608.29943） | 逆向贪婪解码恢复 | 评估（白盒审计 5 方法） | 遗忘/隐私 | 未查 |
| PrivUn（2604.22076） | 三层攻击：直接检索/ICL 恢复/微调恢复 | 评估 | 遗忘/隐私 | 未查 |
| Unlearning Isn't Deletion（2505.16831） | 最小微调后表征恢复（多方法/多域） | 评估（表征级框架） | 遗忘 | 未查 |
| Model Tampering Attacks（2502.05209，TMLR） | 权重/激活篡改＋微调（16 步即撤销） | 评估（能力评估框架） | 对齐/能力移除（含 unlearning 基线） | 未查 |
| RUB（2504.14798） | 对抗恢复（UMA 映射攻击） | 评估基准 | 遗忘 | "将发布" |

说明：MANSU/GROM/FIT/ILU 等在任务书 §1 已列为既有基线；此处补齐了 2026 年新出现的缓解方法。多数新方法**未在摘要中声明代码**，作基线前需要逐一确认。FRP 的"pruning"发生在遗忘时（挑遗忘关键、保留不关键、幅值大的权重做剪枝），不是"部署期剪枝后遗忘复活"的场景——写相关工作时要区分清楚。

---

## D. 创新点 2 相关：工业界 / 标准 / 专利

| 条目 | 内容 | 与创新点 2 的关系 |
|---|---|---|
| OpenSSF Model Signing v1.0（OMS，2025-04）＋ Sigstore model-transparency（google/security 博客、github.com/ossf/model-signing-spec、sigstore/model-transparency） | 对整套模型文件签名（权重/配置/tokenizer），验证点：上传模型库、选择部署、再次训练复用 | 工业侧已有"制品完整性"答案；**只证"这是原厂模型"**，不证"遗忘声明在 T(θ) 上仍成立" |
| IETF draft-sharif-ai-model-lifecycle-attestation-00（2026-03-31，个人草案，2026-10 到期；已读全文） | 训练数据 Merkle 认证→权重签名→**量化认证（逐层误差界）**→部署认证（绑定推理签名密钥/权重哈希/硬件）→逐推理签名；威胁表含 QZ1 量化毒化（88.7% 注入成功率引用） | **D 格最近邻**：生命周期级"量化验证+部署绑定"框架已有人写，但对象是模型版本与推理输出，不是"遗忘/审计结论"。答辩材料须引并划清边界；另注意该 draft 到期后是否有修订/WG 采纳 |
| SpeyTech certifiable-deploy（2026；GitHub + 网站） | 确定性打包；推理 API 仅在权重/内核哈希与证书声明匹配后启用 | 安全关键 ML 的"认证→部署产物"绑定实践；非遗忘 |
| IBM US12141704B2 Neural flow attestation（Gu/Shu/Jamjoom/Ma，IBM） | 运行时神经流证明：云侧对已部署模型执行完整性证明 | 运行时完整性证明族；不涉评估声明 |
| US20210383026A1 Integrity verification of pre-compiled AI model blobs using model signatures | 编译后模型 blob 签名/校验 | 同上 |
| CN112528242A（AI 模型签名＋水印双验证）、CN114547633A/US20220164481A1（模型完整性与保密）、CN120372704B（区块链模型指纹确权）、KR20190112959A（模型签名验证装置） | 权重哈希/签名/指纹/区块链确权的中外专利族 | 完整性/确权工业实践已充分；**未见"遗忘声明绑定"专利**（检索可见范围内） |
| NIST AI 600-1 / AIBOM / CycloneDX / SPDX 系 | 内容来源与模型清单元数据；无密码绑定 | 相关工作的"文档层"，与"密码绑定"不同层 |

D 判定：按任务书第 4 节，"密码绑定被工业标准覆盖"属于**可承受**，但 IETF 草案与 OMS 意味着相关工作必须写得足够精确：你的贡献不是"给权重签名"（那是 OMS/IBM 已有），而是 **(1) 把遗忘的审计/评估结论本身做成可绑定的声明；(2) 绑定对象是实际部署/变换后的 T(θ) 及其变换记录；(3) 变换会使声明失效时可检测、可对账**。Zenodo merge 论文的"证书不可合成"结果可作为你放弃"只读 θ 的证书"、改为"对账 T(θ)"的理论动因。

---

## E. 引文链（Task E）

| 种子 | Semantic Scholar 引用数（2026-09-09） | 值得注意的引用者 |
|---|---:|---|
| Catastrophic Failure of LLM Unlearning via Quantization（ICLR 2025） | 多（约 60+，未逐条数） | GROM、FTS/MANSU、DurableUn、FIT、Distillation Robustifies、Model Tampering Attacks、Unlearning Isn't Deletion、WARP、Downgrade to Upgrade、J-Access、Compress and Forget、Bits and Memories 等（关键新条目均已读摘要并收入 §C/§F） |
| Forgetting That Sticks（2605.15138） | 1 | CircuitKIT（机制解释工具包）——尚无直接竞争者 |
| GROM（2608.05783） | 0 | —（太新；建议两周后复查） |
| Meaningful Data Erasure in the Presence of Dependencies（VLDB 2025） | 1 | Towards Inference-Aware Privacy Guidance for Data Preparation（数据库隐私侧，与 LLM 部署变换无关） |

复跑建议：以第 1 条为探测器每两周跑一次 "Cited by"；对 §C 中 2026 年新条目（GROM、FTS、DurableUn、FRAG/FRP、Downgrade to Upgrade、Margin Calibration）各自追一次被引；OpenReview 搜索页手工复跑一次"machine unlearning"+"quantization/pruning/merging/deployment"。

---

## F. arXiv 剩余 96 条（start=80–175 全量复查）

对全部 96 条逐条读了标题（其中 ~14 条近候选读了完整摘要）。**结论：与任务书 §1 判断一致，旧档没有行级多变换系统评估**。此区间对"遗忘鲁棒性"最重要的增量：

| 论文 | 覆盖变换 | 方法/评估 | 属性 | 开源 |
|---|---|---|---|---|
| Downgrade to Upgrade（2510.00761） | 量化＋微调（作者显式列出 post-unlearning weight quantization / fine-tuning） | 方法（优化器级） | 遗忘 | 未载 |
| Distillation Robustifies Unlearning（2506.06278） | 蒸馏 | 方法 | 遗忘 | 未查 |
| Q-MUL（2503.13917） | 量化（分类网络） | 方法 | 遗忘 | 未载 |
| Model Tampering Attacks（2502.05209） | 权重/激活篡改、微调 | 评估 | 对齐/能力（unlearning 为基线） | 未查 |
| Unlearning Isn't Deletion（2505.16831） | 微调恢复 | 评估 | 遗忘 | 未查 |
| RUB（2504.14798） | 对抗恢复（非部署变换） | 评估基准 | 遗忘 | "将发布" |
| Compress and Forget（2608.18578，经引文链发现） | INT8/INT4 量化 | 评估 | **非遗忘**（工作记忆/主动干扰；量化不保记忆属性） | GitHub ShayanShahrabi/compress-and-forget |
| Bits and Memories（2607.25451，经引文链发现） | 5 种精度量化 | 评估 | **非遗忘**（逐字提取/记忆保持；量化是"选择性遗忘者"但不足以作隐私防御） | 声明开源 |

后两行属性不是遗忘，但可作为引言论据："量化连记忆都删不干净，遑论依赖权重更新的遗忘方法"。

---

## 需要人工/凭据复查的清单

## G. Google Scholar 追加轮（2026-09-09；本节为最重要的增量）

Google Scholar 直连可用后，用 Scholar 补齐了 arXiv/Crossref 检索看不到的场馆与在审记录。最关键的命中：

| 论文 | 覆盖变换 | 方法/评估 | 属性 | 开源 | 判定 |
|---|---|---|---|---|---|
| Composable Interventions for Language Models，ICLR 2025（Kolbeinsson 等；arXiv 2407.06483；PDF 全文已读） | 剪枝 SparseGPT/Wanda（0–75% 稀疏）× 量化 GPTQ/AWQ（2–16 bit），两种先后顺序；另与知识编辑两两/三组合成 | **系统实验**：417 组合；遗忘方法 GA/GD/RMU；指标 WMDP cyber+bio（3,260 题）；模型 Llama-3-8B / Mistral-7B-Instruct / Yi-1.5-9B-Chat | 遗忘（WMDP 能力遗忘；25%=随机） | GitHub hartvigsen-group/composable-interventions | **重伤级竞争（非致命）**：量化+剪枝 × 多遗忘方法的 LLM 系统评估已在 ICLR 2025 出现并明确测了"先遗忘后压缩/先压缩后遗忘"。主要结论：压缩显著损害遗忘（RMU 高稀疏更差；GD 先遗忘再剪枝最好、先量化再遗忘可以最好；GA 本身太差）。**它与你的差异**：仅 2 个变换族；无模型合并/蒸馏/继续微调；无 TOFU/canary 类遗忘集召回或 MIA；无顺序之外的行级"部署变换破坏认证"框架；无密码绑定 |
| When Forgetting Fails: Machine Unlearning for LLMs Across Training, Post-Training, and Inference，HAL hal-05653389，2026-06（Assellaou 等；PDF 全文已读） | 不跑实验；综述 50 方法按训练/后训练/推理分阶段；文中覆盖量化恢复（4-bit 83%）与剪枝式遗忘方法；**全文无 "model merging" 一次** | 综述＋4 级量化阈值"认证"框架（非密码）＋复合 AI 系统防御 | 遗忘 | HAL 开放 | **黄旗-高价值相关综述**：与你创新点 1、2 在"话语层"高度相邻，但没有新实验、无合并轴、认证非密码绑定。相关工作必须引，并明确"我们补的是实验网格＋部署产物绑定" |
| CRED / Contrastive Residual Embedding Decoding（OpenReview hA8RPH58z1，2025-10） | 8-bit/4-bit 推理量化稳定性 | 方法（推理期 in-context 遗忘） | 遗忘 | 未查 | C 行新增；OpenReview 需人工读全文 |
| Quantization-Robust Unlearning through the Lens of Retain-Forget Loss Landscapes Interaction（OpenReview WZecHZcKN9） | 后训练压缩/量化 | 方法（在审或新提交） | 遗忘 | 未查 | C 行新增；**重点复跑对象** |

Scholar 追加轮另确认的英文背景项（不构成命中，引用可用）：Casper 等 “Open Technical Problems in Open-Weight AI Model Risk Management”（arXiv 2608.07514，明确列出微调/蒸馏/合并/量化序列仍是评估空白）；Wiley SPE 2026 “Security in the Fine-Tuning Lifecycle of LLMs”（综述把模型合并/量化/遗忘并置）；MLSys 2026 之外还有 ICLR 2025 “Reassessing Layer Pruning in LLMs”（剪枝本身的能力影响，非遗忘）。

对创新点 1 的改写建议（避免被 Composable 或 HAL 综述抢先）：标题与贡献不要写"首次系统评估部署变换下的遗忘"，改写成 **"面向遗忘声明的行级多变换基准：以遗忘检查（forget-set 召回/MIA/提示审计）为对象，统一施加量化、幅值剪枝、蒸馏、模型合并、继续微调等变换链，测量声明在部署产物上的失效并给出可对账的部署绑定方案"**。与 Composable 的差异要落在：对象（检查项而非 WMDP 总分）、变换集合（含合并/蒸馏/微调与变换链）、目标（部署认证可绑定）三点上。

---

## 需要人工/凭据复查的清单

1. **CNKI/万方学位论文全文**（决定致命与否）：李朝恒（CMFD2026/1025075616）、李云灏（万方 D04147018）、《基于预测交叉熵的模型遗忘研究》（万方 D03718948）——确认其方法是否包含"遗忘后施加量化/剪枝/合并/继续训练并评估失效"。
2. **IEEE/ACM 全文检索**：本环境只能以网页/Crossref/OpenAlex 覆盖，建议用学校账号在 IEEE Xplore/ACM DL 对任务书 A 的检索式复跑一次；重点看 DSN-W 2026 的完整方法表与 EuroS&P 2025 Deep Unlearn 基准。
3. **MDPI Electronics scoping review** 全文（开放获取）：确认其对"post-transformation verification"的覆盖深度，写作时决定放在 related work 哪一段。
4. **Zenodo merge 论文全文**：核对其证明假设（planted-fact 规模、合并方法集合）能否平移 LLM 表述。
5. **IETF draft 后续状态**：2026-10 到期前查是否有 -01 修订或 WG 采纳；答辩前此项可能变化。

## 检索方法与局限

- 判定依据均为本人直接读取的 arXiv 摘要/Crossref/OpenAlex/期刊页/Zenodo/IETF 全文；凡是只有检索快照、未读原文的，一律标注"待人工复核"而未计入命中。
- OpenReview 匿名在审稿无法枚举；IEEE CSDL/CNKI 镜像对脚本访问做了限制，部分详情页只能记录"检索可见"。
- 本轮不涉及 PDF 落地；如需按命中清单下载，可随后一键执行。
