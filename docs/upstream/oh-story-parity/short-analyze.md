# Oh Story Parity Audit: Short-Analyze (短篇爆款拆文)

## 1. 上游能力与定位
- **上游 Skill**: `skills/story-short-analyze`
- **上游版本**: `3.1.0`
- **定位**: 短篇小说结构分析师。拆解知乎盐言、番茄短篇、故事会等爆款短篇的故事核、情绪线、反转节奏与共鸣层次。
- **核心理念**: 短篇靠共鸣和爆点驱动。拆文就是看它用什么故事核、怎么铺垫、在哪里引爆。产出必须直接服务于下游创作。

---

## 2. 处置方案矩阵

| 上游能力 / 逻辑 | 处置 | OpenContent 架构落地说明 |
|---|---|---|
| **分阶段拆解流水线 (Stage 2-6)** | **REUSE** | 严格保留五大拆解阶段：<br>Stage 2: 结构与情节节点清单<br>Stage 3: 情感线与爆点节奏<br>Stage 4: 反转设计与写作手法<br>Stage 5: 人物设定与开篇/结尾钩子<br>Stage 6: 综合评估与机制提炼。 |
| **Stage 完成标记与崩溃恢复机制** | **REIMPLEMENT** | 在 `.opencontent/runs/<run_id>/stages/` 记录检查点，单步失败可断点续拆，不推倒重来。 |
| **输出多维结构与 `_meta.json` 统计** | **ADAPT** | 将 `_meta.json` 与 Markdown 拆文报告转化为 OpenContent 的 Markdown 真源，并在 Vault 中建立 `OpenContent/Deconstruction/{title}/`。 |
| **机制抽取 (Mechanism Extraction)** | **ENHANCED** | 提炼短篇独特机制卡（如信息差回溯、双重伪装揭露、道德审判反转），附带“作用/适用/风险”四元组。 |
| **强行绑定专属写小说命令** | **REJECT** | 拆解出的机制卡进入全局机制库，任何新项目均可通过 Context Assembler 自由调用。 |

---

## 3. 输出资产树

```text
OpenContent/Deconstruction/{作品名}/
├── 原文备份.md
├── 拆文报告.md
├── 情节节点.md
├── 写作手法.md
├── 机制卡片/
│   ├── 机制_01.md
│   └── 机制_02.md
└── meta.json
```
