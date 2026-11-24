# Krita Agent：线稿素材、公众号图片采集、知识库与模型学习方案

> **状态：设计文档（R18 主体，R15–R17 可先使用少量素材；可选 R21 才涉及训练）。** 未下载任何用户素材、未训练模型、未访问私人公众号或启动云端图片分析。任何来源的下载、外部上传、训练和公开展示均需按实际权利分别判断。本文不是自动爬取第三方内容的授权。
>
> [R13–R20 总路线图](ARTIST-ROADMAP-R13-R20.md) · [目标架构](ARTIST-ARCHITECTURE-R13-R20.md) · [验收](ARTIST-ACCEPTANCE-R13-R20.md)

## 1. 为什么线稿值得收集，哪些事情不能假装它能做到

静态线稿可提供：（1）对象轮廓、比例、姿态与连接关系；（2）线宽粗细、曲率、疏密、局部排线和构图节奏；（3）特定画风的表现目标；（4）与同主题授权案例的检索入口。

单张 PNG/JPG **通常不能提供**真实绘制顺序、分笔/连续笔划、每点压力、实时速度、擦除修改历史、选用的具体 Krita 预设。Skeleton、Vectorization、VLM 可估计一些曲线结构和物体语义，但不应把反推的笔顺当成真实作者示范。KRA 的多层数据也不自动等于可重建的笔触时间序列。

因此先分三条数据路线：

1. **静态线稿/结构**：图像、线条特征、部件、姿态、风格标签和可搜索索引。
2. **线稿 ↔ 彩色成品配对**：主体/构图一致的颜色、分区、光照、材质对比；单张彩稿不是全部绘画过程。
3. **真实笔触示范**：主动采集原生路径、时间、压力/tilt、笔刷、尺寸、颜色和实际 Krita 输出；用于未来的“动作学习”，必须明确区分真实传感器和合成生成轨迹。

## 2. 用户素材清单与分批交付

| 类别 | 推荐首批 | 必需性 | 价值和最佳格式 |
| --- | --- | --- | --- |
| 高质量线稿 | 20–30 张 | R18 需要 | PNG 透明优先、JPG/SVG/KRA 也可；人物、动物、植物、静物、建筑等多类别 |
| 细线起收/线宽特写 | 5–10 张 | R16 推荐 | 高分辨率局部、自然 taper / 排线方向 / 连续曲线示范 |
| 线稿+彩图配对 | 5–10 组，有多少用多少 | R17 推荐 | 两图同主体构图，最好还有底色/阴影/高光阶段 |
| 独立彩稿 | 5–10 张 | R17 推荐 | 体积、冷暖、光照和材质 |
| Krita 源工程 | 3–5 份，可选 | 非强制 | 可分离图层、笔刷环境；不能假定有历史笔顺 |
| 真实绘制视频/轨迹 | 2–5 份，可选 | R21 才特别关键 | 录屏/显式记录 timestamp、pressure、stroke id、brush preset |
| 微信公众号/其他文章 | 3–5 篇或 HTML+图片离线包 | 采集器首批需要 | **有权保存/分析**的 URL 或导出文件、标题/作者/来源 |
| 不喜欢的失败例图 | 5–10 张 | 高价值 | 机械粗线、残缺结构、分段暗点、空洞和不自然色彩 |
| 喜欢的风格作品 | 5–10 张 | R16/17 推荐 | 指出“喜欢什么”：细笔、起收、线宽、材质、色彩而非只给文件 |

不要一次性要求全部。R13–R14 只需现有 R12 失败证据和合成输入；R15 可用合成形状；R16 起优先少量高质量线稿；R18 再批量导入。建议保留原始分辨率，长边约 1600px 以上更利于提取细线，但低分辨率文件也可归档并标记限制。**不允许强行增大分辨率后把伪造的细节当成原作者信息。**

## 3. 输入格式与原文件保全

支持方案：

