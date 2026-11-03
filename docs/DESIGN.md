# Krita Agent — 自动绘图系统规划与技术方案

> 文档性质：项目规划 / 技术设计草案（**不是已实现功能清单**）  
> 更新日期：2026-11-03  
> 目标平台：Windows 11 x64；Krita 稳定版 + Krita Next 测试版  
> 
## 1. 项目定位

**Krita Agent** 是一个计划开发的 Windows 原生、可编程绘图控制系统，使外部 Python 命令行程序及 AI Agent 能够通过 Krita 内部插件调用绘图能力，以自动完成从建画布、规划图层、模拟压感笔触、绘画到保存和导出的工作流。

核心目标：

1. **真正使用 Krita 原生画笔引擎**，而不只是生成 PNG 后导入 Krita。
2. **以可复现的绘图命令描述画面**：笔迹轨迹、压力、笔刷、颜色、图层、输出参数。
3. **保留可编辑性**：优先生成包含独立图层的 `.kra` 工程，同时导出常见图像格式。
4. **兼容不同 Krita 版本**：稳定版使用可用接口，Next 版优先试验新增连续笔画接口。
5. **代码与作品分离**：项目脚本受 Git 管理，批量输出默认不提交 GitHub。

**范围说明**：这是“AI / 脚本驱动的绘画自动化框架”，不是安装后就能自动理解任意文字并画出专业插画的成品 AI 绘画模型。自然语言理解、构图算法与视觉迭代需要在基本绘图能力通过测试后逐步集成。

## 2. 总体决策

### 已确定的架构选择

- **主控环境：Windows 原生 Python**，不依赖 WSL2 / Debian。
- **执行环境：Windows Krita**，借助其进程内的 Python 插件访问 Krita API。
- **通信：本机 localhost / loopback 的受控消息通道**，备选为本地任务队列。
- **版本策略：稳定版负责日常使用与兼容性测试；Next 负责新接口研发**。
- **WSL2：不是必需组件**；仅在以后确有 Linux 专属依赖时再扩展。
- **项目仓库与 Krita 安装目录并列**，不能把控制器脚本直接塞进软件安装文件内部。

## 3. 系统架构与职责

```text
用户 / ChatGPT / Codex / 外部自动化程序
                 │
                 ▼
       Windows Python CLI / SDK
       ├─ 命令解析、参数校验
       ├─ 绘画任务与队列管理
       ├─ 构图、曲线、压感轨迹生成
       ├─ 版本 / 能力检测与路由
       ├─ 上游功能追踪（独立 Git / API 分析模块）
       └─ 预览、日志、验收、暂停/恢复/重试
                 │
        本地受控通信协议
                 │
                 ▼
     Krita Agent Bridge（自研插件）
       ├─ 注册 Krita Python Extension
       ├─ 接收、验证与调度命令
       ├─ 在正确的 Qt / GUI 上下文调用 API
       ├─ 文档、图层、笔刷、笔迹操作
       └─ 返回任务状态与错误信息
                 │
                 ▼
       Krita 原生绘图引擎
       ├─ 画布 / 图层 / 笔刷预设
       ├─ paintLine()（兼容路径）
       ├─ paintPolylineStroke()（Next 路径）
       ├─ 其他可用的绘制与像素接口
       └─ 保存 .kra / 导出 PNG 等
```

**接口边界**：Krita 的 `krita` Python 模块属于 Krita 应用内的脚本环境。普通 Windows Python 不能简单地 `import krita` 就控制另一个 Krita 进程，因此需要自研 Bridge 插件。外部 CLI 与 Bridge 以约定的消息协议交互；不要通过任意代码执行来实现控制。

## 4. 预计功能清单与优先级

> 状态均为“规划 / 待验证”，并非宣称当前已有实现。P0 为首轮可用性必需，P1 为完整创作流程，P2 为增强功能。

