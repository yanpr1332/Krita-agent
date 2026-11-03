# Krita Agent

**第二轮本机验收已完成（2026-11-03）**：34 项离线测试通过，Stable、Next Qt5、Next Qt6 的 Dock 按钮及像素断言通过。[REPORT-007](docs/REPORT-007.md) 更新了下文历史“未验证”状态。

[English](README.md) | 简体中文

Krita Agent 是面向 Windows 的 Krita **原生绘图自动化控制器**：外部 Python CLI/SDK、Krita 内部插件、受控本机通信、可编辑分层绘图、压感轨迹，以及 KDE 上游功能追踪。

## 当前状态

- **第一轮已验收**：2026 年 11 月 3 日的验收报告记录了 Stable 5.3.4.1、Next Qt5 5.4.0-prealpha、Next Qt6 6.1.0-prealpha 三个构建，以及 18 项通过的离线测试。具体见 [REPORT-004](docs/REPORT-004.md)。
- **第二轮已编写源码，尚未验证**：在 `feat/round2-advanced-workflow` 分支增加高级图层、素材导入、选区、预览、轨迹处理、持久化任务、上游追踪增强及可选 Dock 面板。**这些新增能力还不能称作“在 Krita 上运行通过”**。见 [REPORT-005](docs/REPORT-005.md)。
- 第二轮不运行测试、不安装插件、不自动触发 GitHub Actions，也不合并主分支。

## 工程结构

```text
src/krita_agent/             外部 Controller、CLI、轨迹、反馈、任务与源码追踪
plugin/krita_agent_bridge/  Krita 内部 Bridge、图层/文档/素材/任务与 Dock
tests/                      离线测试源代码；本轮新测试未运行
examples/                   JSON 工作流和轨迹示例
scripts/                    插件安装与辅助工具
docs/                       架构、API、开发报告与路线图
```

控制链路：ChatGPT / Codex / VS Code → Windows Python → 仅限本机 127.0.0.1 的鉴权 IPC → Krita Python 插件 → 原生画布与图层。基础功能不依赖云端模型。

## 首次使用

在 Windows PowerShell 中运行：

```powershell
cd "D:\computer\Krita\Krita-agent"
python -m pip install -e .
python scripts\install_plugin.py
```

安装脚本默认只预览；确认原有 Stable/Next 共享资源目录并做好备份后，再显式执行：

```powershell
python scripts\install_plugin.py --apply
```

在 Krita 的 **设置 → 配置 Krita → Python 插件管理器** 启用 Bridge 后重启。通过 Controller 显式启动指定 Krita：

```powershell
krita-agent launch --krita "D:\computer\Krita\Krita_Next\bin\krita.exe" --output-dir "D:\drawings\out" --input-dir "D:\drawings\references" --dock
krita-agent connect
krita-agent capabilities
```

`--dock` 仅表示注册可选控制面板，**本轮未验证该面板兼容性**。

## 第一轮已验证的功能

新建画布、笔刷控制、图层、分段/连续笔触、压感预设、任务队列与阶段性暂停恢复、KRA 保存并重新打开、PNG 导出、基本安全拒绝等。具体版本和限制以第一轮验收报告为准。

## 第二轮新增命令（源码已编写、未验证）

```powershell
# 查询递归图层树
krita-agent invoke layer.tree --params "{}"

# 列举笔刷资源
krita-agent invoke brush.list --params "{}"

# 在已有文档上提交多步修改
krita-agent workflow --file ".\examples\round2-edit-workflow.json" --wait

# 曲线插值、平滑、等距重采样
krita-agent draw stroke --file ".\examples\stroke-control.json" --spline --smooth --spacing 3

# 查询中断作业记录：不会自动重放
krita-agent job recover YOUR_JOB_ID

# 本地预览文件对比
krita-agent feedback compare ".\before.png" ".\after.png"
```

复杂参数建议写入 JSON 文件，用 `krita-agent invoke 命令名 --params-file 文件路径` 调用，避免 Windows shell 转义错误。

**操作保护**：导入图片只能来自显式指定的输入目录；所有输出必须位于授权输出目录；默认禁止覆盖。删除、像素替换等破坏性操作要求明确确认。任务崩溃后不会自动重复落笔，作业日志并不等于可直接恢复的 KRA 快照。

**上游追踪**：支持从 Git 差异分析中分类出变更候选，并与保存的运行时符号记录关联；“源码出现”不意味着安装版本能用，真实行为仍需独立测试。

参阅 [第二轮 API 说明](docs/ROUND2-API.md)、[开发路线](docs/ROADMAP.md)、[架构](docs/ARCHITECTURE.md)、[第一轮验收](docs/REPORT-004.md)、[第二轮实现报告](docs/REPORT-005.md)。

原创部分采用 MIT License。Krita 和第三方依赖另按各自许可使用。
