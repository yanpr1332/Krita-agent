# Krita Agent

Krita Agent 是一个计划中的 Windows 本地绘画自动化项目：通过独立 Python 控制器与运行在 Krita 内的 Python Bridge 协作，使用 Krita 原生笔刷绘制可编辑的分层作品。

**项目状态：规划阶段。** 本仓库目前只有结构和设计文档，尚无可运行的 CLI、插件或安装程序。示例命令与接口均为设计目标。

## 目标架构

```text
用户 / 结构化任务 → Windows Python CLI / SDK → 本地 IPC → Krita Python Bridge → Krita 文档与画布
```

优先验证 Windows 上的稳定版与 Next 构建，按实际运行时能力选择绘制路径。连续压感、笔刷切换及 `StrokePoint` / `paintPolylineStroke` 的可用性均须在目标构建中实测；稳定版降级方案尚待验证。后续可加入自然语言规划和视觉反馈，基础绘图链路不依赖云模型。

## 文档

- [开发路线与验收](docs/ROADMAP.md)
- [架构、技术栈与安全边界](docs/ARCHITECTURE.md)
- [贡献与工作流](CONTRIBUTING.md)

`src/` 为独立控制器预留，`plugin/` 为 Krita 插件预留，`tests/`、`examples/` 和 `scripts/` 分别用于测试、示例及部署脚本。这些目录目前没有实现。

## 许可证

项目原创内容采用 [MIT License](LICENSE)，版权所有 Yan Pengrui。Krita 及第三方组件各自适用其许可证；未来分发插件或依赖前需要检查实际代码和分发方式的许可义务。