| 模块 | 预计能力 | 优先级 | 关键技术 / 注意事项 |
| --- | --- | --- | --- |
| 环境探测 | 检测 Krita 进程、版本、插件状态及可用 API | P0 | Krita Python API、运行时 `hasattr` 检查 |
| CLI 控制 | 启动/连接指定 Krita 实例、提交任务、查询进度与结果、取消任务 | P0 | Python、`argparse` / Typer（待定）、JSON；启动与连接分开处理 |
| 通信桥接 | CLI 与 Krita 双向传输指令、错误和任务结果 | P0 | 自研 Krita Python Extension + 本地通信 |
| 画布管理 | 新建、打开、激活画布；设置画布尺寸与基本参数；按需导入图像为参考或图层 | P0–P1 | Krita `Document` / `Krita` API；导入方式需实测 |
| 图层管理 | 创建、命名、排序、切换、显隐图层 | P0 | `Node` / `Document` API |
| 基础绘画 | 点、线、折线、曲线、椭圆、多边形；按需写入像素数据 | P0–P1 | `Node.paintLine`、`paintPath`、`paintEllipse`、`paintPolygon`、`setPixelData`；按版本逐项实测 |
| 压感笔触 | 一笔内粗细变化、模拟起收笔；压力联动大小/不透明度（视笔刷设置） | P0 | 稳定版分段 / Next 连续笔触；明确区分压力数据与实际画笔响应 |
| 笔刷使用 | 选择 Krita 预设、颜色、笔刷尺寸、不透明度；复用铅笔、墨水、水彩等效果 | P0–P1 | Krita `View` / `Action` / 绘图环境，笔刷切换与参数需逐项验证 |
| 工程保存 | 保存 `.kra`，导出 PNG/JPEG，保留图层 | P0 | `Document` 保存与导出 API |
| 任务协议 | 以 JSON 定义画布、图层、轨迹和输出 | P0 | Schema 校验、幂等任务 ID |
| 贝塞尔轨迹 | 曲线离散采样、平滑、等弧长重采样 | P1 | Python 数值算法 |
| 压感模拟 | 自定义压力、随机微扰、速度、倾斜度 | P1 | 插值算法 + `StrokePoint`（版本支持时） |
| 绘画流程 | 草图 → 线稿 → 底色 → 阴影 → 高光 | P1 | 绘画规划器、图层策略 |
| 批量任务 | 多图任务、预设模板、失败续跑 | P1 | 队列、状态机、任务日志 |
| 交互与执行控制 | 绘图进度、暂停/继续（在安全检查点）、停止、撤销及重做 | P1 | 任务状态机、快照、Krita undo/redo；长笔迹不保证可中途打断 |
| 实时可视化 | 在 Krita 画布观察绘制过程，刷新预览并反馈状态 | P1 | GUI 事件调度、进度事件、缩略图或屏幕预览 |
| 上游功能追踪 | 自动发现上游新 API、行为变更、绘图引擎/笔刷更新与兼容风险；生成结构化报告 | P1–P2 | Git 差异分析、API 提取、版本矩阵、候选回归测试（详见第 12 节） |
| 预览与反馈 | 导出缩略图、分析结果并生成下一轮调整 | P1–P2 | Krita 导出 + 图像分析 / 可选视觉模型 |
| 编辑修订 | 修改指定层或局部区域、撤销/重试 | P1–P2 | API 能力验证 + 文档快照 |
| 自然语言入口 | 将描述转换为结构化绘图指令 | P2 | LLM Agent + 安全可控的指令规划 |
| 风格化 | 画笔纹理、漫画勾线、水彩、油画等方案 | P2 | 笔刷预设、专门的绘画算法；不是保证效果 |
| GUI 辅助面板 | Krita 侧边栏显示连接、任务、暂停/继续、进度、日志 | P2 | 自研 `DockWidget` / Qt |

**范围限制**：笔刷参数、滤镜、选区、局部编辑等功能在不同版本中暴露程度不一。若 Krita Python API 不直接提供某项操作，应先研究官方 Action、Qt 接口或其他受控方案；不能把“理论可自动化”误写为“现成 API 支持”。

## 5. 压感和一笔内粗细变化：核心技术方案

目标是实现**一笔下去起笔细、中间粗、收笔细**，并可进一步模拟压力驱动的不透明度/颜色深浅、笔尖角度、速度和纹理变化。这里的“压感”是向笔刷传入压力值，是否真正影响线宽、透明度、纹理等取决于所选笔刷的动态参数映射；应为压力→大小与压力→不透明度分别配置和验收。

