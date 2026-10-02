# OpenContent 写作质量层 1.0.2

## 采用什么，为什么

顺序是读者用途 → 材料特有的观察与判断/叙事变化 → 证据/连续性检查 → 最后语言精修。原有 `editorial.py` 简洁核心保持不变。

- `substance.md`：基于 alchaincyf/huashu-report 的研究深度与行文原则，保留读者用途、事实/解释区分、可比较口径、竞争解释与结论边界。1.0.2 补充具体判断的后果、真正约束结论的反问、有实际用途的细节；仅在体裁需要时表态，教程、介绍、旁白不强制变成评论。
- `voice.md`：基于 op7418/Humanizer-zh 的语义保护、声线校准和有限改写。只做末轮精修，不用禁词表、句长配额或检测器分数判稿，不把有内容的个性磨成统一的稳妥说明。
- `fiction.md`：在原小说连续性要求上采用 oh-story-claudecode scene-craft 的场景信息与疏密原则。1.0.2 强调人物各自的需要、细节对关系/行动的作用、由处境产生的情绪。允许平静、和谐、幽默，不强制尴尬、冲突、反转、感动或某类结尾。

三份上游的精确仓库、commit、文件 URL、SHA256、MIT 许可在 `manifest.json` 与 `upstream/*/LICENSE`。中文模块是 OpenContent 的有限改编，不是原样安装。Humanizer 原完整技能只供审查，运行时不加载整篇。huashu/oh-story 含第三方引用示例，未再分发这些例子，只记录固定来源与哈希。1.0.2 新增的本地编辑判断与合成范文不是上游原文。

## 真正运行在哪里

`opencontent.writing_quality.attach_writing_policy` 把当前任务用到的短模块直接加入请求 `instructions`：

1. 通用文章：`Kernel.request` 的 draft / critique
2. 工作台：`workbench.request` 的 revise
3. Narrative：plan / write / continue / revise / critique；`general-fiction`、`serial-fiction` 用虚构模块，`narrative-nonfiction` 用证据约束模块

plan 不加载末轮精修；critique 只审阅；定向 revise 保留未要求改动的内容。研究、蒸馏、讨论、生图、扫榜、拆文不注入此层。通用文章/工作台仍按证据写作处理；明确授权的虚构散文应选 Narrative 虚构 Profile，而不是借“散文”名义在非虚构中补造经历。

Codex/Claude 沿用 JSON 请求协议。没有新增服务、账号、费用、凭据、联网研究或自动发表。现有 Claim 原句、引用、数据、链接、代码和定向改稿范围不因写作规则放宽。

## 范文按需参考，默认不进提示

`references/` 中两份文件已随插件打包，按 `manifest.json.reference_resources` 的体裁、任务与哈希定位：

- `fiction-observation.md`：虚构散文的首轮两稿、问题解释、后续认可重写《别太大》与迁移边界。用于明确授权虚构的写作/续写/审稿
- `evidence-judgment.md`：分析评论的首轮两稿、问题解释、后续认可重写《谁来发现它没做完》与迁移边界。用于确需判断的评论，不套给所有说明文

先阅读与任务相符的一份，比较“这个细节/判断在此处做了什么”，再在新材料里寻找其自身理由。默认程序不读取这些全文，不以文件存在声称模型已经看过。需要让写作者参考时，由作者明确选取适用段落放进本次参考材料/写作指令；材料仍是待参考数据，不授予工具权限，也不把范文的数字、立场或经历移植到新稿。没有新增 UI 开关或隐式自动检索。定向改稿只参考授权修改范围内的方法。全文复制进 prompt 会增加上下文且可能诱发模仿，因此不推荐常驻加载。

范文是本地合成测试创作；后续两篇得到用户认可，只证明这两篇符合本次判断。初轮六类稿件的完整证据在源码 `docs/writing-quality-evidence/v1.0.2/prior-six-*.json`，保留不占优结果。既不把单篇认可当普遍质量证明，也不将不喜欢的一稿变成句式黑名单。

## 可核查性和验证边界

请求 `writing_quality.sha256` 是当前任务所用补充模块及任务范围句的 SHA256；`prompt_sha256` 是 `instructions` 与 `editorial_guidance` 两字段规范 JSON 的哈希，不含 constitution、对象、schema、skills，不能叫完整请求哈希。完整请求在已有 request/agent-request 文件保存；评测清单另存整份请求的规范 JSON 哈希。

Narrative receipt、通用任务 attempt 保留同一 writing_quality 元数据。版本与哈希证明装配了什么，不证明模型遵守了它。离线测试捕获真实入口请求、模拟 Codex/Claude stdin、核对 schema/范围、来源与参考文件哈希、脱离仓库后的安装资源。夹具输出不是质量样本；真人认可的重写、独立模型迁移试写、真实本地 CLI 端到端验收分别记录，不互相替代。
