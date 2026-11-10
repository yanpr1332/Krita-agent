# Krita Agent

**后续通用 AI 画师路线图（已规划，尚未实现）：** 未来目标是自然、有绘画意图的笔触，覆盖人物、动物、静物、建筑、插画和风景等常见题材，并支持参考图临摹、可复用技法学习。Round 7–12 的详细开发包、架构、验收与 API 接入时机请阅读 **[通用画师路线图](docs/ARTIST-ROADMAP-R7-R12.md)**。完整的 API 大模型自动验收计划放在 Round 11；此前可以按需使用已授权的模型辅助规划。

**第六轮笔刷开发（已记录三构建原生测试）：** 支持逐笔粗细、颜色、透明度、预设切换与弧长压感曲线。见 [第六轮 API](docs/ROUND6-API.md)、[验收清单](docs/ROUND6-ACCEPTANCE.md) 和 [本地重新验收报告](docs/ROUND6-REACCEPTANCE.md)。**独立人工完整作品验收与少量重开像素漂移根因修复仍待完成。**

**完整作品验收新规定（R4.5）：** 命令数、笔触数和图层数不能替代完整插画验收。必须实际查看仓库中的[示例图与创作契约](docs/ARTWORK-ACCEPTANCE.md)，将最终 KRA、PNG、阶段预览和审核证据留在本地 `artwork-results/`。本地 Agent 请先阅读 [AGENTS.md](AGENTS.md)。

[English](README.md) | 简体中文

Krita Agent 是 Windows 环境下的 **Krita 原生绘画自动化系统**：外部 Python Controller 通过仅限本机的鉴权 IPC 连接到 Krita 内部 Python 插件，在真实可编辑的 KRA 文档、图层及笔刷上操作。项目明确区分源码实现、离线测试和真实 Krita 构建验收。

## 项目状态（2026-11-08）

| 阶段 | 状态 | 证据 |
| --- | --- | --- |
| 第一轮：原生绘图与基础任务 | **已验收**：Stable 和两种 Next 构建 | [REPORT-004](docs/REPORT-004.md) |
| 第二轮：可编辑工作流、预览、导入及 Dock | **已验收**：34 项离线测试及真实像素/Dock 验收 | [REPORT-006](docs/REPORT-006.md)、[REPORT-007](docs/REPORT-007.md) |
| 第三轮：安全检查点、非破坏性蒙版、局部修订与上游证据登记 | **三个本机构建已验收，57 项离线测试通过** | [REPORT-009](docs/REPORT-009.md)、[第三轮验收清单](docs/ROUND3-ACCEPTANCE.md) |
| 第四轮：多图层修订、长任务、笔刷档案、ScenePlan v2 | **已记录本地验收** | [REPORT-011](docs/REPORT-011.md)、[第四轮验收清单](docs/ROUND4-ACCEPTANCE.md) |
| 第五轮：自主创作 Workflow、语义场景规划、视觉评审和局部修订 | **源码已实现；Python 3.10/3.13 各 129 项离线测试通过；真实作品验收待完成** | [第五轮 API](docs/ROUND5-API.md)、[第五轮验收清单](docs/ROUND5-ACCEPTANCE.md) |
| 第六轮：多样式笔刷与连续压感绘制 | **已记录三构建原生测试；完整作品人工审计待完成** | [本机重新验收报告](docs/ROUND6-REACCEPTANCE.md)、[验收清单](docs/ROUND6-ACCEPTANCE.md) |

第四轮本地验收覆盖 Stable 5.3.4.1、Next Qt5 5.4.0-prealpha 和 Next Qt6 6.1.0-prealpha。功能范围与限制见 [REPORT-011](docs/REPORT-011.md)。

## 工程结构

```text
src/krita_agent/             外部控制器、任务协议、曲线与结构化场景规划、
                             基于目标图像的局部修订、反馈和上游追踪
plugin/krita_agent_bridge/  Krita 内部插件、原生图层、蒙版、检查点、
                             独立可逆像素记录、跨会话复制与可选 Dock
tests/                      第四轮 82 项离线测试通过
scripts/                    默认预览的插件安装器及验收辅助工具
examples/                   JSON 画面与任务示例
docs/                       验收报告、架构与开发文档
```

## 安装与既有功能

安装器默认只预览改动，Krita Stable 与 Next 可能共用插件目录，务必先确认和备份：

```powershell
cd "D:\computer\Krita\Krita-agent"
python -m pip install -e .
python scripts\install_plugin.py
# 确认用户资源和备份后才显式运行：
python scripts\install_plugin.py --apply
```

在 Krita 的 **设置 → 配置 Krita → Python 插件管理器** 中启用 Bridge，重启 Krita，并由 Controller 显式启动指定版本：

```powershell
krita-agent launch --krita "D:\computer\Krita\Krita_Next\bin\krita.exe" --output-dir "D:\drawings\out" --input-dir "D:\drawings\references" --dock
krita-agent connect
krita-agent capabilities
krita-agent workflow --file ".\examples\round2-edit-workflow.json" --wait
```

具体构建的实测结果和限制见 REPORT-009。

## 第三轮新增命令（本机构建已验收）

