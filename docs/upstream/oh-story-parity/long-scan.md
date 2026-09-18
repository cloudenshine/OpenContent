# Oh Story Parity Audit: Long-Scan (长篇扫榜)

## 1. 上游能力与定位
- **上游 Skill**: `skills/story-long-scan`
- **上游版本**: `1.0.0`
- **定位**: 网络小说市场分析师。采集并分析起点、番茄、七猫、晋江等主流长篇网文平台榜单，提炼真实市场趋势与题材候选。
- **核心理念**: 单本排名只提供线索，跨样本重复模式才算信号。榜单数据是事实证据，模型做归纳分析，严禁凭空编造热门数据。

---

## 2. 处置方案矩阵

| 上游能力 / 逻辑 | 处置 | OpenContent 架构落地说明 |
|---|---|---|
| **真实榜单抓取脚本 (`qidian-rank-scraper.js`, `fanqie-rank-scraper.js`, 等)** | **ADAPT** | 适配为本地 Python/Node 爬取器，优先采用移动端/公开接口 JSON 数据，回退至 CDP；抓取结果以标准 JSON/Markdown 保存至 Vault `Market/Long/`。 |
| **数据清洗与简介脱敏 (`cdp-utils.js`)** | **REUSE** | 剔除榜单推广水军、简介营销词、无意义排版乱码，保留标准字段：排名、书名、作者、题材、状态、字数、推荐数、简介。 |
| **样本数量与质量门禁** | **REIMPLEMENT** | OpenContent 强制门禁：有效样本数未达到门限（如每平台少于 10 本有效数据）时，标记 `INSUFFICIENT_DATA`，禁止直接生成题材结论。 |
| **流量型 vs 付费型跨平台差异分析** | **PROFILE** | 起点（订阅/追读/世界观创新）与番茄/七猫（完读/快节奏/爽点前置）分层分析，写入 `MarketRun` 分析报告。 |
| **Oh Story 全局安装与 Shell 依赖** | **REJECT** | 不要求用户在全局装 shell 脚本或全局 npm 包；通过 OpenContent 内核统一任务调度。 |

---

## 3. 输入输出契约

- **输入**:
  ```json
  {
    "task": "long-scan",
    "platforms": ["qidian", "fanqie", "jjwxc"],
    "rank_types": ["hotsales", "yuepiao", "newsign"],
    "sample_limit": 20
  }
  ```
- **输出**:
  - `MarketRun` (保存于 `OpenContent/Market/Long/{run_id}.md`)
  - `raw_snapshot.json` (不可变原始抓取数据)
  - `normalized_records.json` (清洗后统一数据结构)
  - `analysis.md` (3 个经数据印证的候选创作方向及风险分析)
