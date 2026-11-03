# Krita Agent

[English](README.md) | [简体中文](README.zh-CN.md)

Krita Agent 是规划中的 Windows 本地绘画自动化项目。它计划使用独立 Python 控制器和 Krita 内的自研插件，调用 Krita 原生笔刷，生成可复现、可编辑的分层作品。

> **状态：早期开发。** 已提供实验性的只读环境探测工具；Bridge、安装程序和自动绘画功能尚未实现。文档中的命令、协议和功能均为设计草案，具体接口须经目标 Krita 构建验证。

## 项目目标

- 通过 Krita 原生绘画引擎绘制，而非仅导入外部生成的图片。
- 用结构化任务描述画布、图层、笔刷、轨迹、压力和输出。
- 保存可编辑的分层 `.kra`，并导出预览图。
- 探测稳定版与 Next 的实际能力，按验证结果选择或降级绘制路径。
- 追踪 Krita 上游接口变化，形成可追溯的兼容报告与候选测试。
- 后续可选接入自然语言规划与视觉反馈；基础链路不依赖云模型。

```text
用户 / 外部程序 → Windows Python CLI / SDK → 本地受控通信 → Krita Python Bridge → 原生绘画引擎
```

普通外部 Python 进程不能直接通过 `import krita` 控制另一个 Krita 进程，因此计划以应用内插件提供受控桥接。WSL2 并非初期依赖。

## 技术方向

Windows Python 3、Krita Python / LibKis API、Krita Python Extension、目标构建自带的 Qt / PyQt、本地 IPC、JSON 与 Schema。Git、虚拟环境和 pytest 拟用于开发与测试；CLI 框架、通信实现及版本约束尚待原型确定。优先测试 Qt5 构建，后续验证 Qt6。

压感绘制优先研究 Next 的连续笔触接口，并测试稳定版可行的分段降级路径。接口出现在源码或文档中并不代表当前安装的构建支持；笔刷是否响应压力也需要独立验证。

## 文档导航

- [完整设计方案](docs/DESIGN.md)：功能清单、技术方案、示例协议、工作流、压感、上游追踪与参考资料。
- [开发路线与验收](docs/ROADMAP.md)：阶段任务及真实绘画验收。
- [架构与安全边界](docs/ARCHITECTURE.md)：组件职责、能力验证和部署原则。
- [贡献指南](CONTRIBUTING.md)：分支、评审、验证及双语 README 维护约定。

## 仓库结构

```text
src/krita_agent/   独立控制器（占位）
plugin/            Krita Bridge（占位）
tests/             测试（占位）
examples/          示例（占位）
scripts/           安装和维护脚本（占位）
docs/              设计与路线
```

Krita 安装文件、官方源码克隆、个人资源、缓存及批量作品不属于本仓库。在仓库根目录执行 `python -m pip install -e .` 后，可用 `krita-agent doctor --krita "C:\path\to\krita.exe"` 运行实验性探测。它对指定程序执行 `--version` 并报告错误或超时；不会检测运行时 API。Krita 内部探测脚本和限制见[第一轮开发报告](docs/REPORT-001.md)。

## 许可证

原创内容采用 [MIT License](LICENSE)，版权所有 Yan Pengrui。Krita 和第三方组件适用各自许可证；插件实际实现和分发前需检查相关许可义务。