- PNG/JPG/WebP：静态图像，用于 reference/annotation；透明 PNG 优先保留 alpha。
- SVG：矢量路径与变换、stroke styles 可分析，但需拒绝不可信脚本/外链/任意文件访问；禁止在导入阶段执行未知代码。
- KRA：读经用户许可的原生层结构；保持原稿不可变，另存分析版本。
- HTML/用户导出网页资料：提取文章图片和顺序、出处、许可，图像不可只信 URL 后缀。
- 用户提供 ZIP/目录：检查路径穿越、大小/压缩炸弹、重复和符号链接，限定文件数量、单文件字节、解码像素数。

处理结果永不覆盖 originals。每个 import job 有稳定 ID、输入 SHA-256、清洗工具版本、操作历史、失败状态、图片数量和存储开销。重复图片使用 SHA-256 + 感知哈希辅助人工判定；**感知哈希不等于法律或像素相同**。

推荐目录（**位于忽略的私有工作空间**，不是公开仓库数据集）：

    local-secrets/                  # 可选本机配置/凭据；不传 GitHub
    private-references/             # 已在 .gitignore 中忽略
      lineart-library/
        manifests/
          import-jobs/
          rights/
        sources/
          <source-id>/
            originals/
            normalized/
            lineart/
            thumbnails/
            annotation/
            hash-index.json
        index/
          versioned-index.json
        splits/
          train.json
          validation.json
          heldout.json
    artwork-results/                # Git 忽略的原生作画证据，不作为素材公共库

