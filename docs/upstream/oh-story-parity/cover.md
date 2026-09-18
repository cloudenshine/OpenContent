# Oh Story Parity Audit: Cover (封面生成)

## 1. 上游能力与定位
- **上游 Skill**: `skills/story-cover`
- **上游版本**: `1.0.0`
- **定位**: 小说封面设计师。根据书名、简介与题材自动识别视觉风格，构建高质感构图提示词，调用图像模型一次性生成包含标题与署名的成型封面。
- **核心理念**: 封面是读者的第一印象，一眼传达题材与氛围。但封面生成必须独立于正文创作，属于 Presentation 表现层能力。

---

## 2. 处置方案矩阵

| 上游能力 / 逻辑 | 处置 | OpenContent 架构落地说明 |
|---|---|---|
| **平台特有视觉风格映射 (`cover-styles.md`)** | **PROFILE** | 提取番茄（高饱和人物居中）、起点（电影质感与沉稳插画）、晋江（唯美柔光大眼）、知乎（极简留白与氛围感）、七猫（强冲击海报）等五大平台视觉语义库。 |
| **题材视觉语义与构图分析** | **REUSE** | 根据书名、主角身份与故事核自动匹配色彩调性、光影模式与前景/后景构图比例。 |
| **平台多规格尺寸适配 (3:4, 2:3, 16:9)** | **ADAPT** | 规范目标尺寸：番茄 3:4 (`768x1024` / `600x800`)、起点/晋江 2:3 (`1024x1536` / `600x900`)、知乎 16:9 / 1:1，提供标准居中裁切。 |
| **多版本不覆盖与封面决策** | **REIMPLEMENT** | 每次生成保留为 `cover-v1.png`, `cover-v2.png`，在写作/发布页面提供并排对比选择，经用户明确点选后才成为正式封面。 |
| **架构解耦 (Cover Director ↔ Media Generation Adapter)** | **REIMPLEMENT** | 彻底解耦！Narrative Pack 只实现 `CoverDirector`（负责视觉语义与提示词）；底层的图片生成由 `MediaGenerationAdapter` 对接本地 Codex 图片工具、DALL-E 或本地模型，不把某家特定 API 绑死在叙事包内。 |
| **硬编码依赖 OpenAI API Key 或外部中转 curl** | **REJECT** | 优先利用本地 Codex CLI 已授权的内置图像能力；缺失时明确报告能力缺失，不擅自向外部计费接口发送请求。 |

---

## 3. 分层架构示意

```text
Narrative Pack (Cover Director)
        ↓  (视觉风格 / 构图 / 标题 / 平台比例)
Media Generation Adapter
        ↓  (本地 Codex CLI 图像工具 / 外部图片渠道)
Vault 附件目录 (Attachments/OpenContent/{project}/covers/cover-v{n}.png)
        ↓
人类最终定稿点选
```
