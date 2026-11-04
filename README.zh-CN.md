# Krita Agent

[English](README.md) | 简体中文

Krita Agent 是 Windows 环境下的 **Krita 原生绘画自动化系统**：外部 Python Controller 通过仅限本机的鉴权 IPC 连接到 Krita 内部 Python 插件，在真实可编辑的 KRA 文档、图层及笔刷上操作。项目明确区分源码实现、离线测试和真实 Krita 构建验收。

## 项目状态（2026-11-04）

| 阶段 | 状态 | 证据 |
| --- | --- | --- |
| 第一轮：原生绘图与基础任务 | **已验收**：Stable 和两种 Next 构建 | [REPORT-004](docs/REPORT-004.md) |
| 第二轮：可编辑工作流、预览、导入及 Dock | **已验收**：34 项离线测试及真实像素/Dock 验收 | [REPORT-006](docs/REPORT-006.md)、[REPORT-007](docs/REPORT-007.md) |
| 第三轮：安全检查点、非破坏性蒙版、局部修订与上游证据登记 | **三个本机构建已验收，57 项离线测试通过** | [REPORT-009](docs/REPORT-009.md)、[第三轮验收清单](docs/ROUND3-ACCEPTANCE.md) |
| 第四轮：多图层修订、长任务、笔刷档案、ScenePlan v2 | **源码已提交，尚未执行测试或实机验收** | [REPORT-010](docs/REPORT-010.md)、[第四轮验收清单](docs/ROUND4-ACCEPTANCE.md) |

已完成的前三轮验收覆盖 Stable 5.3.4.1、Next Qt5 5.4.0-prealpha 和 Next Qt6 6.1.0-prealpha，不代表第四轮新功能也通过。第三轮验收见 [REPORT-009](docs/REPORT-009.md)。第四轮没有运行新测试、Krita 实机或 GitHub Actions。

## 工程结构

```text
src/krita_agent/             外部控制器、任务协议、曲线与结构化场景规划、
                             基于目标图像的局部修订、反馈和上游追踪
plugin/krita_agent_bridge/  Krita 内部插件、原生图层、蒙版、检查点、
                             独立可逆像素记录、跨会话复制与可选 Dock
tests/                      前三轮记录 57 项通过；第四轮新增测试未执行
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


## 第四轮新增源码接口（尚未验收）

    krita-agent graph capture --output ".\plans\graph.json"
    krita-agent overlay plan --before ".\images\before.png" --target ".\references\goal.png" --graph ".\plans\graph.json" --output ".\plans\overlay.json"
    krita-agent overlay apply --plan ".\plans\overlay.json" --confirm
    krita-agent longjob plan --file ".\examples\round4-longjob.json"
    krita-agent longjob run --file ".\examples\round4-longjob.json"
    krita-agent brushcal generate --preset "Basic-5 Size" --output ".\plans\calibration.json"
    krita-agent scene-v2 compile --file ".\examples\round4-scene-v2.json"

多图层修订采用新增顶层透明绘画层承载**完全不透明的目标区域**
变化，保留原有图层、蒙版和滤镜，不尝试对任意混合模式作不可逆推断。
长任务拆分为带检查点的有界子任务；遇到未知执行结果停止、不盲目重试。
ScenePlan v2 是结构化 JSON 规划，不自动接入 AI 模型，也不安装额外
Krita 第三方插件。

## 文档与项目管理

[第四轮 API](docs/ROUND4-API.md) · [第四轮验收清单](docs/ROUND4-ACCEPTANCE.md) · [第四轮开发报告](docs/REPORT-010.md) · [第三轮 API](docs/ROUND3-API.md) · [第三轮验收清单](docs/ROUND3-ACCEPTANCE.md) · [项目路线图](docs/ROADMAP.md) · [工程架构](docs/ARCHITECTURE.md) · [第三轮源码实现报告](docs/REPORT-008.md) · [贡献规范](CONTRIBUTING.md)。

原创代码采用 MIT License；Krita 和第三方依赖遵循各自许可证。