若改用 data-private 等其他目录，必须先验证/增加 Git ignore 规则并为用户提供明确路径选择；**当前根 .gitignore 已有 private-references/ 和 local-secrets/**，不应仅写下新目录名就假定它不会被提交。

需要公开复现的仅可提交：格式/schema、代码、人工合成或许可明确的极小测试图、脱敏统计。不得直接提交真实作者素材、私有网页 HTML 或 KRA。

## 4. 每个样本的来源与授权模型

权利字段最少独立判断：

- `can_store_locally`：是否允许保存/缓存用于用户当前用途。
- `can_analyze_locally`：是否允许本地识别/分类/提取。
- `external_upload_permitted`：是否允许发给具体第三方模型；记录供应商/范围/用户同意时间。
- `training_permitted`：是否允许用于训练/微调（区别于推理参考）。
- `can_publish_preview`：是否允许公开展示缩略图、相似作品或出处。
- `rights_basis`：owned / public_domain / licensed / explicit_permission / unknown；未知不自动升级为许可。
- 原作者、来源 URL、文章标题、取得时间、许可原文或相关证据、适用地域/限制（若已知）。

**允许访问和下载不自动代表允许训练、外部上传、二次发布或商用。** 第三方作品即便很老或看似开放，也需按该来源的真实权利声明和用途确认。不在聊天或 GitHub 文件中暴露可能包含隐私的源 URL/账号/路径。

## 5. 微信公众号 / 类似文章的采集器设计

### 5.1 输入策略（按优先级）

1. **作者或平台提供原图/导出包**：质量和可追溯性最好。
2. **用户保存的 HTML/网页导出 + 本地图片**：离线解析，避免网络稳定性和身份认证问题。
3. **公开可访问且授权允许的文章链接**：在支持的浏览器会话读取合法加载的页面，按正文和图片次序发现资源。

微信公众号文章常见图片懒加载（例如 `img[data-src]`）。实际页面结构会变化，不能把一个 CSS 选择器当成长期 API。必须支持图片 src、data-src、srcset、picture、正文外的无关图过滤，必要时使用安全浏览器抓取**用户有权访问的已渲染 DOM**。不破解登录、反爬、付费限制、验证码、Cookie 或身份验证；站点/作者条款禁止时停止并提示用正式导出。

### 5.2 建议处理流水线

    URL or HTML + images
       → permission/source preflight
       → parse article title / author / date / canonical URL
       → discover inline image references in reading order
       → bounded authorized download OR user-provided image attachment
       → decode + size/mime safety + SHA
       → exclude icons/QR/avatars/ads/small decorative images
       → identify line-art / colored art / scans / composites
       → split multi-panel long images (reviewable proposal)
       → produce immutable originals + processed derivatives
       → human quality/rights review → index

图片提取程序不应把解析 HTML 当成执行 JavaScript；对 `javascript:`、`file:`、本地网段/内部 IP、重定向、任意协议或超大文件必须拒绝。下载范围只限允许的 HTTP(S) 公共资源，防 SSRF，限定总大小、数量和频率，记录失败原因且不悄悄跳过许可。

### 5.3 长图拆分与去重

一篇长图可能同时包含数张线稿、标题/说明、二维码和完整成品。自动检测面板边界只能提出候选，需在首批样本中人工检查裁切是否伤及作品。每个 crop 保留 parent image id、像素 crop box、算法版本、页内顺序和导入来源，不丢掉原始可追溯性。

去重优先 exact SHA，其次感知相似分组；调整分辨率、转码或加水印后的相似图片需要人工复核。若同一作品来自多来源，权利记录不能自动互相传递。

### 5.4 失败/例外处理

访问限制、图片缺失、权限不确定、下载部分失败、文件太大、长图多页、无法解析的版权声明、作者实名隐私等，标记 BLOCKED / REVIEW_REQUIRED；不得自动去掉限制继续抓取，更不得在 repo 内上传原始失败文件求助。

## 6. 线稿清理、结构提取和可信度边界

**原始图保真优先**。可以在衍生版本中完成：

- 白底/透明/灰底预处理、边缘检测、轻度去噪、必要时颜色空间归一。
- 纯线/草图/彩稿/摄影/非作品分类，标注人工校对与模型标签来源。
- 二值化、骨架化、线段/结点提取、端点/交叉点检测。
- 多段曲线拟合（SVG/polyline/Bezier）并对照原像素报告几何误差。
- 轮廓闭合候选、封闭区域、与对象部件的关联。对于模糊线稿标记不确定而非伪造完整闭合结构。
- 线宽直方图、曲率、疏密和排线方向；压感只能作为**视觉线宽代理，不是设备传感器读数**。
- 可选经授权的 VLM 提出“人物/动物/室内”“部件关系”等结构假设；必须允许人工修正。

每次处理都保留：原始 SHA、衍生文件 SHA、算法版本、输入尺寸、裁剪坐标、置信度来源、人工是否确认。误判不能自动变成“已学会技法”。

## 7. 技法与检索知识库格式

推荐本地记录：

    {
      "schema": "krita-agent-lineart-asset/1-proposal",
      "id": "lineart-000001",
      "source_id": "source-001",
      "original_sha256": "<SHA256_HEX>",
      "file": "sources/source-001/originals/000001.png",
      "subject_tags": ["animal", "cat"],
      "pose_tags": ["sitting", "three_quarter"],
      "style_tags": ["thin_contour", "tapered", "hatching"],
      "parts": ["head", "ears", "body", "legs", "tail"],
      "has_color_pair": false,
      "stroke_trajectory_observed": false,
      "review_status": "pending",
      "rights": {
        "rights_basis": "owned",
        "can_store_locally": true,
        "can_analyze_locally": true,
        "external_upload_permitted": false,
        "training_permitted": false,
        "can_publish_preview": false
      }
    }

这是**目标 schema 草案**，不是已经加入代码、已有图像或确切 SHA。实现还要独立校验来源证据、许可变更、同一文件多来源、删除/撤销授权后的索引失效和数据派生删除要求。查询结果应有 source ID 和有效许可证，图像不应默认变成外部模型上传内容。

检索方式逐级实现：

1. 文本标签、对象/姿态/部件和人工标注索引（无需复杂模型，可离线实施）。
2. 基础线条几何/颜色特征相似，结构明确时选用。
3. 经用户许可的图文嵌入向量搜索或视觉重排，以输出证据示例和来源，不根据相关性分数声称“学会画画”。
4. 将检索的示范映射到 v4/R14 的结构意图和 R10 technique profile；除非有真实 native 验证，不把候选技术标为 human_reviewed。

## 8. “学习”的三个层次和触发标准

| 学习形态 | 核心能力 | 数据依赖 | 是否修改模型权重 |
| --- | --- | --- | --- |
| 检索增强 + 技法记忆（首选） | 查找相似姿态、线宽、画法、材料配方 | 许可线稿、标注、技术档案 | 否 |
| 专用视觉模型或条件生成（可选） | 更好的轮廓/部件识别、线稿到配色建议 | 干净标注、配对图和训练许可 | 可能，需要独立训练 |
| 真实动作模仿（可选） | 笔顺、压力、速度、修改过程 | 带时间/压力/笔刷记录的真实示范 | 可能，需要动作数据 |

只有样本多、质量稳定、法律许可、任务定义清楚、独立留出评测集时，才建议评估模型微调。当前仓库的 R10 技法档案与 R18 检索只是模型外部知识，不是 LoRA 或基础模型权重更新。API Key 也不等于训练许可和训练能力。

未来若采用外部条件生成（包括线稿到彩图），生成位图只能做**辅助草案/对比**，不能用贴进 KRA 的图片取代真实原生笔刷/层绘制验收。

## 9. 数据集分割与防止评测泄漏

- 参考图库按**作品/作者/系列/近重复组**分隔 train/dev/heldout，而不是把同一线稿不同裁切分到不同组。
- 正式 24 项题目和锁定参考图属于项目验收集，不能进入用于优化相同题目输出的训练/检索调参；需要时使用额外的开发集。
- 第一期 30–50 张可用线稿只是采集管道的功能性样本，并不是足以训练通用绘画模型的数量。
- 缺少授权不能用“我本地看到过”替代，若许可撤回要阻止新的检索/模型使用并按记录处理派生物。
- 每次线上或本地实验记录：哪一版本素材索引、哪一组检索命中、模型/配置、结果图哈希、对照测试，便于判断改进是否归因于知识库。

## 10. 需要实现的 CLI / 测试（规划）

建议 R18 在用户授权后提供：

- `krita-agent library import --file ... --rights ...`：导入本地图像和许可记录；dry-run 默认，正式写入须显式选项。
- `krita-agent library import-article --html ...`：在本地导入已保存的 HTML/图片包；公共 URL 路径单独权限检查。
- `krita-agent library inspect --id ...`：查看来源、许可、图像信息和衍生数据。
- `krita-agent library annotate --id ...`：自动候选 + 人工复核，不将未复核模型标签当作事实。
- `krita-agent library search --subject ... --style ...`：返回已授权样本及限定用途。
- `krita-agent library export-metadata --sanitized ...`：只输出允许公开的非敏感统计，不自动推送 GitHub。

上述 CLI 均为**建议接口，当前尚未实现**。若最终采用其他命令名或数据结构，以对应 R18 PR 的 API 文档为准。

**测试门禁（初始建议）：** 本地导入/重复/权限拒绝/异常网络/HTML 格式变化/巨图/ZIP 安全/路径穿越/撤销许可/授权分层/失效参考拒绝均有离线测试；30–50 张初始集索引可复现、人工抽查失败保留；在独立小型绘画任务上开展开关知识库 A/B 视觉对照，**没有独立可见收益就不宣称学习成功**。

## 11. 用户交接最简方案

最初只需要：

1. 已有 20–30 张你有权保存并用于知识库的线稿（少量更好也可以），优先细线、不同主体和姿态。
2. 若方便，附 5 张你喜欢的效果/5 张不喜欢的机械画面，给出一句理由。
3. 3–5 篇可以合法提取图片的公众号文章链接，或对应 HTML+图片导出包。
4. 每一组说明作者/来源、能否在本地使用、可否上传外部模型、可否训练/公开。**不确定就标 unknown**。
5. 可选的 Krita KRA 和真实绘制过程示范，另行核实该数据是否属于你。

本地 Agent 先在 `private-references/` 做小批量 dry-run、生成目录和抽查缩略图；未经用户同意不扫描整机文件夹、下载整站内容、上传模型或提交 GitHub。
