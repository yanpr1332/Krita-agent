# Krita Agent R13–R20 目标架构与渐进式迁移设计

> **架构提案 / 非已实现功能。** 2026-11-24。此设计不修改原有 R1–R12 API 或 Krita Bridge。实施必须经独立开发 PR、真实能力探测与验收。当前实际能力详见 [ARCHITECTURE.md](ARCHITECTURE.md)、[ROUND12-API.md](ROUND12-API.md) 和 [本地验收报告](ROUND12-LOCAL-ACCEPTANCE-REPORT.md)。

[总路线图](ARTIST-ROADMAP-R13-R20.md) · [素材与学习](LINEART-DATASET-AND-LEARNING.md) · [量化验收](ARTIST-ACCEPTANCE-R13-R20.md)

## 1. 为什么不能沿用“大模型直接写完整 ScenePlan v4”作为唯一入口

现有 v4 已有高层的 subject/stage/gesture/coverage/accents 表示，但模型仍须自行生成大量复杂结构、像素坐标、材料参数、polygon 和 brush 细节。R12 首次正式 18/18 文本规划未通过结构校验（13 个坐标越界、3 个材质参数越界、1 个笔数限制、1 个风格失败），说明结构规范和自由生成的职责边界不合适。之后的轻量局部重组试画能运行但仅 6/24 分。问题包含两层：

- **规划可靠性不足：** 模型产生合法候选的概率低，错误排查成本高。
- **视觉绘画能力不足：** 成功编译不等于形成合理结构；区域填色、方向场和笔触节奏仍机械。

解决方法不是放宽边界、自动绕过安全检查、让模型多输出几万 token，也不是用纯随机算法“模拟手绘”。应采用**模块化单体架构：语义规划 → 结构/几何 → 绘画意图 → 安全编译 → Krita 原生执行 → 真图评审 → 有界修订**。

## 2. 七个职责层与数据流

    User brief / image / line-art / authorized library
       │
       ├─ Input & Provenance Gate（本地 SHA、许可、外发/训练权限）
       ├─ Perception & Retrieval（结构观察、线稿/技法检索）
       │
       ▼
    AI Director / high-level planner（少量稳定的结构化语义）
       │  ArtBrief + CompositionGraph
       ▼
    Geometry & PaintPlan Solver（确定性 ROI、多边形、结构与边界）
       │  PaintPlan: area / contour / accents / material / revision
       ▼
    Safe Compiler（白名单，预算，路径，颜色和版本/计划哈希）
       │
       ├─ Region/Fill engine → 原生选区、mask、形状和填充（探测后启用）
       └─ Stroke engine → 原生连续笔刷 + 受控压力/尺寸/透明度
       │
       ▼
    Authenticated Krita Bridge → editable layers / KRA / real PNG
       │
       ▼
    Pixel Evidence / Critic / Human Review
       │
       └─ Bounded revision proposal → explicit user approval → new version

**分层职责：**

| 层 | 输入 | 输出 | 强制边界 |
| --- | --- | --- | --- |
| Input & Provenance | 文本、文件、URL/网页导出、许可 | 内容哈希、可信路径、数据用途权限 | 不能因可下载就默认可训练/外发 |
| Perception & Retrieval | 已授权图像和本地索引 | 对象/部件/ROI/轮廓与检索证据，含不确定性 | 像素/边缘分析不自动等于语义或笔顺识别 |
| AI Director | ArtBrief、可用技巧、结构观察 | 简洁语义/比例/阶段目标 | 无任意 IPC、文件路径、具体 Krita 操作权限 |
| Geometry & Solver | 语义约束、区域、锚点 | 受画布及主体边界约束的合法几何 | 每条坐标合法；自交/悬空/泄漏拒绝 |
| PaintPlan & Compiler | 区域任务、线条意图、颜色/笔刷契约 | 经批准、可追溯的 native allowlist task | 多版本兼容、预算检查、不可偷加 stroke |
| Executor & State | 已验证的命令/会话 | 真实原生笔画、图层、预览、KRA、hash | 不确定 side effect 不重放；阶段逐一批准 |
| Evaluation & Revision | 真 PNG/KRA/阶段/评分/用户指令 | 问题、绑定 ROI 的修订建议、独立评审 | 不能冒充人工、不能越 ROI、不能复用旧失败冒充通过 |

