# R13–R20 开发验收、画质评价与最终作品发布门禁

> **状态：未来验收协议提案（未执行）。** 此文将每轮源码/离线/云端原生/Windows 本地/真实画质/独立人工结论严格区分。沿用已合并的 [Round 12 本地验收协议](ROUND12-LOCAL-ACCEPTANCE-PROTOCOL.md) 和 [完整作品最低证据标准](ARTWORK-ACCEPTANCE.md)。**不能因本文件新增就勾选任何完成项**。
>
> [R13–R20 路线图](ARTIST-ROADMAP-R13-R20.md) · [目标架构](ARTIST-ARCHITECTURE-R13-R20.md) · [原生本地历史报告](ROUND12-LOCAL-ACCEPTANCE-REPORT.md)

> **实施时间调整（用户 2026-11-24 指示）：** 从 R14 起，各轮开发以 GitHub Python 3.10/3.13 离线 CI、安全/兼容测试为必须门禁，暂不反复执行昂贵的真实三构建 Krita、独立视觉评审、人工评审与 24 项完整画作验收。详细见 [统一最终验收与成本控制政策](CONSOLIDATED-ACCEPTANCE-POLICY.md)。本文件以下**量化标准和必须保存的证据没有降低**；目前没运行的 G2–G5 项必须写 `NOT_RUN`，直到 R20 集中验收。

## 1. 正确区分阶段结果和最终结果

所有测试项统一状态：`PASS` / `FAIL` / `BLOCKED` / `NOT_RUN`，若存在独立评审争议，可另外报告 `DISPUTED`（不得计入 PASS）；真实 native effect 不明另报 `unknown_needs_review`，禁止自动重试。

| 等级 | 说明 | 可以宣称 | 不能宣称 |
| --- | --- | --- | --- |
| Source authored | 有代码和设计文档 | 有实现候选 | 可运行、可画好 |
| T1 Cloud offline | CI 真实执行 Python 3.10/3.13 测试 | 指定版本的协议/几何/故障测试通过 | Krita 真实原生通过 |
| T2 Real cloud native | 特定 Linux Krita 版本、真实 Bridge、真实 KRA/PNG/reopen/hashes | 该环境下已测命令有效 | Windows Stable/Next 或画质通过 |
| T3 Windows local native | 指定 Krita Stable / Next Qt5 / Next Qt6 原生证据 | 该构建的指定操作通过 | 通用画师/完整作品通过 |
| T4 Artwork visual/human | 真实画面与 KRA 由独立视觉审查和真人审查 | 该特定作品被接受 | 所有题材泛化能力已达标 |
| Campaign | 封存 24 任务全部计入分母，达到总门槛 | 第一版有限范围的绘画能力达标 | 任意主题专业级质量 |

跨构建结果不可互相挪用。图层数、笔触数、JSON 合规率、planned brush diversity、覆盖率、内置 critic 的“pass”，都不等于独立艺术通过。

## 2. 门禁分层：用小样先淘汰问题，再做大作品

**G0 需求和安全**：锁定 source SHA、架构/Schema、测试输入、预期结果、许可和成本上限；所有本地/外部调用需明示。失败后不篡改门槛。

**G1 离线函数/安全测试**：JSON/geometry/fuzz、边界/循环、invalid enum/超大输入、path traversal、未知副作用、恢复、模型假结果与真实提供者错误等；GitHub CI Windows 3.10/3.13 都过。不得把假 PNG 伪装成真实 KRA。

**G2 真实云端 Krita 小样**：有 Krita Bridge 真正执行、真实阶段预览、非空 KRA 和 PNG、fresh copy reopen、RGBA/ICC 严格比较，保留实际哈希。可按成本和流程变化决定是否运行，并明确 NOT_RUN 与原因。

**G3 Windows 本地最小技术矩阵**：三构建各单独会话，检查笔刷、阶段、区域、save/export/reopen、选区/蒙版/颜色/已修复问题。失败则不要开始完整耗时画图。

