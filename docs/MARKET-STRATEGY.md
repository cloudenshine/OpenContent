# OpenContent：Obsidian 市场判断与 v0.3 产品决策

> 2026-09-08 后续纠偏：本报告遗漏 Gemini Notebook 与 Open Notebook，并将批准稿交接过度收窄为产品终点。请先读 [Notebook 竞争与全流程决策修正](NOTEBOOK-COMPETITION-AND-FULL-LIFECYCLE.md)。以下 v0.3 实施事实仍有效；有关长期定位和发布反馈优先级，以后续修正为准。

研究日期：2026-09-08。对象是当前工作区项目及其 Implementation Charter。本报告区分**公开事实、代码观察、产品推断和待验证假设**；没有把下载量当活跃用户，也没有声称做过用户访谈或竞品运行性能实测。

## 1. 判断：保留章程的内核，改变用户入口

认可章程将状态、来源、编辑规则与最终判断留给 OpenContent，将执行交给外部 Agent 的方向。需要调整的是市场表达与产品优先级：“内容生产操作系统”适合作为内部架构目标，初次使用者更需要看到“从已有笔记写出有出处、可复核的文章”。九类对象、十个状态不应成为首次使用前的学习成本。

**建议定位：面向定期产出教程、研究说明和知识通讯的 Obsidian 作者，提供从材料到成稿的编辑质量工作流。** 当前可争取的差异是主张与证据的关系、来源变更后的审查失效、需要人判断的队列，以及批准稿的可移交性。它是组合能力与持续使用体验的机会，尚不是被市场证实的护城河。

