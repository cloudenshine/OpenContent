# Oh Story Parity Audit: Long-Analyze (长篇爆款拆文)

## 1. 上游能力与定位
- **上游 Skill**: `skills/story-long-analyze`
- **上游版本**: `1.0.0`
- **定位**: 网络小说结构分析师。深度拆解爆款长篇小说的黄金三章、人设架构、爽点节拍与底层机制。
- **核心理念**: 看懂别人的爆款，才能写出自己的爆款。拆解必须抽象出**创作机制（Mechanism）**，坚决禁止将具体剧情套路直接当成复用模板。

---

## 2. 处置方案矩阵

| 上游能力 / 逻辑 | 处置 | OpenContent 架构落地说明 |
|---|---|---|
| **黄金三章深度拆解 (Stage 1)** | **REUSE** | 提取开篇钩子、核心危机、读者契约、前三章推进速度，产出 Stage 1 快速速览报告。 |
| **多阶段渐进管道 (Stage 2-6)** | **ADAPT** | 支持逐章摘要、人物关系网络、爽点/期待管理链条拆解；支持断点续跑与异常恢复。 |
| **只读文学批评与合法边界声明** | **REUSE** | 严格遵循只读的转化性文学分析原则，提取结构机制而非侵犯原文表达。 |
| **三层产物模型 (3-Tier Asset Model)** | **ENHANCED** | 升级上游单一报告为三层资产：<br>1. **Source Analysis** (逐章/整体分析)<br>2. **Mechanism Cards** (机制/作用/适用/风险卡片)<br>3. **Reusable Creative Insights** (当前新项目可直接调用的机制资产)。 |
| **Oh Story 专属 .story-deployed 目录与 Agent 派生规则** | **REJECT** | 统一由 OpenContent Kernel 与 Capability Runtime 调度，不创建平行的 Agent 注册文件。 |

---

## 3. 机制卡规范 (Mechanism Card Contract)

所有长篇拆文必须提炼标准机制卡，格式如下：

```yaml
id: mech_01
name: 预设证据的公开认知翻转
function: 积累不公感与压抑情绪 → 建立强期待 → 瞬间释放
application: 身份差 / 误解消除 / 价值反转 / 逆转打脸
risk: 若证据事先未曾埋设，会退化为机械降神或突兀打脸
abstraction: >
  先让主角或关键角色因外界的错误认知付出被动或公开的代价，
  并在关键节点亮出此前已被读者获知但被剧中人忽略的既有物证，
  实现剧情与情绪的剧烈翻转。
```