建议使用统一的“笔迹采样点”数据模型，每个点可携带：

- 坐标：`x, y`（画布像素坐标）。
- 压力：`pressure`（建议归一化为 0～1）。
- 时间：`time_ms`（相对起笔时间）。
- 速度：`speed`（若所用 API 支持）。
- 倾斜：`x_tilt, y_tilt`（若所用 API 支持）。
- 可选：旋转、切向压力等高级输入传感器值。

例如一条笔画的压力序列为：

| 位置 | 压力 | 预期视觉效果 |
| --- | ---: | --- |
| 起笔 | 0.10 | 细 |
| 前段 | 0.35 | 逐渐加粗 |
| 中段 | 0.90 | 最粗 |
| 后段 | 0.50 | 逐渐变细 |
| 收笔 | 0.05 | 尖细收尾 |

### 5.1 Krita 稳定版兼容路径

使用 `Node.paintLine(pointOne, pointTwo, pressureOne, pressureTwo, ...)`。为模拟复杂曲线，可对贝塞尔路径重采样，按相邻采样点分段绘制并在段首/尾设置压力。

**注意**：多次调用 `paintLine` 不等同于“一条连续自由手绘笔迹”，笔刷间距、随机纹理和撤销行为可能出现接缝/不连续，需要通过实测验收。`paintPath` 也不等于可逐点指定压感。

### 5.2 Krita Next 原生连续笔触路径

Krita 2026-10 开发月报确认，Next 开发分支引入：

- `Node.paintPolylineStroke(...)`：将多组 `StrokePoint` 输入组成一条连续笔触。
- `StrokePoint`：提供压力、倾斜等模拟传感器参数。
- `View.brushPosition`：读取画笔位置的新增接口。

该能力出现在当时的 **Krita Next 5.4.0 / 6.1.0 pre-alpha 开发线**；**不能假设稳定版 5.3.4.1 包含它，也不能仅凭目录名保证本机 Next 构建已包含它**。需通过实际运行检查类与方法是否存在，再做绘画验收。

Next 的连续笔迹方案优先解决多段连接时的笔刷间距、纹理与撤销连续性。最终笔触宽度是否随压力变化，仍取决于选择的笔刷预设是否开启“压力影响大小”等动态参数。

### 5.3 绘制算法建议

1. 使用贝塞尔曲线或手绘路径确定几何轨迹。
2. 按距离/曲率进行重采样，避免过稀或忽密忽疏。
3. 生成压力曲线（如平滑起落、多峰压力、局部波动）。
4. 如支持，补充时间、速度、倾斜等属性。
5. 优先提交 Next 原生连续笔画；否则在稳定版中降级为分段绘制。
6. 对比两种输出的线宽、接缝、纹理、撤销和性能。
7. 保存可复现的参数和验收图。

## 6. 技术栈、官方 API 与拟自研组件

| 类型 | 技术 / 工具 | 用途 | 必需性 |
| --- | --- | --- | --- |
| GUI 绘图软件 | Krita 5.3.x 稳定版 | 日常绘图、兼容性验收 | 必需 |
| GUI 绘图软件 | Krita Next 5.4/6.1 开发线 | 新压感连续笔触 API 研发 | 推荐 |
| 控制端 | Windows Python 3 | CLI、绘图规划、任务调度 | 必需 |
| 应用内扩展 | Krita 官方 Python 插件机制（`Extension`） | 进入 Krita 进程并调用 API | 必需 |
| API | Krita Python / LibKis | 文档、图层、笔刷、绘制与导出 | 必需 |
| GUI / 事件循环 | Krita 自带 Qt/PyQt（以实际构建为准） | 插件事件调度、可选侧边栏 | 必需/可选 |
| 通信 | localhost 受限 IPC | CLI ↔ Bridge | 必需 |
| 序列化 | JSON + Schema | 绘图任务、参数及结果 | 必需 |
| 开发工具 | Git、Python venv、pytest | 版本管理、依赖隔离、测试 | 推荐 |
| 研究工具 | 官方 KDE Invent 源码仓库 | 追踪 API 实现与变更 | 推荐 |
| AI 入口 | ChatGPT / Codex / 自定义 LLM 接口 | 任务理解、生成绘图计划 | 可选，后期 |
| 视觉反馈 | 图像分析 / 可选视觉模型 | 构图评估与迭代修订 | 可选，后期 |