**G4 小规模艺术 A/B**：同一画面、seed、画布、允许预设、模型/参数、预算、评审方式锁定；仅对比一个算法变量；真实像素 + 匿名盲评，记录人类意见和反例。

**G5 完整艺术样本/正式 24 题**：小样过门槛之后才开展高成本完整作品。独立视觉与真人签认、完整可编辑证据，并记录所有失败尝试。

研发 PR 可以在明确“源实现”状态下合并，但不能借合并自动提升 G3/G4/G5；每轮必须清楚写待验收项及阻塞风险。需用户同意后才使用本机 Krita 和付费模型，不自动开始长期或大批量外发。

## 3. 每一轮的具体验收清单

### R13：原生稳定与兼容

- [ ] 复现 Stable 自动多点 segmented fallback 的暗色接缝，在透明底同颜色/大小/压力条件下 25%、50% 不透明度记录本体 alpha 与接点 alpha。已知历史为 64/112、128/192；修复不应出现非预期叠加，或明确拒绝不支持的 continuous 行为并标注未通过。
- [ ] Next Qt5/Qt6 的 continuous 对照和强制 segmented 负面样本，确认原因而不把工作绕到其他笔刷隐藏问题。
- [ ] Windows backslash/archive 路径诊断验证：真实阶段归档路径、SHA、文件存在性、目录边界；恶意 traversal 与被修改的哈希必须拒绝；检查已有候选修复是否仍成立，不能引用旧报告当新 CI。
- [ ] Stable / Next Qt5 / Next Qt6 分别完成三阶段图、KRA 编辑层、导出/重开 RGBA 和 ICC 一致。
- [ ] 断连/超时、未知状态、重复请求、错误会话、隐私和旧 API 回归；不自动重放。
- [ ] 文档列出每一构建“supported / unsupported / unknown”，没有实际验证就不能填 supported。

**结论输出**：支持矩阵 + 真实原生 RGBA/alpha 截图与 SHA + 异常日志 + 修复前后对照。若 Stable 根本不提供 continuous API，应接受**受限兼容/显式降级**的设计决策，不在没有像素证据时写“已修复”。

### R14：语义规划与合法结构

- [ ] ArtBrief/CompositionGraph/PaintPlan 的严格版本化 schema、字段长度/对象数/深度/预算限制。
- [ ] 独立 solver 将归一化布局变为合法几何，测试主体 bbox、polygon、曲线、遮挡、ROI、旋转和不同画布尺寸。
- [ ] 对未授权命令、任意路径、模型返回 HTML/无效 JSON、重复 ID、过预算、超长 token、非单调阶段和未知字段拒绝。
- [ ] 最多两次有界校正（固定上限，审批边界内）；记录每次错误，不能吞错或者修改测试题。
- [ ] **建议性能目标：** 独立锁定 30 条非正式艺术题库任务，至少 27/30 产生合法可编译计划，且记录每题模型/参数/调用次数/实际用户成本。若模型不可用，独立报告 local candidate/模拟通过，不能填真实模型通过。
- [ ] R7–R12 的 v3/v4 兼容、计划 SHA 和阶段用户批准保持正常。

**说明：** 27/30 是**初始建议阈值**，实施前要冻结，并根据预试数据经独立文档审查调整，而不是看到正式结果不合格后降低；结构正确必须另经真图检查。

### R15：轮廓、区域、遮挡与铺色

- [ ] 合成多边形：凸/凹、孔洞、多个非连接部分、自交/退化；无跨主体填色。
- [ ] 锁定对象、选区、蒙版、z-order、边缘羽化与真实 Krita 像素；无需一次支持所有构建不可实现的原生 API，应记录缺失。
- [ ] 固定杯子、树冠与树干、室内墙面/床/椅等至少三类样本；每个 sample 拥有封存的目标区域和允许误差。
- [ ] **建议覆盖阈值：** 指定需填充的内部区域有效覆盖 ≥95%；在非授权区域剔除预设笔尖/抗锯齿允许边界后的可见泄漏为 0；边缘误差与空洞单独报，不以整个背景/非白像素误当有效覆盖。
- [ ] 确保区域底色和纹理分离在有实际贡献的可编辑层，导出/重新打开像素一致。
- [ ] 比较旧版 parallel rough strokes 与新版 region fill 的实际视觉效果，封存负例。