不要将 Agent、Projects、Skills、本地存储或“有门禁”当独占优势。Copilot 已覆盖多种 Agent 和项目化工作；Ailu 已实现相当具体的发布前确认与版本校验。重复实现通用聊天、全库检索、模型设置和每个平台上传器，会消耗维护能力而难以形成首选理由。[Copilot 官方说明](https://github.com/logancyang/obsidian-copilot)、[Ailu 官方说明](https://github.com/mcncarl/ailu)。

## 2. 市场证据及其边界

本地留存的 [机器可读快照](market-evidence/market-snapshot.json) 采集于 2026-09-08 10:08:57 UTC，包括请求来源。官方 GitHub 社区插件注册表在这一快照有 **7,410 条记录**；这只是条目数，不是去重后的在售市场规模。选取以下相邻产品研究，是因为它们分别占据捕获、检索、生成、写作组织和交付入口，并非下载榜的完整统计。[注册表](https://github.com/obsidianmd/obsidian-releases/blob/master/community-plugins.json)、[下载统计](https://github.com/obsidianmd/obsidian-releases/blob/master/community-plugin-stats.json)。

| 插件 | 快照中累计 downloads | 对 OpenContent 的意义（推断） |
|---|---:|---|
| Templater | 5,536,902 | 原生模板和小动作已经有强入口 |
| QuickAdd | 2,085,877 | 捕获要顺手，用户不愿先切换到一个复杂系统 |
| Copilot | 1,839,057 | 通用 AI 工作台竞争已有规模 |
| Smart Connections | 1,190,927 | 相关笔记发现本身就有清晰价值 |
| Text Generator | 579,299 | “生成文字”不是空白市场 |
| Longform | 183,084 | 项目、草稿、编译组织也已有产品 |
| Smart Composer | 171,994 | 上下文编辑与快速采用修改是直接替代品 |

downloads 包含历次版本下载，不能换算为独立安装、付费人数、周活、留存或我们的可得市场。Ailu 在同时点为 111 stars、15 forks；它和 OpenContent 的 id 未出现在该注册表快照中，不代表无人使用或不能手动安装。GitHub `open_issues_count` 混合 issue 与 PR，不据此评价缺陷数量。没有足够证据给出 TAM、收入预测或竞品留存率。

一位论坛用户在 2025-07-25 提到使用相关 AI 插件时卡顿并卸载。这是历史个案，只用于提醒我们验证编辑器干扰和资源成本，不能用于判定当前版本性能或声称 OpenContent 更快。[论坛原帖](https://forum.obsidian.md/t/llm-integration/103249)。

## 3. 竞争不止来自 AI 插件

| 用户正在完成的工作 | 现有选择及官方证据 | OpenContent 应采取的关系 |
|---|---|---|
| 随手捕获与复用格式 | [QuickAdd](https://quickadd.obsidian.guide/docs/)、[Templater](https://silentvoid13.github.io/Templater/) | 兼容原生 Markdown、命令、选区；不再造快捷捕获生态 |
| 保存网页资料 | [Obsidian Web Clipper](https://obsidian.md/help/web-clipper) | 接收笔记正文与 `source` 属性；保存快照，不自动抓取全网 |
| 展示文件及属性 | [Obsidian Bases](https://obsidian.md/help/bases) | 数据维持为文件；我们的视图重点解释判断与依赖 |
| 发现相关笔记 | [Smart Connections](https://github.com/brianpetro/obsidian-smart-connections) | 可先在已有工具发现，再显式捕获；不在本版建设向量索引 |
| 聊天、选区问答、Agent 项目 | [Copilot](https://docs.obsidiancopilot.com/) | 避免以通用聊天替代作者的现有选择 |
| 上下文写作与模板生成 | [Smart Composer](https://community.obsidian.md/plugins/smart-composer)、[Text Generator](https://community.obsidian.md/plugins/obsidian-textgenerator-plugin) | 必须用证据与审查的实际收益解释额外流程成本 |
| 长文项目、场景、草稿编译 | [Longform](https://github.com/kevboh/longform) | 不向所有长文作者兜售事实审查链；小说不是当前主目标 |
| Agent 编辑与多平台交付 | [Ailu](https://github.com/mcncarl/ailu) | 在批准稿与平台交付之间形成普通 Markdown 接口 |
| 不装插件 | 原生 Markdown、属性、Bases，加外部 Agent | 这是重要基线：我们必须比手工核对更省事，不能仅仅“更有架构” |

Smart Connections 官方主张本地嵌入和隐私优势，本文未复测其效果。Smart Composer README 的维护状态只反映该作者声明，不外推为整个生态缺乏维护。对不同需求，用户完全可能合理地选择这些工具而不需要 OpenContent。

## 4. Ailu 需要认真学习什么

观察固定在提交 [`8a232fe082163c5898038cca7bcf26cb1956b9a2`](https://github.com/mcncarl/ailu/tree/8a232fe082163c5898038cca7bcf26cb1956b9a2)。阅读 README、目录树及 10 个模块/文件；URL 与 SHA-256 留在 [审计清单](market-evidence/ailu-audit-manifest.json)。没有运行 Ailu、调用发布服务或执行其代码。

| 方面 | 已查证的公开能力或代码观察 | 对我们的判断 |
|---|---|---|
| 编辑入口 | 选区/当前行改写及采用修改的交互 | 价值在作者正在写的地方出现，比先建对象更自然。[inlineEdit.ts](https://github.com/mcncarl/ailu/blob/8a232fe082163c5898038cca7bcf26cb1956b9a2/src/ui/inlineEdit.ts) |
| 运行环境 | 配置路径、PATH、桌面 Codex 与托管运行时的发现方式；状态缓存 | 安装与连接也是产品。我们的目录表单只是改善提示，尚未达到自动发现能力。[discovery.ts](https://github.com/mcncarl/ailu/blob/8a232fe082163c5898038cca7bcf26cb1956b9a2/src/runtime/discovery.ts) |
| 发布安全 | guard 对比内容哈希、源文件版本、主题、准备结果、预检和目的地身份等状态 | “我们有版本门禁，Ailu 没有”是错误定位。它保护发布事务，我们重点保护编辑论证链。[publicationGuard.ts](https://github.com/mcncarl/ailu/blob/8a232fe082163c5898038cca7bcf26cb1956b9a2/src/publishing/publicationGuard.ts) |
| 工作覆盖 | Claude/Codex、聊天、微信/飞书/X Article 相关预览与交付能力；细节依各通道而异 | 平台完成度是 Ailu 的优势；本项目新交接只是本地 Markdown 输出。[官方 README](https://github.com/mcncarl/ailu) |
| 平台限制 | 当前 README 明示 Windows 的写入相关能力 fail closed；写流程验证集中在 macOS/POSIX。锁模块默认依赖 `/usr/bin/python3` | 我们有 Windows 实机运行证据，可作为首批支持环境；对方未来补齐后此差距会消失。[processWriteLock.ts](https://github.com/mcncarl/ailu/blob/8a232fe082163c5898038cca7bcf26cb1956b9a2/src/storage/processWriteLock.ts) |

在已读类型、目录和相关模块中，未发现与本项目九类领域对象和编辑论证关系相同的实现；这不等于穷尽整个 Ailu 产品，更不等于对方不能加入。不同门禁解决的问题不同，双方可重叠也可互补。

本次是独立实现。Ailu 仓库标注 AGPL-3.0，研究副本保留其 LICENSE 并被排除于 OpenContent 发布包；没有把上游代码混入 MIT 源码。可选外部发布组件还可能有各自许可，实施直接集成前需逐项核对。[Ailu LICENSE](https://github.com/mcncarl/ailu/blob/8a232fe082163c5898038cca7bcf26cb1956b9a2/LICENSE)。

## 5. 优劣势与适合争取的用户

**现有优势，有本地工程证据：** Markdown/YAML 可独立读取；Agent 响应不能直接替用户批准；引用须匹配捕获材料；来源、草稿与规则变更能使旧判断失效；Windows 原生 Obsidian + Codex 流程已跑通。v0.3 新入口把这些能力接回日常笔记，而不是要求手工建立九种对象。

**主要劣势：** Python、Kernel 与可选 CLI 带来安装负担；目前仅一个真实 Provider，跨平台、移动端、同步多设备写入未经完整支持；关系 ID 与结构化属性对手工维护者不友好；批判式编辑多出时间和模型费用；没有社区分发、真实留存或付费意愿证据。精确引文并不证明语义蕴含、来源可靠性或原创性，五轴 PASS 也不应作为自动质量保证。

**机会（假设）：** 经常从多份资料产出中文说明文的人，可能愿意为减少漏引、过期依据、重复审稿而保留这个工作流。长期可积累的价值是自己的材料、编辑判断与修订记录，而不是换模型后的短期生成差异。

**威胁（推断）：** Copilot/Ailu 可加入类似审查功能；原生 Bases 继续改善文件组织；插件维护成本与 Agent API 变化增加支持负担；用户可能认为门禁的误报比其收益更大。开源代码可复制，不能将字段设计视为商业壁垒。

| 用户情境 | 建议 |
|---|---|
| 每周/双周写教程、研究说明、通讯，资料多且常修订 | 首批目标；以一篇真实文章验证收益 |
| 多次使用同一来源，需知道哪些旧稿受影响 | 后续重点；当前有逐稿重检，跨项目影响面与复用 UX 尚待建设 |
| 只想向全库提问或快速润色一段话 | Copilot/Smart Connections/现有编辑工具通常更直接 |
| 首要诉求是微信、飞书、X 的排版上传 | 优先研究 Ailu 的受支持环境与通道 |
| 日记、小说、纯手机使用、期待零依赖安装 | 当前不是合适首批用户，不强行套证据流程 |

## 6. 已实施的 v0.3 决策

| 用户阻力 | 本次实施 | 验收含义与限制 |
|---|---|---|
| 离正在写的笔记太远 | 命令、编辑器菜单、文件菜单捕获；选区优先；可直接建项目 | 不调用模型、不改写源笔记；全文捕获移除前置属性，保留 `source` URL |
| 重复捕获增加整理成本 | 同项目、同来源、相同正文与来源 URL 去重 | 重复无新对象；内容改变保存新快照；不跨项目偷偷合并 |
| 首页像管理后台 | “继续工作”队列、优先待判断、记住上次项目、阶段总览折叠 | 以明确下一步替代首次面对八个空栏目 |
| 不清楚会发送什么 | 启动、重审、重试前预览材料/规则并说明关联对象与配置 Skills | 预览 token 与首个排队请求绑定；资料改变则发送前拒绝 |
| 批准后工作断开 | 本地 `OpenContent-Exports/` Markdown 与交接收据 | 主张标记转脚注，现有文件被人修改后拒绝覆盖；不上传、不自动进入 PUBLISHED |
| 后台干扰写作 | 无任务且无内容事件时停止 Board 轮询；解析按文件字节哈希缓存；合并重叠渲染 | 仍读取领域文件字节核对变化；不是大型 Vault 性能保证 |
| 初次连接难找入口 | 首屏配置连接、Python/目录/Codex 说明、保存后健康检查 | 依赖仍需用户安装；未伪称一键自动配置 |

交接文件是普通 Markdown，可交给 Ailu 或其他工具打开；**未验证 Ailu 的实际导入、排版或远程发表**。本版为减少附带 URL 查询凭据会去掉查询串和片段，依赖 query 定位的来源可能需要作者在交付前补正。正文中作者自行写入的敏感信息也需自行检查。完整证据仍保存在项目内。

材料与关系的发送范围是应用构造请求的范围。Provider 的 read-only sandbox 与提示并不构成“禁止读取所有其他文件”的强操作系统隔离；机密材料应依据所选 Agent 的数据政策决定是否发送。这是当前能力边界。

实现证据与测试细节见 [v0.3 验收](VALIDATION-v0.3.md)，不是用户市场验证结果。

## 7. 下一阶段如何进化：条件、取舍、停止规则

以下是执行顺序与建议验收条件，**不是已完成清单或确定工期承诺**。估算以一位维护者为假设，需以试点暴露的问题调整。

| 阶段 | 可交付工作 | 启动与验收条件 | 暂不投入 |
|---|---|---|---|
| 现在：v0.3 可试用版 | 本文上述入口、队列、交接、回归证据；4 周试点材料 | 新旧门禁均通过；源笔记不损坏；失败可诊断 | 通用聊天、全库自动上传、遥测服务 |
| 试点后 1–2 个迭代（每轮约 1–2 周，估算） | 优先解决实际安装失败；测试后决定可选打包运行时、发现 CLI；优化误阻拦说明 | ≥3 位目标用户在同一环节失败才认定共性，不按一条抱怨扩架构；不得为降低误报绕过人批准 | 多 Provider 同时铺开 |
| 工作流有复用证据后 | 来源更新→受影响稿件视图；让用户选择重新捕获与重审；记录修改原因 | 两个真实项目出现跨稿复用需求；旧结论失效、人工修正、再次交付形成可追踪测试 | 自动将新来源当真相、全库后台改写 |
| 价值信号成立后 | 自愿记录发表链接、反馈摘录与下次规则建议；规则变更由人确认 | 记录的是实际反馈；建议能回溯到样本；不把点击量直接当质量 | 自动增长运营、跨平台自动发布 |
| 分发准备 | 公开源码、README/隐私说明/支持环境、正式 Release 资产、官方规范检查，再提交社区目录 | 依赖成本透明；最低版本有实测；许可和失败恢复说明齐全 | 未评审即声称“官方上架” |

若用户只使用捕获而持续绕开审查，需验证审查是否太重或目标用户选错；先精简呈现和审查解释，不把门禁默认为通过。若两轮试点仍不能体现少返工或更容易核对来源，应收窄为证据审查插件或暂停扩张，而不是用更多 Agent 掩盖价值不足。

官方当前流程是准备 GitHub Release（`main.js`、`manifest.json`、可选 `styles.css`），在 Community directory 登录、关联 GitHub 后提交；不要照搬旧博客中只改注册表 PR 的流程。本轮未操作账号、发布仓库或提交市场。[提交文档](https://docs.obsidian.md/plugins/releasing/submit-plugin)、[提交要求](https://docs.obsidian.md/community-directory/submission-requirements-for-plugins)。

## 8. 怎样让用户愿意回来

习惯应来自反复发生的写作需求，而不是提醒刷存在感：读到资料时捕获；写作时回到项目；交稿前处理几项明确判断；来源变化时有理由重新检查。每次返回都应让作者更快定位下一步，且离开插件后仍能使用材料和文章。

目前尚未观察真实用户行为。已经准备 [四周试点方案](PILOT-PLAN.md) 和空白记录表，衡量首次成功、第二项目、有效返回、误阻拦、返工与放弃原因。下载数、打开次数、生成字数不作为留存成功标准。对个人作者先降低使用与迁移成本；未来收费只作为待访谈验证的托管/支持或团队协作假设，不先锁住用户已有内容。
