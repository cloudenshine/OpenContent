# Oh Story High-Fidelity Capability Parity Report
## OpenContent Creative Capability Pack (Narrative Pack v1)

本报告详细记录 OpenContent Narrative Pack v1 与上游参考实现 Oh Story (`zenstory-ai/oh-story-claudecode`) 的高保真能力对齐、复现结果、增强项与架构归属。

---

## 一、核心能力对齐总表 (Parity Matrix)

| 生产能力 | Oh Story 原版实现 | OpenContent Narrative Pack | 状态 | 实测案例与证据支持 |
|---|---|---|---|---|
| **长篇真实扫榜** | `story-long-scan` 脚本抓取起点/番茄/七猫等榜单 | `market.long_scan` (`LongMarketAnalyzer`) 真实榜单摄入与归一化 | **PARITY** | `tests/test_parity_pipeline.py::test_long_market_scan_parity`，生成 `MarketRunLong` 资产 |
| **长篇数据清洗** | `cdp-utils.js` 正则清洗简介与异常过滤 | `market.py:clean_intro` + `normalize_record` 自动剔除简介营销与异常字段 | **PARITY** | 异常数据自动阻断与脱敏，字段标准化测试全绿 |
| **短篇扫榜** | `story-short-scan` 独立分析知乎/点众情绪风口 | `market.short_scan` (`ShortMarketAnalyzer`) 独立情绪与完读模型 | **PARITY** | `tests/test_parity_pipeline.py::test_short_market_scan_parity`，输出 30-60 天趋势时效 |
| **长篇拆文** | `story-long-analyze` 黄金三章 + 逐章演进 | `deconstruct.long` (`StoryDeconstructor.deconstruct_long`) | **PARITY** | `tests/test_parity_pipeline.py::test_long_and_short_deconstruction_parity`，深度拆解黄金三章 |
| **短篇拆文** | `story-short-analyze` 5 阶段分析管道 | `deconstruct.short` (`StoryDeconstructor.deconstruct_short`) | **PARITY** | 生成情节节点.md、写作手法.md、拆文报告.md |
| **机制抽取** | 部分提取，缺乏统一卡片规范 | **三层资产模型**：Source Analysis → Mechanism Cards → Reusable Insights | **ENHANCED** | 提炼标准机制四元组（名称/作用/场景/风险/抽象），落盘于 `机制卡片/` |
| **连续创作** | 基于会话的单章/连续写作 | `create.continue` 显式继承上一章结尾状态与伏笔，不依赖脆弱聊天记忆 | **PARITY** | `packs/narrative/workflows/continue.yaml` |
| **上下文装配** | 按模板拼装大段 prompt | `ContextAssembler` P0/P1/P2 分级预算与解释性溯源 | **ADAPTED** | `opencontent/capabilities/context.py`，杜绝整库盲目倾倒 |
| **独立审查** | `story-review` 独立角色审读 | `quality.critique` 独立多轴审计（严重度/位置/问题/修改建议） | **PARITY** | `packs/narrative/workflows/critique.yaml` |
| **正式版本治理** | 无，依赖普通 Markdown 文件 | **Kernel 事务保护**、上下文哈希校验、人工批准与防篡改 | **OPENCONTENT** | `opencontent/kernel.py`，机器无法自批，改动即失效 |
| **封面生成** | `story-cover` 绑定特定图生图接口 | `presentation.cover`（`CoverDirector` ↔ `MediaGenerationAdapter` 解耦） | **PARITY** | `opencontent/capabilities/media.py`，生成多比例规格与候选图片 |
| **桌面工作台** | 命令行 CLI 交互 | **Obsidian 原生右侧栏工作台**，一键可视化操作五阶段生产链 | **OPENCONTENT** | `plugin/main.js`，通过 CDP 在运行中 Obsidian 实测通过 |

---

## 二、关键分项深度对比与证据

### 1. 市场情报 (Market Intelligence)
- **Oh Story 现状**：长短篇采用两个独立 Skill，分别处理订阅型长篇和情绪型短篇。
- **OpenContent 落地**：
  - 拒绝粗暴合并为 `generic_scan()`，在 `opencontent/capabilities/market.py` 中设立独立的 `LongMarketAnalyzer` 与 `ShortMarketAnalyzer`；
  - **长篇扫榜**：强制有效样本门限（>=3 条有效书籍），自动提取高频题材与交叉热词，产出 3 个带商业逻辑和风险提示的创作方向；
  - **短篇扫榜**：重点提炼情绪触发点（如“不公压抑 → 决绝离开 → 全员悔恨”）与反转类型，并在报告中显式标注 `shelf_life_days: 30-60` 及建议复扫日期；
  - **证据**：`OpenContent/Market/Long/` 与 `OpenContent/Market/Short/` 生成标准资产文件。

### 2. 爆款拆文与机制卡库 (Story Deconstruction)
- **Oh Story 现状**：产物直接输出在 `拆文库/{书名}/`，部分内容停留在对特定剧情的复述。
- **OpenContent 落地**：
  - 严格落实**三层资产架构**（Source Analysis → Mechanism Cards → Reusable Creative Insights）；
  - 抽象出“机制名称、功能机制、适用场景、避坑风险、原创迁移抽象”五要素卡片（如《预置不可调和的制度与身份困境》、《现实物证降维打击》）；
  - 任何新项目在创作时均可通过 Context Assembler 引用这些机制卡，做到“学机制而不抄剧情”；
  - **证据**：`tests/test_parity_pipeline.py` 实测生成 `OpenContent/Deconstruction/{title}/机制卡片/*.md`，并在 Obsidian 前端提供「🎴 机制卡库」一键检索抽屉。

### 3. 表现层封面体系 (Presentation & Cover)
- **Oh Story 现状**：在 Skill 内直接用 curl 或固定环境变量调用远端图像模型。
- **OpenContent 落地**：
  - 实施**两层解耦**：`Narrative Pack (Cover Director)` 负责题材视觉语义分析（科幻、悬疑、仙侠、都市）与目标平台规格比例（番茄 3:4, 起点 2:3, 知乎 16:9）；`MediaGenerationAdapter` 负责在本地 Vault `Attachments/OpenContent/{project}/covers/` 下安全保存多版本候选图片（`cover-v1.png`, `cover-v2.png`）；
  - 支持本地无网络图片占位与 Codex 内置图像工具直连；
  - **证据**：`tests/test_parity_pipeline.py::test_cover_director_and_generation_parity` 生成有效图像资产。

### 4. 连续创作与多产物支持 (Multi-Artifact & Continuity)
- **Oh Story 现状**：依靠多文件组织连续写作。
- **OpenContent 落地**：
  - 彻底解除了之前 OpenContent 每项目单 Artifact 的限制；
  - 支持单项目容纳多章节（第一章、第二章……），各章节版本独立、审查记录独立、定稿状态独立；
  - 在前端写作页提供便捷的「📖 章节/稿件切换」下拉框与章节编号标注；
  - **证据**：`tests/test_multi_artifact.py` 严格验证第一章定稿批准后第二章保持未批准，且支持独立审读。

---

## 三、结论

OpenContent Narrative Pack v1 已经完全具备 Oh Story 上游的核心生产力，并在**架构解耦、机制资产化、上下文装配精细度、版本安全治理以及桌面 GUI 交互**上实现了全面超越。从“市场扫榜 → 爆款拆解 → 机制提炼 → 连续写作 → 质量审查 → 封面装帧”的完整生产链已全面贯通。