### R16：细线、渐变压力与自然笔触

- [ ] 固定压力梯度、双向压力曲线、尺寸/opacity/不同预设，对每个 Krita build 运行真实校准；物理数位笔测试**单独**标记，Bridge 合成 pressure 不冒充硬件压感。
- [ ] 连续模式起/中/末端、不同方向/曲率、长短线、相邻笔触过渡，比较平滑/断裂/误叠色；所有笔刷参数可溯源。
- [ ] 限制机械圆点、等距线/重复端点和无目的粗笔，但允许有意图的底色宽笔/厚涂；依据**真实 PNG**评估。
- [ ] 与当前真实输出进行同题材固定 A/B，至少包含人物/动物线条、布料褶皱、植物/毛发等三个线条机制；预注册“自然度、结构贴合、接缝、控制性、细节质量”五项盲评。
- [ ] **建议改进目标：** 五维平均至少 3.0/4、每项至少 2/4，且与旧版同样本相比在独立盲评平均提高 ≥0.5/4。分数需有真实人类评价者、身份/时刻和 PNG/KRA hash，不以一个内部 AI 分数代替。
- [ ] 对连续 API 缺失构建给出明确能力限制、稳定 fallback 或安全拒绝。

### R17：色彩、材质、光照

- [ ] 体积与明暗块先建立，受光方向/阴影/环境色逻辑一致；材料局部方向场和不同硬软边。
- [ ] 同固定场景至少三种有差异材质（布料、金属/陶瓷、植被/水等），真实 Krita native 输出和 ROI crop，保持布局/seed/model/preset/主色调一致。
- [ ] 颜色空间/ICC/profile、透明混色、Krita Color Smudge 等按构建验证，不捏造逐点颜色控制。
- [ ] 对材质识别、表面方向与笔触尺度、光色一致性、边缘与机械重复分别 0–4 分；沿用 [R12 material A/B](ROUND12-LOCAL-ACCEPTANCE-PROTOCOL.md) 的候选平均 ≥3.0、单 ROI ≥2.0、相较旧版改善 ≥0.5 才能宣称提高。
- [ ] 增加颜色数量或 ROI 覆盖率本身不计入艺术通过；保留全部败例。

### R18：线稿采集、检索和学习效果

- [ ] 有权使用的本地文件、已导出 HTML+图片、受控公开文章等导入；默认 dry-run，用户决定下载/存储/上传范围。
- [ ] SHA 和来源许可记录，不同 can_store/can_analyze/external_upload/training/publish 独立拒绝；撤销/不明许可不越权。
- [ ] 线稿/彩图/摄影/图标/二维码分类，长图分割，源图不覆盖，结构提取和可追溯版本。
- [ ] 30–50 份合法样本的批量导入、去重、追溯、人工抽查；故意损坏/大文件/恶意 zip/SSRF/路径穿越/权限拒绝测试。
- [ ] 知识库检索对照画图：相同模型、prompt、参考和预算，开启/关闭检索；对比结构识别和线条自然度，真实 KRA/PNG + 评价记录。没有改善就报告结果，不假称“模型已学会”。
- [ ] 训练数据集与正式 24 项持出评测集隔离，公开索引仅含脱敏且被授权的数据。

### R19：真实视觉反馈与局部修订

- [ ] 视觉模型必须真实收到完整 PNG；ROI/stage/reference/元数据各自外发需授权；不得从 JSON/文件名推断像素。
- [ ] 固定错误集合至少包含主体缺失、部件关系/透视、颜色与光照、区域越界、重复机械线、错误评价建议。
- [ ] 反馈绑定原 PNG 与 KRA hash、部件/ROI、可信度和具体可见证据。模型不直接给 native 执行代码。
- [ ] 用户逐次批准明确的局部修订；ROI、保护层和原文件无误伤，新版本保存严格 reopen；丢失响应禁止盲重试。
- [ ] 独立比较修订前后像素与艺术分；报告成功、变差、范围越界、无可见改善、成本、调用上限和 API 失败率。
- [ ] 内部 critic 的“provisional pass”永不等于独立人类审查。

