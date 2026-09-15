# Markdown Schema 与 Kernel 协议

对象路径 `OpenContent/<Type>/<oc_id>.md`。`oc_id` 为 32 位小写十六进制稳定 ID，文件重命名后仍用 frontmatter ID 解析；Artifact 的 `[[id]]` 引文依赖 Obsidian 文件名，MVP 建议保留 ID 文件名、用 `title` 展示名称。YAML frontmatter 可用 Obsidian 属性编辑；不支持 YAML anchors、重复字段、符号链接目录或 >1 MB 对象。

```yaml
---
oc_id: 0123456789abcdef0123456789abcdef
type: Knowledge
title: 一项可复用知识
created: '2026-09-08T08:00:00+00:00'
project: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
derived_from:
  - bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
---

从材料中提炼的知识正文。来源 ID 指向 Material。
```

| 类型 | 必需语义字段 | 溯源与约束 |
|---|---|---|
| Material | source、正文 | URL / vault:原路径 / 明确人工来源；捕获快照 |
| Knowledge | derived_from | 同项目 Material ID，至少一个 |
| Idea | derived_from、正文 | 同项目 Knowledge ID，至少一个 |
| Project | goal、audience、thesis、state、history | thesis 在进入 IDEA 前必须形成；history 保存通过依据 |
| Claim | derived_from、confidence、正文 | 同项目 Knowledge ID；confidence=low/medium/high；正文为完整主张 |
| Evidence | claim、material、quote、relation、正文 | relation=supports/opposes；quote 必须是 Material 正文子串；正文说明支持/反对理由 |
| Artifact | derived_from、author、state、正文 | Claim ID 列表；正文逐项包含 Claim 原句和 `[[id]]` 或 `[[id|label]]` |
| Review | artifact、mode、origin、reviewer、context_hash | mode=critique/decision；审查快照与决定都留在 Markdown |
| Publication | artifact、url、published_at、context_hash、正文 | 只追踪已批准版本；正文可手动记录观察 |

Critic Review 的 `axes` 必须完整包含 Evidence、Logic、Originality、Voice、Utility；每轴 `status=PASS/WARN/FAIL` 与不少于 8 字符的 `reason`。`claims_complete` 明确表达重要事实登记是否完整；有反对证据需要 `conflict_resolution`。`reviewed_body` 保留审查时草稿用于 Diff。正文是审查总结。

人工 Review 的 `mode=decision`、`origin=human`、`decision=accept/reject`、`review` 指向 Critic Review，正文保存决定理由。外部 Agent 没有此写入动作。

## 状态门禁

| 到达状态 | 前置证据 |
|---|---|
| CAPTURED | Project 目标、读者 |
| DISTILLED | Material 与合法 Knowledge 溯源 |
| IDEA | 合法 Idea 与非空 thesis |
| RESEARCHING | 已形成 Idea / thesis |
| ARGUMENT_READY | Claim→Knowledge→Material 完整、每 Claim 至少一项有效支持 Evidence |
| DRAFTING | 论证门禁再次有效 |
| REVIEWING | Artifact、结构有效的 Review、论证链 |
| APPROVED | 当前草稿全部通过 Quality Gate + 每个 Artifact 明确人工 accept |
| PUBLISHED | 手动 Publication URL/时间与批准版本一致 |
| LEARNING | 手动发表观察存在；无自动反馈学习 |

自动 pipeline 分为四个独立任务尝试：distill（推进到 RESEARCHING）、research（推进到 DRAFTING）、draft（新建 Artifact）、critique（推进到 REVIEWING）。每次跨越多个状态仍逐个检查前置条件并记录 history。`done`、Provider 退出码 0 或 Markdown 中写 `state: APPROVED` 都不能代替批准证据。

Quality Gate 每次从 Markdown 重新计算。内容依赖哈希包括 Project 内容、Material、Knowledge、Idea、Claim、Evidence、当前 Artifact 和共享/项目宪章。Review/Publication 不递归进入哈希；最新 Critic ID 仍必须匹配人工决定。声明的高阶 state 在失效时由 Board/Inspector 显示有效状态 REVIEWING，原始历史字段保留，不覆盖用户文件。

## 最小 HTTP API

