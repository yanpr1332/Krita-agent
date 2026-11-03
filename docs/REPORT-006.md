# Round2 修复与实机验收 — 2026-11-03

本报告替代同名文件中的初步离线失败记录。核心 API 实机验收通过；可选 Dock 的按钮交互和视觉效果未单独验收。

## 修复

1. 安装 Pillow 后，普通二进制文件比较不再抛 UnidentifiedImageError；保留 SHA256 结果，pixel_comparison 返回 unsupported_image。
2. RGBA 比较保留 alpha 通道变化，changed_bbox 能识别纯透明度变化。新增回归测试。
3. 原生 Resource 没有 valid() 方法，导致 brush.inspect 失败。改为检查原生资源名称和文件名；valid 表示资源元数据存在，不代表笔刷压力行为已验证。

## 验证结果

- 离线：27 passed；compileall 与 git diff --check 通过。
- Stable 5.3.4.1 bd6e8d0、Next Qt5 5.4.0-prealpha 2687e5d、Next Qt6 6.1.0-prealpha 2687e5d：每个构建 54 条记录通过。详见 acceptance-evidence/round2-{stable,qt5,qt6}.json。
- 真实命令覆盖递归图层树、检查、改名、属性、移动、复制、组、重排、缩放、旋转、删除；多文档列举/激活/关闭；矩形选区、复制、剪切、粘贴、清除；笔刷枚举与检查；可编辑图片及文件图层导入；全画布/图层/区域预览；像素填充/清除；撤销/重做；裁剪、KRA 保存重开、PNG 导出。
- 多步工作流完成；任务 history/recover 查询、pause/resume/cancel 成功。真实进程终止并重启后任务变为 interrupted，replay_safe=false，未自动打开文档或重放步骤。
- 缺少删除/像素修改确认、输入目录逃逸、输出目录逃逸、覆盖已有 KRA 均被拒绝。
- 独立检查三个构建输出的 KRA ZIP 完整性及层名、PNG 裁剪后的 200×200 尺寸、预览文件的实际尺寸均通过。

## 执行与证据边界

首次尝试的环境变量配置未隔离 Krita 的实际共享资源目录，加载旧版插件；该次结果已作废。之后使用安装脚本对共享插件进行时间戳备份，安装当前源码。测试作品均位于仓库 .cache/round2 的独立输出目录，没有覆盖用户作品。最终安装插件包含本报告中的修复。

曾尝试按进程名关闭 Krita，被自动审批拒绝；之后核对测试 PID 和监听端口，只关闭本次启动的实例。后续矩阵由脚本仅终止自身创建的进程。

54 条记录是命令响应、保护拒绝和重启恢复检查，不代表逐像素证明所有编辑效果。导入色彩、缩放插值、选区像素内容及撤销视觉正确性未进行独立像素断言。以 --dock 启动的三个构建能正常加载 Bridge，但 Dock 可视布局、按钮点击和状态刷新未单独验证。第一轮压力效果与第二轮轨迹算法离线测试保留原有证据，不扩张为本轮新增视觉结论。

scripts/acceptance_round2.py 为可重复的原生命令验收脚本，需要明确启动一次性测试 Bridge，并设置 KRITA_AGENT_TOKEN、TEST_PORT、TEST_OUT、TEST_BUILD。TEST_OUT 必须是 Bridge 的全新授权输出目录；脚本会创建、修改、保存和关闭测试文档。测试凭据不写入证据。