### 自研插件

**Krita Agent Bridge**：不是 Krita 官方现成插件，需在 `krita-agent/plugin/` 中开发，按照官方 `pykrita` 插件机制部署。至少提供：

- 插件启动、关闭、状态探测；
- 受控指令白名单、参数校验、异常隔离；
- 在 Krita 所要求的 GUI / Qt 上下文执行绘图操作；
- 版本特性检测与兼容分支；
- 绘画任务状态、错误、日志与取消；
- 可选的 Krita 停靠面板。

### 有帮助的官方工具，但不是强制依赖

- **Scripter**：Krita 内置的 Python 脚本实验工具，适合快速核验 API。
- **Krita Python Plugin Manager**：启用自研 Bridge 插件。
- **Krita 的笔刷预设系统**：保存绘画风格所需的笔刷配置；注意线宽、透明度与压力响应可能使用不同的笔刷动态选项。

不需要为了本项目另外安装一整套 Linux Krita；初期也不需要引入额外的第三方 Krita 插件。

## 7. 计划的任务协议及命令行使用方式

下面是**拟设计的接口示例**，**不是 Krita 原生命令，也不是当前已实现的工具**。

```powershell
# 未来由我们自己的 CLI 实现
krita-agent doctor
krita-agent connect --target next
krita-agent new --width 2048 --height 2048
krita-agent layer add "Line Art"
krita-agent brush select "configured-ink-brush" # 预设的名称/标识待实际确定
krita-agent brush size 24
krita-agent brush opacity 0.75              # 笔刷不透明度，API 能力待验证
krita-agent draw ".\examples\pressure-stroke.json"
krita-agent job status job_001
krita-agent job pause job_001              # 在安全检查点暂停；规划接口
krita-agent job resume job_001
krita-agent undo                            # 撤销支持以运行时测试为准
krita-agent preview ".\output\preview.png"
krita-agent save ".\output\artwork.kra"
krita-agent export ".\output\artwork.png"
krita-agent upstream check                 # 检查上游 API / 绘图引擎变化
```

拟设计的 JSON 格式：

```json
{
  "schema_version": "0.1-draft",
  "document": {"width": 2048, "height": 2048},
  "layer": "Line Art",
  "brush": {"preset": "configured-ink-brush", "size": 24},
  "strokes": [
    {
      "points": [
        {"x": 100, "y": 180, "pressure": 0.10, "time_ms": 0},
        {"x": 220, "y": 140, "pressure": 0.35, "time_ms": 60},
        {"x": 360, "y": 160, "pressure": 0.90, "time_ms": 120},
        {"x": 500, "y": 230, "pressure": 0.50, "time_ms": 180},
        {"x": 650, "y": 250, "pressure": 0.05, "time_ms": 250}
      ]
    }
  ],
  "output": {
    "kra": "output/artwork.kra",
    "preview": "output/artwork.png"
  }
}
```

这里的 `brush.preset` 仅表示目标笔刷标识；具体怎么切换 Krita 预设和笔刷大小要结合当前版本 API 实测设计。协议需允许未来增加颜色、倾斜、速度、压力→大小/不透明度映射及撤销/重试信息。**压力轨迹与笔刷压感响应需分别验证**。命令中的 `pause` / `resume` 应按笔画或任务步骤实现检查点，不保证能中断 Krita 已经开始执行的一笔。

## 8. 端到端工作流