软件内部应是同一个可部署的 Python Controller，不建议先拆成大量网络微服务或多个相互自由讨论的 Agent。需要可替换的 ModelProvider、可审计的 Geometry Solver、严格 native Bridge 三个稳定边界。

## 3. 三个中间契约：ArtBrief / CompositionGraph / PaintPlan

**强约束：模型仅产出前两个的简洁语义提案；需要真实物理坐标、复杂 polygon、mask 和下游执行表，由 solver/compiler 产生。**

### 3.1 ArtBrief（用户意图）

建议字段：

- schema、用户请求文本/目标、画布参数与分辨率、风格/媒介、复杂度/预算。
- mode: text_to_art / lineart_guided / licensed_reference / style_reference / local_revision。
- required_subjects、required_relations、forbidden_elements 和必须保持的锁定对象。
- references: 列出来源 ID/hash、分析用途；私有路径不传给模型或日志；外发与训练权限独立。
- stage_preferences、brush_policy、审批/模型预算。此层没有任何可执行 Krita 步骤。

### 3.2 CompositionGraph（绘画结构，不是完成的坐标密集脚本）

对象节点：
- id、name、semantic_class、parent、normalized_bbox、depth_order、confidence。
- part_ids、silhouette_hint、pose/anchors、orientation、material_hints、edge/lineart style hints。
- 尺寸、包含、遮挡、近远、透视、受光方向的明确关系约束；缺失部分需标为 unknown，而不是模型猜测。
- 不将整个人物/树冠简化成一个矩形中心点的统一方向场。复杂对象需部件级 orientation/flow。

建议模型产生**0–1 的归一化布局和关系**；绝对像素、合法闭合轮廓和准确 ROI 由 Python 几何模块构造。布局自相矛盾必须返回结构化诊断。真实参考输入是独立的 authorized analysis，不允许把参考像素直接变成 native 成品。

### 3.3 PaintPlan（怎样画）

- 画面级：sketch → block_in → form → material → detail → polish，3–6 阶段按需要。每阶段有预算、目标、批准 hash。
- 区域级：fill/base_value/shadow/highlight/edge/soft_blend。包含主体/部件 ID、实际 ROI、alpha/mask、材质、色彩/光照来源。
- 笔画级：contour/follow_surface/hatching/fur_growth/fold/highlight/accent，包含 path guide、taper、pressure profile、local direction、preset capability requirement。
- 全部颜色与笔刷设定先验证属于该 Krita 构建可执行的白名单；“单笔沿线色彩混合”仅使用真实预设支持的 native brush engine，而不是假设存在任意 per-sample color API。
- 修改级：revision intent 只定位已批准对象/ROI，在安全几何和受保护图层基础上生成**新版本**。

### 3.4 最小契约示例（规范草案）

    {
      "schema": "krita-agent-composition/1-proposal",
      "canvas": {"width": 1600, "height": 900},
      "subjects": [
        {
          "id": "cat",
          "kind": "animal",
          "bbox_normalized": [0.28, 0.18, 0.43, 0.65],
          "parts": ["head", "body", "front_legs", "tail"],
          "required_relations": ["head_above_body"],
          "surface_hints": ["fur_growth_follows_body_form"]
        }
      ],
      "composition_notes": "猫坐在窗边，窗口逆光"
    }

这只是目标设计草案，**目前不存在上述 schema/API 实现**。实现时须确立版本号、严格字段白名单、最大数量/深度/字符串长度、合法 enum 和类型边界。不能让纯模型 JSON 或置信度数字绕过下游检查。旧 v4 继续保留只读/编译兼容入口。

## 4. Geometry Solver：把模糊语义变成可执行的合法几何

R14–R15 分阶段引入：

