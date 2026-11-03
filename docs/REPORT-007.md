# Round2 补充验收：Dock 与像素结果（2026-11-03）

结论：REPORT-006 留下的 Dock 实际按钮交互和编辑效果像素验证已完成，三个指定构建均通过。本文更新该报告中的未完成项；不是对所有未来 Krita 构建或任意色彩空间的保证。

## 实机环境与执行

Stable 5.3.4.1 bd6e8d0、Next Qt5 5.4.0-prealpha 2687e5d、Next Qt6 6.1.0-prealpha 2687e5d。每次只启动一个测试进程，使用唯一的仓库缓存输出目录；仅结束脚本记录的本次测试 PID。共享插件目录由安装脚本先备份后更新，最终安装源码与本次修复一致。未修改现有作品。

## 实际发现并修复

- selection.paste 原生接口会返回成功却没有粘贴目标像素。改用会话内、最多 400 万像素的 RGBA U8 缓冲，复制时应用选区覆盖率，粘贴时执行 source-over 混合；拒绝越界与锁定图层。剪切仍由原生 Selection.cut 清除源区。系统剪贴板导入不属于此接口，复制内容不会在进程重启后保留。
- layer.set 修改可见性等属性后，以及原生 undo/redo 后，导出可能使用旧投影。编辑后刷新投影并等待原生任务完成。
- 原生 thumbnail 会裁掉透明画布边界，使预览大小及坐标不可靠。画布/图层预览改为完整画布投影后缩放，保留透明度；图层预览显式要求 RGBA U8。
- Qt6 Dock 注册失败：DockRight 需要从作用域枚举 DockPosition 访问。优先兼容 Qt5 的直接成员，缺失时使用 Qt6 枚举。

## Dock：三个构建均为实际 UI 点击

使用 computer-use 技能的 sky 接口观察窗口和控件，实际点击 Pause / Resume / Cancel；不是直接调用 Python 按钮回调，也不是只验证 Bridge 命令。

- Stable：Pause 后显示 paused 366/400，Bridge 同时确认；Resume 后完成 400/400；第二任务 Cancel 后为 cancelled，done=1。
- Qt5：Resume 后观察 running 273/400；另一任务 Resume 后 Pause，观察并由 Bridge 确认 paused 343/400；Cancel 后为 cancelled。
- Qt6：修复注册后显示面板和三个可点击按钮，Resume 后显示 running 344/400；Pause 后 paused 360/400，两次独立查询的进度保持不变；Cancel 后为 cancelled。
- 已观察可读标签、连接状态、运行/暂停进度及空闲提示，按钮布局完整可用。Qt5/Qt6 DPI 布局不同，均无阻碍操作的遮挡或截断。

原始摘要：acceptance-evidence/round2-dock-{stable,qt5,qt6}.json。

## 像素：每个构建 8 组断言全部通过

scripts/acceptance_round2_pixels.py 在真实 Krita 文档上执行操作、导出 PNG，并用 Pillow 比较像素。不是用模拟 Krita 对象证明实机效果。

1. 图片导入：检查指定位置的 RGB 与 alpha（色彩转换允许每通道 2/255 误差），画布外部仍透明。
2. 选区：复制/粘贴目标确实为红色，源区仍在；剪切后源区透明，目标保留。
3. 变换：移动后的 alpha 包围盒精确为 (15,27,35,37)；Bicubic 缩放为 (15,27,55,47)；90° 旋转为 (25,17,45,57)。边缘允许最多 4 像素插值范围，不将变换命令返回视为像素证据。
4. 撤销/重做：原生笔触产生非空像素，undo 后逐像素等于绘制前图像，redo 后逐像素等于已绘制图像。
5. 属性/清除：隐藏后透明，50% 不透明度为预期 alpha，恢复后逐像素相同，clear 后为空。
6. 预览与保存：区域、全画布、图层预览在原尺寸下与导出 RGBA 逐像素相同；复制图层可保留相同结果，删除副本后隐藏原图层的画布为空；裁剪等于参考图的相应区域；KRA 重开后逐像素相同。
7. 半透明叠加与混合模式：半透明红色选区覆盖蓝色得到预期 RGB，Multiply 叠加绿色得到黑色。
8. 文件图层与顺序：链接文件图层的颜色位置正确，隐藏后透明；蓝色层重排至红色层下方后，交叠位置变为红色。

原始结果：acceptance-evidence/round2-pixels-{stable,qt5,qt6}.json。PNG/KRA 仅保存在本地 .cache/round2/visual-*，不提交生成作品与凭据。

## 离线回归与范围

34 tests passed；compileall、git diff --check 通过。新增覆盖选区遮罩 alpha、source-over、越界/锁层拒绝和两种 Dock 枚举布局。存在一条宿主 anyio 的 pytest 弃用警告，不影响通过结果。

本轮已补齐上次明确遗漏的验收项。原生笔触撤销通过不意味着直接像素替换自动成为原生撤销事务；本实现对直接像素编辑不作此承诺。像素断言使用确定性 RGBA U8 图案，未宣称所有 ICC 配置、所有角度和所有画笔都具有相同行为。

复测脚本接受 --session 私有 JSON（token、out、build），Bridge 固定测试端口 47721。它会创建、修改、导出测试文档，必须只指向一次性测试会话。所有导出名称唯一，原生拒绝覆盖保护保持有效。