1. **环境检查与连接**：探测或启动指定的 Windows Krita 实例，识别实际版本、Bridge、画布状态及可调用 API。
2. **任务输入与规划**：接收自然语言或 JSON，生成画布、图层、笔刷、笔迹及压力变化计划。
3. **参数校验**：检查尺寸、压力、文件权限、路径、任务 ID；有参考图片时按需导入参考层/图像层。
4. **本地通信**：Windows CLI 向 Krita Agent Bridge 提交带 ID 的绘制任务。
5. **创建画布与图层**：例如 Background → Sketch → Line Art → Base Color → Shadow → Highlight，保持可编辑。
6. **准备绘制状态**：切换图层与笔刷预设，配置颜色、尺寸、不透明度以及压力映射（以当前 API 支持为准）。
7. **执行笔迹**：Next 优先采用 `paintPolylineStroke`；稳定版按能力降级；保留进度、暂停/继续检查点和撤销策略。
8. **实时反馈**：在 Krita 画布观察绘制，读取每步状态、错误及阶段性预览。
9. **验收与修订**：检查压力带来的粗细/深浅变化、笔触接缝、纹理、图层；按需撤销、重试或局部重绘。
10. **保存与输出**：保留分层 `.kra`、导出 PNG/JPEG，保存任务参数、预览与简洁日志。
11. **清理与复现**：清理临时缓存，不误删作品；保留复现任务所需配置。
12. **兼容性维护（独立流程）**：上游追踪模块检测 Krita 新功能或行为变化，生成兼容报告/候选测试，确认后再更新控制器。

### 视觉闭环（中后期）

```text
用户描述 → 结构化计划 → Krita 原生绘制 → 预览
   ▲                                           │
   └──────── 问题识别 / 局部修正 / 再绘制 ──────┘
```

视觉模型只是可插拔的一环；基础绘图链路应能在没有云端模型的情况下独立运行和测试。

## 9. 未来 krita-agent Git 仓库的建议结构

**以下为计划结构，部分目录和所有功能尚未实现。**

```text
krita-agent/
├── src/krita_agent/
│   ├── cli/                 # CLI 命令
│   ├── bridge/              # IPC 客户端 / 协议
│   ├── drawing/             # 几何采样、压感和笔迹规划
│   ├── jobs/                # 队列、执行状态、重试
│   ├── compatibility/       # 版本与能力适配
│   └── upstream/            # 官方仓库变更分析、API 追踪
├── plugin/
│   └── krita_agent_bridge/  # Krita 内部 Python 插件源码和清单
├── presets/                 # 绘画参数 / 笔刷配置
├── resources/               # 必要素材
├── examples/                # 体积较小的演示指令和验收样例
├── tests/                   # 单元、集成、真实 Krita 验收
├── scripts/                 # Windows 安装与部署脚本
├── docs/                    # API / 设计 / 兼容性文档
│   └── upstream/            # 追踪报告、API 变化、版本矩阵
├── .cache/                   # 上游快照 / 中间缓存，不纳入 Git
├── output/                  # 本地生成文件：默认不加入 Git
├── pyproject.toml
├── .gitignore
└── README.md                # 未来仓库自己的 README；与本文件不同
```

### Git 与 output 管理策略

- `src/`、`plugin/`、`scripts/`、`tests/`、`presets/`、`docs/` 正常提交 Git。
- `examples/` 保存少量经过筛选的 JSON 样例与小型验收图；必要时可以跟踪。
- `output/` 保留在仓库工作目录，但大批量的 `.kra` / PNG / JPEG / 中间产物不提交。
- 大型作品可考虑独立存放，确有版本控制需求时再使用 Git LFS。
- 不把 `Krita (x64)`、`Krita_Next` 和 `krita-upstream` 当作 `krita-agent` 仓库内容提交。

建议未来的 `.gitignore` 条目：

```gitignore
/output/*
!/output/.gitkeep
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
*.log
*.tmp
/.cache/
```

## 10. 版本共存、插件部署与安全边界

### 双 Krita 版本

- 稳定版与 Next 版的程序文件可以放在不同目录。
- 它们**可能共用用户配置、笔刷资源和 Python 插件目录**；这不等于完全隔离。
- 开发前先备份个人配置与资源；避免 Next 测试损害稳定版工作环境。
- 插件源码放在自有仓库，通过安装脚本复制/链接到 Krita 的用户资源目录中的 `pykrita`。
- 当配置目录共享时，部署脚本必须可检测两套 Krita 的版本和插件兼容性；不能盲目覆盖。
- 不修改 Krita 程序安装目录内的官方文件。

### 本地控制器的基本安全要求