```powershell
# 保存真实 KRA 检查点，查看并显式恢复到新的 KRA 副本：
krita-agent checkpoint create
krita-agent checkpoint list
krita-agent checkpoint inspect CHECKPOINT_ID
krita-agent checkpoint restore CHECKPOINT_ID --confirm

# 将明确的图层与笔触计划转为可审查 JSON：
krita-agent scene --file ".\examples\round3-scene.json" --output ".\plans\scene.json"

# 对比当前画布与用户提供的目标 PNG，规划受控局部修改：
krita-agent revision plan --before ".\before.png" --target ".\reference\goal.png" --layer-id LAYER_ID --output ".\plans\revision.json"
krita-agent revision apply --plan ".\plans\revision.json" --confirm

# 蒙版、滤镜、色彩信息及像素历史等经通用命令入口调用：
krita-agent invoke mask.create --params-file ".\examples\round3-mask.json"
krita-agent invoke color.info --params "{}"

# 只阅读已克隆 KDE 源码中的 API 差异，不等同于运行验证：
krita-agent upstream catalog --repo "D:\computer\Krita\Krita-upstream" --from-sha OLD_SHA --to-sha HEAD
```

崩溃后的任务不会自动重画。检查点恢复会先验证 KRA SHA-256；只有用户明确要求，才可能从已保存的步骤边界在新副本上继续。RGBA U8 直接像素编辑采用**独立的、有校验的撤销记录**，不冒充 Krita 原生 Undo。局部修订需要用户确认、预览一致、指定唯一可见的 100% 不透明普通混合绘画图层，并限制修改范围。

局部图像差异分析可选安装 `pip install -e ".[feedback]"`。核心程序无需云端模型或生成式 API。


## 第四轮命令

    krita-agent graph capture --output ".\plans\graph.json"
    krita-agent overlay plan --before ".\images\before.png" --target ".\references\goal.png" --graph ".\plans\graph.json" --output ".\plans\overlay.json"
    krita-agent overlay apply --plan ".\plans\overlay.json" --confirm
    krita-agent longjob plan --file ".\examples\round4-longjob.json"
    krita-agent longjob run --file ".\examples\round4-longjob.json"
    krita-agent brushcal generate --preset "b) Basic-5 Size" --output ".\plans\calibration.json"
    krita-agent scene-v2 compile --file ".\examples\round4-scene-v2.json"

多图层修订采用新增顶层透明绘画层承载**完全不透明的目标区域**
变化，保留原有图层、蒙版和滤镜，不尝试对任意混合模式作不可逆推断。
长任务拆分为带检查点的有界子任务；遇到未知执行结果停止、不盲目重试。
ScenePlan v2 是结构化 JSON 规划，不自动接入 AI 模型，也不安装额外
Krita 第三方插件。

## 第五轮新增命令（源码已实现，验收待完成）

~~~powershell
# 离线结构预检，不连接 Krita，也不修改画布
krita-agent scene-v2 validate --file ".\plans\landscape.json" --min-painted-layers 8

# 仅从已验证的 KRA 检查点边界显式继续任务
krita-agent longjob resume --file ".\examples\round4-longjob.json" --ledger ".\logs\long-job-ID.json" --confirm
~~~

长任务续跑会先将已验证的检查点恢复为新的 KRA 副本，并核对文件哈希与文档身份；恢复结果不明确时会停止，不会继续提交。完整作品审核记录现在绑定到准确的参考图、最终 PNG、可编辑 KRA 和三个阶段预览的 SHA-256，并要求逐个对象及空间关系提供可见证据。这只提升证据完整性，不会自动判断艺术质量，也不代表完整插画已经通过验收。详见[作品审核 v2](docs/ARTWORK-VLM-REVIEW.md)。

第五轮现已新增完整的 `krita-agent creative` 命令链路：可选模型自然语言规划或人工 ScenePlan v3 → 按对象选择笔刷及压力策略 → 审批后执行 Krita 原生绘画 → 根据实际 PNG 像素进行视觉检查 → 生成限定区域的新增图层修订 → 保留各版本 KRA/PNG 供独立验收。模型输出不能直接执行任意 Bridge 命令；任务结果不明确时不会盲目重试。内部 Critic 的「通过」不等于最终艺术作品验收通过。详见[第五轮 API](docs/ROUND5-API.md)。本轮可保存三张 Krita 实际阶段预览，并生成本地只读 HTML 进度页面；实时 Dock 仍留待后续。无需安装新的 Krita 第三方插件。

## 文档与项目管理

[第四轮 API](docs/ROUND4-API.md) · [第四轮验收清单](docs/ROUND4-ACCEPTANCE.md) · [第四轮验收报告](docs/REPORT-011.md) · [第三轮 API](docs/ROUND3-API.md) · [第三轮验收清单](docs/ROUND3-ACCEPTANCE.md) · [项目路线图](docs/ROADMAP.md) · [工程架构](docs/ARCHITECTURE.md) · [第三轮源码实现报告](docs/REPORT-008.md) · [贡献规范](CONTRIBUTING.md)。

原创代码采用 MIT License；Krita 和第三方依赖遵循各自许可证。