### R20：完整软件工作流和正式作品

- [ ] 用户通过 CLI / Dock / dashboard 可选文本、授权线稿/参考、风格、预算和修订目标。
- [ ] 阶段预览和实际状态一致，暂停恢复安全，模型连接失败可解释，支持数据授权与费用限制。
- [ ] 可编辑 KRA、完整 PNG、真实阶段预览、执行账本、图层贡献、hash 和用户审阅记录完整；失败原件不覆盖。
- [ ] Stable、Next Qt5、Next Qt6 的核心兼容性矩阵，严格导出/重开、非法命令、安全/恢复回归，CI 通过。
- [ ] 正式封存的 24 项任务，要求下文所有条件；公开的是脱敏结果而非原始用户图像。
- [ ] 安装、迁移、操作、贡献和安全文档更新，有回滚方案和已知功能差异清单。
- [ ] 发布不能把“可执行”说成“能创作专业好画”，按题材/构建/模型/预算限制清楚列出。

## 4. 正式 24 项完整作品：继承 R12 协议，不准软化

完整基准是**六题材 × (三个未见过的文字任务 + 一个具有独立授权的参考任务) = 24**。风景参考采用已锁定的 sunset-alpine-lake；其他有来源/授权的参考图按原合同记录。正式运行前锁定任务、契约、输入/reference SHA、模型标识与参数、Krita build、画布、评价表；不能挑选自己最容易画的题目、只统计成功的运行或为已暴露的具体题目手写硬编码策略。

**每一幅计入合格必须同时通过：**

1. **Technical gate：** 真实 Krita native、8 个以上具有真实可见贡献的可编辑绘画图层、三张真原生阶段全画面预览、KRA/首次 PNG/真实 fresh reopened PNG 严格 RGBA + ICC/profile 匹配、确切哈希与完整执行证据。不能粘贴参考 PNG 冒充。
2. **Visual gate：** 独立视觉评审真实打开参考和最终 PNG、各阶段图，审查要求对象/关系、结构和画质；失败模式/证据真实。
3. **Human gate：** 人类真实看见 PNG，并重新打开 KRA 检查编辑层，给出明确签署的通过或拒绝。缺失人工通过不能写 artwork accepted。
4. **Rubric gate：** 6 维（任务/参考符合性、构图、结构识别、材质光色、自然笔触、完成度），每维 0–4，总分至少 18/24，没有维度低于 2，任务/参考符合性、结构识别、完成度各至少 3；具体可见理由和 hash 绑定。
5. **Rights/security gate：** 上传许可、参考权利、文件无越权与证据隐私合规。

**Campaign 合格：** ≥18/24 全部通过；每题材 ≥3/4（其中文字 ≥2/3），参考图 ≥4/6。所有 FAIL/BLOCKED/NOT_RUN/DISPUTED 保留在分母。无法执行的任务不能默默删除、换成更容易的任务。该标准衡量**受测条件下的有限通用能力**，不代表能稳定绘制所有主题或任意艺术风格。

**现有审计限制：** `scripts/artwork_acceptance_audit.py` 与固定山间湖泊合同绑定，不能对其他 23 项报告通用完整审计成功。R20 应先开发可加载合法 task-contract 的统一审计模块、回归旧合同；可验证证据完整性和 hash，但不能代替人类对构图/画质的判断。

## 5. A/B 盲评准则与人类评价

