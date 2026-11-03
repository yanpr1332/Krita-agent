# Krita Agent

[English](README.md) | 简体中文

Krita Agent 是 Windows 本地 Krita 原生绘画自动化控制器。包含 Python CLI/SDK、Krita 进程内 Bridge、回环 IPC、图层和笔刷命令、异步绘图任务、基础上游功能追踪。

**2026-11-03 第一轮开发状态：代码已写入，尚未执行运行验证。** 不等于已确认 Krita Stable/Next 兼容、插件可加载或成功生成图片。按用户要求，本轮没有执行测试、部署插件或打开 Krita。

## 架构

外部 CLI → 本机 127.0.0.1 JSON（随机令牌）→ Krita Python Bridge（Qt GUI 线程）→ Krita 原生画布、图层、笔刷。

- Controller：src/krita_agent/cli.py、client.py、session.py、protocol.py、geometry.py
- Bridge：plugin/krita_agent_bridge；支持 Qt5/Qt6 的导入分支，具体兼容性待测
- Upstream：src/krita_agent/upstream.py；源代码差异候选、报告、基线
- 纯 Python 测试：tests/；真实 Krita 验收尚未开始

## 安装与首次启用（尚未执行）

先在 Windows PowerShell 进入仓库，然后使用原生 Windows Python：

~~~powershell
cd "D:\computer\Krita\Krita-agent"
python -m pip install -e .
python scripts\install_plugin.py
~~~

第二个命令只预览将安装的插件。确认共享的 Krita 用户资源目录及备份后，显式执行：

~~~powershell
python scripts\install_plugin.py --apply
~~~

如果已有同名插件，需手动核实后加 --replace；安装器会先备份。Stable 与 Next 可能共用资源目录；不要盲目替换。进入 Krita 的 Settings → Configure Krita → Python Plugin Manager 启用 Krita Agent Bridge，重启 Krita。Bridge 仅在由 launch 注入令牌时启用，普通启动保持静默。

~~~powershell
krita-agent doctor
krita-agent launch --krita "D:\computer\Krita\Krita_Next\bin\krita.exe"
krita-agent connect
krita-agent capabilities
krita-agent canvas create --width 1024 --height 1024
krita-agent layer add --name "Line Art"
krita-agent brush set --size 24 --color "#AA5544" --pressure-enabled true
krita-agent draw demo --wait
~~~

launch 只是启动一个 Krita 进程并创建本机用户配置目录中的会话凭据，不能证明 Bridge 已加载。若路径不同，先调整 exe 路径。不要同时启动 Stable/Next 并复用同一端口；需要并行时分别指定端口与会话文件。

任务运行：

~~~powershell
krita-agent job run --file ".\examples\pressure-demo.json" --wait
krita-agent job list
krita-agent job status JOB_ID
krita-agent job pause JOB_ID
krita-agent job resume JOB_ID
krita-agent job cancel JOB_ID
~~~

作业执行采取每一步的安全检查点；单条原生笔触执行中无法承诺立即中断。文件只能保存到 launch 所配置的输出目录中，默认用户 Pictures/KritaAgent，默认拒绝覆盖已有文件。失败后的部分画布保留以便检查。

## 上游追踪

~~~powershell
krita-agent upstream snapshot --repo "D:\computer\Krita\Krita-upstream"
krita-agent upstream init --repo "D:\computer\Krita\Krita-upstream"
krita-agent upstream check --repo "D:\computer\Krita\Krita-upstream" --write-report ".cache\krita-upstream-report.md"
~~~

init 创建本地基线；check 默认只读已有本地 Git，显式 --fetch 才联网更新；更新基线需显式 --update-baseline。git diff 只产生源码候选，不能证明当前安装包具有对应 API。

## 首轮验收状态

- 源码、JSON 协议、插画演示任务、任务控制、压感适配器、输出保护、上游报告：已编写，待验收。
- 自动测试：已编写，未运行。
- Bridge 安装/启用、真实 Krita 运行、压感笔触视觉效果、保存并重新打开 KRA：未验证。
- 下一步手动验收参阅 docs/ACCEPTANCE.md 和 docs/REPORT-003.md。

## 许可

原创代码采用 MIT License；Krita 本体及第三方依赖仍遵循各自许可证。Bridge 发布前须复核 Krita GPL 兼容和实际分发安排。
