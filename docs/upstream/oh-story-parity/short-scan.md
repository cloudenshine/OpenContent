# Oh Story Parity Audit: Short-Scan (短篇扫榜)

## 1. 上游能力与定位
- **上游 Skill**: `skills/story-short-scan`
- **上游版本**: `1.0.0`
- **定位**: 短篇网文市场分析师。捕捉知乎盐选、点众、黑岩、七猫短篇等平台的爆款趋势。
- **核心理念**: 短篇市场是“情绪市场与传播市场”。题材生命力取决于单篇完读率与社交转发，风口周期短（数周内可能饱和），必须独立建构分析模型，**严禁与长篇扫榜合并为通用泛化模型**。

---

## 2. 处置方案矩阵

| 上游能力 / 逻辑 | 处置 | OpenContent 架构落地说明 |
|---|---|---|
| **短篇榜单抓取 (`dz-browse-scraper.js`, `heiyan-booklist-scraper.js`)** | **ADAPT** | 适配抓取知乎故事专栏、点众、黑岩等短篇热榜数据，抽取点赞、完读预估、字数分布（5k-2w 字中位数）。 |
| **情绪钩子与爆点提取算法** | **REUSE** | 提取核心情绪交付类型（虐恋极致、逆风翻盘、认知反转、道德审判），以及触发场景。 |
| **风口时效性与饱和度警告** | **REIMPLEMENT** | 输出必须强制附带：`sample_date`、`validity_window`（如 30 天）、`saturation_risk`（高/中/低）以及推荐复扫日期。 |
| **跨平台短篇写作差异规范 (`real-market-data.md`)** | **PROFILE** | 转化为 `Narrative Pack` 的短篇参考规范，涵盖知乎、七猫、点众的人称、章节字数、反转节奏要求。 |
| **泛化合并为单一扫榜函数** | **REJECT** | 坚决拒绝 `generic_scan()` 方案；保留独立的 `ShortMarketAnalyzer`。 |

---

## 3. 输入输出契约

- **输入**:
  ```json
  {
    "task": "short-scan",
    "platforms": ["zhihu", "dz", "heiyan"],
    "focus": "emotion_and_virality"
  }
  ```
- **输出**:
  - `ShortMarketRun` (保存于 `OpenContent/Market/Short/{run_id}.md`)
  - 情绪图谱与爆点分布清单
  - 3 个具有完读保证与反转预期的短篇选题建议
  - 趋势时效与复查截止日期