1. 画布坐标转换：归一化 → 整数/浮点 canvas px，界限与裁剪策略明确，绝不默默将错误大面积拉伸进画布。
2. 多边形及曲线：闭合、自交检查、孔洞与多连通区域；使用可验证的图形几何算法，离散误差受控。
3. 主体/部件/锚点：关键结构与约束一致，体态/透视未定义时不假装保证解剖准确。
4. 遮挡与层序：建立有向遮挡图，拒绝不可解释的环，明确 z-order 和保护图层。
5. 安全区域扩展：用于抗锯齿和真实笔尖足迹的外扩/内缩 ROI，既检查 stroke **中心线** 又检查最终可见像素，不能只做中心线裁剪就宣称永不出界。
6. 结构化错误：每个问题记录对象 ID、字段、非法值、允许范围、建议修正方式；有限重新规划。
7. 测试：跨尺寸、边界、空面积、自交、复杂遮挡、旋转和缩放的确定性 fixtures/fuzz、幂等性、编译预算。

模型若只给 bbox 而没有可靠轮廓，solver 只能提出结构近似或请求用户/视觉模型完善，不能凭 bbox 假称有真实物体形状。

## 5. 双执行引擎：区域操作优先，笔触精细塑形

### 5.1 Region/Fill Engine（R15）

**目标：先有完整形体，再谈自然材料。**

输入是闭合 contour、已审核的可绘区域、目标色阶/阴影及遮挡图层，输出是实际 Krita 中仍可编辑的操作：

- 首选已被当前构建验证的本机选区、蒙版、区域填充、矢量形状/图层等能力。
- 如某操作无法经现有 Bridge 安全调用，先做 Krita SDK/插件能力清单和受控最小实现；不得承诺所有版本同样支持。
- 多区域/孔洞/羽化与叠色需要明确边缘行为；保存前后真实图层/透明像素证据。
- 区域铺色与纹理笔触放在**不同阶段/图层**，允许必要的几何铺色，不以多条平行粗笔刷刷过作为默认填充手段。
- 避免外部画好的完整 PNG 再粘贴成结果。现有 PNG/selection import 可以作为授权输入和测试参考，但不可作为“原生绘制完成”的替身。

### 5.2 Natural Stroke Engine（R16）

输入是**曲面/轮廓/材料意图 + 局部方向场 + 已验证的预设**，而不是固定短线网格：

- 轨迹：局部曲率驱动自适应采样，稳定 Catmull-Rom/Bezier 平滑，保留端点，坐标允许但不能过度越界。
- 动力学：taper 的起笔、运笔和收笔；动态压力随 arc length 和意图变化，避免纯随机正弦造成规律性振荡。
- 尺寸策略：在轮廓/细节上细笔优先；但厚涂、底色刷可以是大笔，前提是有视觉目的且不破坏填充正确性。
- 显示效果：实际 brush preset 是否压力影响 size/opacity/flow 必须真机测量，不据 brush.profile metadata 猜测。
- 连续性：在支持的 Native API 中优先 continuous stroke。Stable 等只能 segmented fallback 的情况应明确降级或提供经过 RGBA/接缝证明的局部安全修复，不允许悄悄重叠造成颜色加深。
- 材质方向：发丝沿发束、毛皮沿生长、水纹沿水面、褶皱沿张力、金属沿面和反射；不只使用 subject bbox 的 radial/tangential。
- 颜色：不同笔可选相邻冷暖/明暗色；**单笔内部任意 RGB 变化不是现有可用 native API**。若要单笔混色，需真实 Krita 预设和输出证据。

### 5.3 Color & Material（R17）

维护受光环境、局部形体、环境色、暗部和反光的显式记录。选色应满足明度和材质目的，避免每笔随机色相偏移。颜色空间和 ICC 处理以真实 Krita 文档为准，按构建记录差异。材质 A/B 必须锁定主体、seed、模型参数、画布和正常项目路径，仅改变单一变量；真图/ROI 盲评与像素测量独立。