1. 仅监听 `127.0.0.1` 或受操作系统权限保护的本地 IPC，不对局域网开放。
2. 只允许事先定义的任务指令；禁用外部传入的任意 Python / Shell 代码执行。
3. 文件读写尽量限制在授权的项目与输出目录；重要文档覆盖前备份或显式允许。
4. 为任务添加 ID、超时、错误码；避免重复提交造成重复绘制。
5. Qt GUI / Krita 画布操作在合适线程运行；网络/队列工作线程不能直接随意修改 GUI 对象。
6. 开发版不作为唯一的正式绘画环境，重要 `.kra` 工程保留备份。

## 11. 开发与验收路线

| 阶段 | 主要交付 | 验收标准 |
| --- | --- | --- |
| P0-A 环境探测 | `doctor` 与 API 清单 | 稳定版 / Next 均能报告真实版本、`StrokePoint` 和 `paintPolylineStroke` 可用性 |
| P0-B 最小桥接 | CLI ↔ Krita 插件 | 发送简单命令、获取成功/失败、无 GUI 冻结 |
| P0-C 基础绘制 | 建画布、图层、直线及曲线 | 可自动保存一张含多图层的 `.kra` |
| P0-D 压感测试 | 细→粗→细的一条或多条笔迹 | Next 连续笔画、稳定版降级效果均有验收图与比较 |
| P0-E 交付收尾 | 安装脚本、日志、单元测试、README | 在干净目录可复现安装和基础任务 |
| P1 绘画系统 | 草图/线稿/底色/阴影的结构化绘制；笔刷配置、参考图、任务控制 | 按 JSON 重复绘制且输出可编辑；暂停/恢复及撤销在检查点可靠工作 |
| P1-U 上游追踪初版 | Git 增量检测、API 变更摘要、版本能力矩阵 | 能识别可追溯变更并区分源码出现、实际可运行的差别 |
| P2 智能迭代 | 自然语言、视觉反馈、自动修订 | 可以对单层/局部修改并回归验证 |
| P2-U 上游追踪增强 | 候选测试生成、兼容风险预警、可选定期报告 | 测试只在隔离环境运行；用户确认后才启用定期检测或代码改动 |

### 首轮真实绘画验收用例

- 自动创建 2048×2048 画布，至少三个独立图层。
- 选定一种能响应压力变化的 Krita 原生笔刷。
- 同时画出等压线、渐增压线、细→粗→细曲线；分别验证压力作用于大小和不透明度的笔刷预设。
- 分别测试稳定版与 Next，保存对比结果。
- 检查线宽、接缝、抗锯齿、纹理、性能和撤销行为。
- 输出 `.kra` 和 `.png`；关闭后重新打开 `.kra`，确保图层没有丢失。
- 重复运行验证不会产生不可控的残留文件或覆盖用户作品。

## 12. 上游功能追踪模块（Upstream Feature Tracker，计划开发）