- 先锁定评分目标、真实图片、随机化标签方案、有效样本数和比较变量，后运行。
- 对比应保持 source SHA、Krita build、相同画布/题目、相同模型与参数、种子、素材授权、预算和可用预设；如果算法导致步数不同，记录真实数目和时间，不暗称其他变量完全相等。
- 评审收到 **真实完整 PNG + 相同 ROI** 而非目标标签/工作流名称；报告应解释对每个对象或材质的实际观察。
- 视觉模型与人工评审分开；模型不扮演人类。若对同一作品有争议，以 `DISPUTED` 保留，并请独立人工复评；不能平均掉反对意见。
- 公开仅可脱敏评分/摘要/经授权预览；原始 KRA、用户线稿、私有源图和来源凭据保留本地。
- A/B 进步与完整作品达标是两种独立断言。改进 0.5 分但绝对分仍极低，不能当成功。

## 6. 必须保留的原生证据模板

每轮测试/每件艺术作品应在唯一 ignored directory 下保留：

    artwork-results/<campaign-or-run-id>/
      manifest.json              # source sha, build, prompt/contract hashes, rights
      environment.json           # OS, Krita/Qt, plugin, known capability
      approved-plan.json         # authentic approved plan digest
      execution.json             # native command log/ledger/status
      layers.json                # real layer graph & visible contribution notes
      stages/                   # real stage previews from Krita
      artwork.kra               # editable original
      artwork.png               # export from that artwork
      reopened.png              # exported from fresh reopened copy
      reopen-evidence.json      # strict RGBA & ICC/profile measurements
      screenshots/              # real Krita window, if required
      reviews/
        visual-model.json
        human.json
        scorecard.json
      versions/                 # all failed originals and repaired successors
      summary.md                # PASS/FAIL/BLOCKED/NOT_RUN, caveats, timings, cost

相应基准已有更加严格的文件名和版式要求时，以 [ARTWORK-ACCEPTANCE.md](ARTWORK-ACCEPTANCE.md) / [R12 protocol](ROUND12-LOCAL-ACCEPTANCE-PROTOCOL.md) 及相关 schema 为准；本模板不能代替现有审计脚本期待的 `scene-plan.json` 或 `layer-graph.json` 等文件名。

## 7. 成本、进度与发布纪律

- CI 和纯结构测试优先；昂贵 native 测试只在相应需要时运行，完整大作品在先前小门禁通过后再安排。
- p50/p95 per-stage 与端到端真实 wall-clock 分开，嵌套阶段不能直接相加；费用与失败重试数独立列出。
- API 调用需要可配置的模型、explicit consent、timeout、max calls、token/image budget、estimated/actual cost；“额度不够”不是改写结果 PASS 的理由。
- 用户本人/授权人工进行每阶段/作品判断，Agent 不替人工填成功；不经批准不自动启动原生绘画、不碰个人 KRA。
- 每轮 PR 附源 SHA、实际 CI/原生链接、仅适用的构建、风险和未完成项；允许独立的安全修复 PR，但绝不修改原失败数据或重命名假成功。
- 原始正式 24 项锁定合同与数据留出，研发只使用独立开发题库；如需更换基准，建立**新版本基准**并说明原因，不覆盖旧版或把旧失败消除。

## 8. 完成定义与不可提前声称事项

`R13 Done` 等仅代表该轮预定门禁按实际证据达标；某轮源码、CI、云端原生已过并不自然意味着真实艺术验收过。计划承诺“尽量做到第一版功能基本完善”，不是“任意指令皆可专业成画”的产品保证。

第一版可称为 `functional milestone` 的条件：

- 核心 CLI/可编辑原生工作流与最常用文本/参考/线稿/局部修订模式可用，已知安全缺陷有明确关闭状态。
- 目标三构建能力矩阵与真实 KRA export/reopen 有证据；不能跨未测试构建泛化。
- 结构、区域、精细笔触、颜色材质的最低艺术小样通过独立 A/B 或人工验收。
- **正式 24 项**按固定 rubric 和 campaign 阈值实测合格，所有失败留档。
- 用户在完整工作流中可控制审批、外发数据、成本、失败与版本保全。

没有满足某条件，应继续有针对性地开发或如实下调**产品适用范围**，不能偷偷降低验收条件。