## 6. ModelProvider、Perception 和训练边界

### 6.1 为什么要用 API Key

API 用于高级语义理解、视觉观察、构图/阶段取舍、技法检索和失败画面定位，**不用于逐笔实时调用**。每个阶段限制模型请求数、图像数、token 和费用；失败可回退到手工候选/离线能力。API Key 存本地环境，不写入 GitHub/日志，所有调用的 endpoint、模型、用户授权、图像 SHA/统计与实际状态均可追踪但不记录敏感正文。

### 6.2 不应让模型承担的工作

- 原始像素/坐标的精密数值计算、复杂多边形闭合、安全裁剪、路径白名单。
- Krita API 或文件系统直接操作、未审核插件代码生成。
- “通过一次图片上传自动训练并记住技巧”；API 调用不会自动更改模型权重。
- 作品完整性/独立人类验收的替身。
- 未知 Krita side effect 的自动重放。

### 6.3 线稿/参考理解与资料库

一律先检查本地可用性和权利：按图片存储内容哈希、来源、授权类型和允许操作。Perception 可用传统图像算法提取边缘/骨架/方向和候选 ROI，可选视觉模型提出“猫头部在右侧”等**假设**。两个通道都要保留置信度和缺失信息，不假装从平面线稿恢复时间/笔压。

知识库使用有权限的本地索引和技法版本，检索到的线稿/风格可作为结构建议与画风指导，但**不能**被直接作为完成的原创图层填充替代。对作者/用途/上传/训练许可进行分开检查。

## 7. Orchestration、审批、可重复执行与未知状态

沿用现有 Workflow/Scheduler 和 Bridge，不重写其认证/安全根基：

1. `created` → `brief_validated` → `structure_proposed` → `structure_approved` → `plan_compiled` → `plan_approved`。
2. 每个 stage 单独 `stage_ready` → 显式批准 → `stage_submitted` → Krita 执行 → 原生 preview/checkpoint → `stage_verified`。
3. 若执行、导出、重开或修订回复丢失：`unknown_needs_review`，必须读回实际状态与原文件，绝不自动再发一次副作用命令。
4. `export_integrity` 和 `reopen_stability` 两门都需严格 RGBA/ICC 一致（真实测量，不随意容忍 1 级漂移）。
5. `review_requested` → `revision_proposed` → 显式批准/拒绝 → 新图层/新版本 → 再次实图评审 → 独立人工验收。
6. 每个版本保留计划 hash、模型/基准版本、Krita build、执行账本、各阶段真实 PNG、KRA 和哈希、失败/修复关联、审查记录。

以上状态名称为设计候选，不能直接当现有程序状态值使用。开发中应定义迁移映射和状态图测试，不改变旧 ledger 的自动恢复条件。

## 8. 渐进式代码目录与适配边界

**目标树，不要求一次性重命名所有模块。**

    src/krita_agent/
      api/                 CLI, typed DTOs, user-facing permissions
      planning/            ArtBrief, CompositionGraph, PaintPlan, validators
      perception/          image/lineart analysis and semantic hypotheses
      geometry/            contours, masks, occlusion, bounded solver
      painting/            region, stroke, color, material engines
      providers/           opt-in model adapters, calls, cost and consent
      knowledge/           indexed references and technique profiles
      orchestration/       state machine, checkpoints and revisions
      evidence/            metrics, hash bindings, native image comparisons
      compatibility/       old v2/v3/v4 adapters and native build capabilities
    plugin/krita_agent_bridge/
      ...existing allowlisted native Bridge...
    benchmarks/
      structural/ brushwork/ material/ artwork/
    docs/
      ...protocols and reports...
    tests/
      unit/ integration/ native/

实际迁移映射：