**官方主仓库**：[https://invent.kde.org/graphics/krita]  
**GitHub 镜像**：[https://github.com/KDE/krita]

推荐将上游源码克隆为单独的 `D:\computer\Krita\krita-upstream` 目录，**仅作参考**，不嵌入自有 `krita-agent` 的 Git 历史。初期采用浅克隆以减小下载量：

```powershell
cd "D:\computer\Krita"
git clone --depth 1 --single-branch https://invent.kde.org/graphics/krita.git krita-upstream
```

随后按需：

```powershell
cd "D:\computer\Krita\krita-upstream"
git pull --ff-only
git grep -n "paintPolylineStroke"
git grep -n "StrokePoint"
```

**用途**：阅读 Python API 绑定、函数签名、实现细节、提交变更和测试；据此生成“可用 / 新增 / 行为变更 / 待验证”报告。**本地源码更新不等于已安装软件自动升级**。未来若需要跨版本比较，可抓取对应 release/tag 或维护另一参考工作树，避免反复覆盖开发工作区。

### 12.1 定位与追踪范围

这是 **krita-agent 的独立核心模块**，不只是本地克隆一份 Krita 源码。目标是帮助控制器持续发现 Krita 可自动化能力的变化，评估现有脚本能否使用，并为后续功能开发准备证据与回归测试。

重点追踪：

1. **Python / LibKis API**：新类、方法、参数、返回值、枚举、弃用、行为变化；尤其是 `Node`、`Document`、`View`、`Extension`、`StrokePoint`。
2. **笔刷引擎与绘制能力**：压感、连续笔触、笔尖旋转、倾斜、纹理、笔刷预设以及受脚本控制的新入口；注意“底层支持”不等于“Python API 已开放”。
3. **图层、导入、保存与导出**：新的图层操作、文件格式、色彩空间与渲染能力。
4. **Python 插件、Qt 和安装兼容性**：稳定版 / Next、Qt5 / Qt6 差异、插件入口及绑定变化。
5. **与自动化相关的修复**：绘图可靠性、崩溃、撤销栈、性能、接口回归。
6. **不影响 agent 的改动**：一般 UI 文案、无关翻译等只记录或过滤，不占据优先开发队列。

### 12.2 数据源和版本基线

- **主数据源**：官方 KDE Invent Git 仓库（上游基准）；GitHub 仅作镜像或访问备选。
- **辅助证据**：Krita 官方发布说明、开发月报、API 文档、仓库测试及相关合并请求说明。
- **版本基线**：分别记录稳定版、Next 本地执行文件的实际版本和构建信息；记录 Git 分支 / tag / 提交 SHA。
- **上游快照**：保存上一次成功检查的提交 SHA，下一次只处理增量；首次运行先生成基线报告。
- **分支比较**：默认分支和相关稳定维护分支分别比较；对未来版本使用其实际分支名称，不假设永远是 `master`。
- **浅克隆限制**：`--depth 1` 便于首次下载，但无法直接做完整历史和跨旧标签比较；需要时补充 fetch 相应分支 / 标签或加深历史。

### 12.3 工作流：更新 → 发现 → 判断 → 验证 → 报告

```text
手动执行追踪 / 用户开启定期计划
             │
             ▼
读取上次检查记录与当前本机 Krita 版本
             │
             ▼
Git fetch 官方 upstream，确认远端分支 / tag / commit
             │
             ▼
比较两个快照的提交与关键源码 / API 文档变更
             │
             ▼
提取接口变更 + 绘图引擎变化 + 插件兼容风险
             │
             ▼
去重与分类、关联对应 Commit / MR / 版本
             │
             ▼
评估可用性：已在本机验证 / 需 Next / 仅源码可见
             │
             ▼
输出机器可读 JSON + 人类可读 Markdown + 候选测试
             │
             ▼
在隔离测试环境中验证（按配置触发）
             │
             ▼
更新能力矩阵与开发待办；开发者审核后再修改 agent
```

**触发机制**：初期提供手动命令；后续可选 Windows 任务计划程序按用户设定的频率检查（例如每周一次）。计划任务必须先由用户明确启用，文档本身不代表已经设置自动监测。只读扫描不能默认静默升级 Krita、修改 agent 或覆盖绘画作品。

**变更发现**：Git diff / log + 相关 API 绑定、头文件、实现、测试、发布说明的针对性扫描；必要时追踪 merge request。优先通过可审计的规则和签名比较找到变化，可选 LLM 负责生成通俗摘要，但不能代替源码证据。

**变更分类**：新增 API、签名变化、弃用/移除、行为修复、性能/质量变化、插件兼容风险、功能不可达、非相关改动。对每条记录标记影响模块（笔刷/图层/保存/CLI/Bridge）、风险等级和建议优先级。

**能力判断**：至少分为 `source_seen`（源码发现）、`documented`（文档确认）、`present_in_build`（运行时可见）、`tested_working`（真实验收通过）、
ot_supported`（目标构建不可用）。**只有最后的真实执行验证，才能把“新功能可用”写进已实现清单。** 例如看到新 `paintPolylineStroke` 提交后，应核对该方法是否存在于当前 Next 构建、参数格式是否匹配，再画出真实连续压感笔迹。

### 12.4 模块拆分和未来命令（设计草案）

| 子模块 | 职责 |
| --- | --- |
| `upstream/fetcher` | 获取远端增量、维护分支/标签和快照 |
| `upstream/diff_analyzer` | 解析提交、源码 / 文档变更、接口定义差异 |
| `upstream/classifier` | 归类、去噪、关联 Krita Agent 受影响组件 |
| `upstream/capability_matrix` | 合并源码证据、发布版本与本机运行时检测 |
| `upstream/test_suggester` | 针对新增 / 修改 API 生成**候选**验收脚本 |
| `upstream/reporter` | 生成差异摘要、兼容性风险和待办报告 |
| `upstream/scheduler` | 可选集成 Windows 任务计划程序，不默认启用 |

下面的命令只是预留的 CLI 设计，不是已经可运行的程序：

```powershell
krita-agent upstream init --repo "D:\computer\Krita\krita-upstream"
krita-agent upstream check                         # 拉取增量并生成变更报告
krita-agent upstream diff --from "OLD_COMMIT_SHA" --to "NEW_COMMIT_SHA"
krita-agent upstream report --format md
krita-agent upstream probe --target next          # 运行时 API / 构建能力核验
krita-agent upstream test --suite suggested       # 经用户启用后执行候选隔离测试
```

### 12.5 报告、状态和数据管理

建议输出以下几类**将来生成的文件**（位置位于独立的 `krita-agent` 仓库，不是当前总目录）：

```text
krita-agent/
├── src/krita_agent/upstream/               # 上游追踪模块源码
├── docs/upstream/
│   ├── latest.md                           # 最新人工可读摘要
│   ├── compatibility-matrix.md             # 本机稳定版 / Next 能力对照
│   └── history/                            # 历史追踪报告（可筛选保留）
├── tests/upstream/                          # 审核后的兼容性 / 回归测试
└── .cache/upstream/                         # 本地快照、提交状态和临时数据（不提交）
```

每一项上游变化至少记录：检查时间、基线与目标 SHA、分支/tag、提交或合并请求链接、涉及文件、变更摘要、调用签名、与 Krita Agent 的关系、目标版本、可用性证据、建议测试、风险及处理状态。报告应将高优先级变化（例如可编程笔刷、压感、图层 API）放在前面。

### 12.6 与开发流程的衔接及验收

1. 报告发现新的绘图或插件 API → 建立候选功能任务 → 编写最小复现测试 → 在相应 Krita 构建内验证。
2. 如果已用 API 发生变更 → 定位 Krita Agent 依赖点 → 检查兼容层 → 运行回归测试。
3. 如果稳定版未支持而 Next 支持 → 在能力矩阵标记“Next 专属”，实现安全降级；不贸然修改稳定版路径。
4. 经测试确认后，才能更新内部 API 清单、文档与控制器功能；**默认只提出建议，不自动提交代码或安装新版本**。

**验收标准**：在可控的 Git 提交区间内，至少能识别一次新增方法、一次签名/行为相关变化（可以用测试夹具模拟），给出可追溯源码链接，正确区分“仅源码可见”和“本机可调用”，并生成不破坏用户绘图文件的候选测试。失败或网络不可达时保持上次成功快照，不伪造更新结果。

**边界**：本模块不直接进行 Krita 自动升级，不在未授权时定时联网，不自动合并上游代码，更不直接执行上游提交中任意脚本；测试在独立文档与临时输出目录进行。

## 13. 参考资料

1. Krita 官方 Python 脚本介绍：<https://docs.krita.org/en/user_manual/python_scripting/introduction_to_python_scripting.html>
2. Krita 官方 Python 插件编写指南：<https://docs.krita.org/en/user_manual/python_scripting/krita_python_plugin_howto.html>
3. Krita 官方 Python 插件安装与管理：<https://docs.krita.org/zh_CN/user_manual/python_scripting/install_custom_python_plugin.html>
4. Krita 2026 年 10 月开发月报（新 `StrokePoint` / `Node.paintPolylineStroke`）：<https://krita.org/en/posts/2026/monthly-report-2610/>
5. Krita 官方源码：<https://invent.kde.org/graphics/krita>
6. Krita GitHub 镜像：<https://github.com/KDE/krita>
7. Krita Node 绘制接口参考：<https://api.kde.org/legacy/krita/html/classNode.html>

---

**设计原则**：Windows 单平台优先；原生笔刷优先；连续压感优先；能力探测优先于版本假设；上游变更优先转化为可追溯的能力矩阵和测试；确保真实可用后再扩展 AI 生成与复杂绘图。