所有请求须 `Authorization: Bearer <startup token>`，修改请求为 JSON 对象且不超过 1 MB。

| 路由 | 用途 |
|---|---|
| GET /health | Vault 身份、Provider capabilities |
| GET /board | 生产板、判断收件箱、诊断、当前 token、任务 |
| GET /objects/:id | 项目关联对象或 Artifact 溯源与 Gate |
| GET /jobs | 最近 100 条任务收据 |
| POST /projects | title、goal、audience |
| POST /objects | project、type、title、body、fields、token |
| POST /capture | project、title、body、source、token、可选 HTTP(S) source_url；返回 object/duplicate |
| POST /handoff | artifact、token；仅当前批准稿，返回本地 path/file_hash/context_hash/status，不发布 |
| POST /advance | project、target、token、可选 thesis |
| POST /reviews | artifact、reviewer、axes、claims_complete、summary、conflict_resolution、token |
| POST /decisions | artifact、decision、reviewer、reason、token |
| POST /jobs | project，可选 provider / stage=critique / resume=旧任务 ID / token；插件提交预览 token |
| POST /cancel | id |
| POST /shutdown | 停止本服务并取消其拥有的执行 |

`token` 为 Vault 内容快照版本，不是 Bearer 凭据。外部修改后旧 token 返回 409；程序应显示冲突，让使用者检查后重新执行，不能静默覆盖。

0.3 的 `/capture` 正规化换行及首尾空白，按同项目 `source/body/source_url` 去重；材料可增加 `capture_hash` 和 `source_url`。不存在自动修改原始来源笔记的步骤。`/jobs` 首个请求检查排队时的版本；后续阶段仍按已有响应提交 CAS 验证。`/handoff` 在构造前和写入前重新核对版本，重新求值批准门禁；交接是非权威导出，接收者后续修改不会回写批准稿。

## Provider 契约

`AgentExecutionProvider` 位于 `opencontent/providers.py`，Domain 不导入具体 Provider。Job Manager 依赖接口实例注册表。响应仅接受当前阶段的 schema；新对象 ID、状态、运行来源由 Kernel 分配，原文引用由 Kernel 验证。Skill 从显式目录发现；Agent 看到同一份可编辑 CONTENT.md。

失败阶段保留请求/响应/诊断，不写入半份领域对象。后续重试重新捕获当前 Vault。Kernel 异常停止后 QUEUED/RUNNING 转为 INTERRUPTED；仅在用户继续后新建任务，不伪造续跑成功。

## v0.4 增量契约

Material 可含 source_note_hash、versions（旧正文/来源哈希）、reused_from。来源变化检查读取原始 Vault Markdown；旧版无哈希显示 UNTRACKED，可显式刷新开始跟踪。Project.planning.planned_for 不计入内容审查哈希。

Publication 继续是 Markdown 领域对象，新增 channel、destination、action、payload、delivery_status、events、intent_hash、remote_media_id / publish_id / article_id、verified_at、feedback。没有 delivery_status 的旧记录按 MANUAL 兼容；准备或失败记录不要求有发表 URL，不能用于推进 PUBLISHED。反馈及回执不递归使原稿审查失效。

新增 API：GET /sources、GET /publications；POST /sources/preview、/sources/refresh、/sources/reuse、/projects/plan；POST /channels、/channels/check、/channels/cover；POST /publications/prepare、/publications/confirm、/publications/reconcile、/publications/cancel；POST /feedback、/feedback/decide、/feedback/project。具体 JSON 参数与边界以 server.py 路由和 tests/test_lifecycle.py 为可执行规范。

/publications/confirm 必须提交 publication、当前 preview_hash 作为 confirmation、reviewer、当前 Vault token。确认的内容和关联批准作为不可变投递意图；reconcile 不执行内容写入。只有 prepare(draft)/confirm 创建草稿、prepare(publish)/confirm 提交发表；本地重启不自动重试。

恢复用 ACK 文件存于 .opencontent/delivery-recovery/<Publication ID>.json；文章及历史真源仍是 Publication Markdown。崩溃时若 ACK 已收到但 Markdown 保存失败，恢复先读 ID 再查询微信。丢失所有 ID 不盲目猜测重发。