| 现有实现 | 目标职责 | 迁移策略 |
| --- | --- | --- |
| scene_v2/v3/v4.py、structure_v9.py | schema + planning + geometry | 初期保持旧导入路径，用显式 adapter 分阶段拆分 |
| generalist_director.py、model_provider.py | AI Director + provider | 先加新简洁 schema/有限修正，保留旧 v4 候选入口 |
| intent_strokes_v4.py、material_rendering.py | painting / stroke and region | 引入区域执行新路径；旧 brush intent 作为回退和独立对比 |
| brush_dynamics.py、stroke_engine.py、brush_profiles.py | natural stroke + capability | 原生动态验证、非破坏性增强，跨版本测试 |
| creative_workflow.py、scheduler.py | orchestration | 保留日志/安全/审批，不大规模改动原生任务状态 |
| reference_*_v10.py、technique_library_v10.py | perception + knowledge | 在既有授权/来源/hash 机制外扩展本地索引 |
| visual_critic_v11.py、artifact_integrity.py | evaluation/evidence | 真像素、多阶段、可审查的有界修订，保留严格重开门禁 |
| plugin/krita_agent_bridge/ | native executor | **仅为真实缺失的 Krita 操作添加白名单原生命令** |

每个拆分 PR 都需要“旧 import 和 CLI 不破坏”回归，避免把架构美观优先于项目可用性。禁止一次性删除旧模块后只测试新结构。

## 9. 安全、隐私与数据治理

- Krita Bridge 仍只绑定本地 loopback，token、request ID、命令白名单和 GUI 主线程调用约束不可取消。
- 不开用户未授权的本地工作区，不修改其他 Krita 进程、用户个人 KRA、个人数据或字体/笔刷资源。
- 永不把用户线稿、KRA、付费模型密钥、私有图片、训练数据、绝对私有路径写入 GitHub/公开 CI artifact。图像数据放已忽略的本地根目录，提交的只有 schemas、合成小样、脱敏报告。
- 下载网页素材：遵守站点授权、访问控制和许可；合法原图优先；不破解认证、反爬或付费壁垒；日志保留作者/来源/权利声明。
- 模型外发需要用户确认、每张参考的 external_upload_permitted、provider/cost 清楚列出；上传权限和训练许可不同。
- 修改或修复：在新版本完成，历史失败保留；绘画像素、文件、独立人工评价都不可伪造。

## 10. 端到端场景示例（目标，不是已实现）

“画一只窗边毛发细腻的猫”：

1. ArtBrief 明确猫/窗、风格、可选授权线稿、1600×900、预算。
2. Perception/知识库寻找合法猫坐姿和细毛笔触技术，不直接复制图像。
3. LLM 简洁提出：猫坐姿、头/身/耳/腿/尾、窗台层级、侧逆光。Geometry Solver 提出合法轮廓与 ROI。
4. PaintPlan 先草图结构 → 区域底色 → 亮暗块 → 沿形体毛发生长绘制短/长连续细笔 → 局部边缘/高光。
5. Native Bridge 分阶段创建可编辑层和实际 KRA，真实预览通过用户批准，严格 reopen 证据。
6. 视觉反馈观察真实 PNG：若“尾部与身体脱节”，只给新局部修订意图，用户审查后执行。
7. 独立评审检查对象识别、结构、色光、笔触、完整度；所有失败原件保留。

若任何层失败，返回有依据的对应 gate 错误，不能转而输出一张外部生成的 PNG 冒充完成。

## 11. Architecture Decision Records（后续必须记录）

- ADR-001：Python 模块化单体 + 受控 Native Bridge，不先引入微服务。
- ADR-002：模型语义 / solver 几何 / native executor 分层；原生动作可由白名单编译产生。
- ADR-003：双引擎（Region + Stroke），不让短线承担所有填色。
- ADR-004：真实预设中 in-stroke sensor 变化与跨笔 palette 变化区分；不虚构 per-point color。
- ADR-005：检索先于训练；训练触发条件需要独立证据和用户授权。
- ADR-006：T1/T2/T3 + 独立人类画质验收；计划分数永不冒充艺术接受。

ADR 应随真实 R13–R20 PR 演进而单独成文，包含 alternatives、decisions、tradeoffs、rollback。修改目标架构必须同步修改路线图、验收和迁移计划。
