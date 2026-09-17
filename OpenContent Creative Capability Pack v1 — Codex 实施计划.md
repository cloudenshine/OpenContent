# OpenContent Creative Capability Pack v1
## Codex Implementation Charter

### 0. Mission

在现有 `cloudenshine/OpenContent` 主干上实现一个生产级、可扩展的 **Creative Capability Pack** 架构。

本阶段的目标不是“集成 Oh Story”，也不是创建通用 Agent 平台，而是：

> 建立 OpenContent 的通用创作能力包机制，并以 `Narrative Pack` 作为第一个真实生产能力包。  
> Oh Story 作为方法、Skill、脚本和工作流的重要参考来源；可依法复用的实现经过审计后选择性吸收，但不形成第二套项目管理、状态管理或正式作品真源。

完成后，OpenContent 应形成以下稳定结构：

```text
Obsidian UI
    ↓
OpenContent Core
    ↓
Creative Capability Runtime
    ↓
Capability Pack
    ↓
Local Agent CLI
```

第一期：

```text
OpenContent
    ↓
Capability Runtime
    ↓
Narrative Pack
    ↓
Codex / Claude CLI
```

后续可以增加：

```text
Evidence Essay Pack
History Storytelling Pack
Video Narrative Pack
Travel Narrative Pack
Social Content Pack
...
```

新增 Pack 原则上不得要求修改 OpenContent Core 的领域语义。

---

# 1. 首先执行 Repository Audit

开始编码前必须检查当前实际仓库，不以本 Charter 中的文件名或历史文档代替现实代码。

检查：

```text
README.md
docs/ARCHITECTURE.md
docs/SCHEMA.md
opencontent/domain.py
opencontent/providers.py
opencontent/jobs.py
opencontent/kernel.py
opencontent/workbench.py
opencontent/vault.py
opencontent/editorial.py
plugin/
tests/
scripts/verify.py
scripts/doctor.py
```

同时检查：

```text
当前 git status
当前 branch
未提交用户修改
当前版本号
当前测试数量
当前 Provider 行为
当前 Schema
当前 Plugin API
```

任何现有用户工作不得覆盖。

如果实际代码已经比本文规划更先进，以实际实现为基线，只补缺口，不倒退重构。

---

# 2. Frozen Architecture Invariants

以下为本轮冻结架构原则。除非实际代码证明某一条无法实施，否则不得更改。

## 2.1 OpenContent Core 不懂具体创作方法

Core 可以理解：

```text
Project
Artifact
Candidate
Review
Version
Approval
Job
Provider
Pack
Capability
```

Core 不应该硬编码：

```text
小说应该怎样写
历史内容怎样讲
视频脚本应该怎样安排镜头
公众号文章应该怎样起标题
```

这些属于 Pack。

---

## 2.2 Pack 可以包含 Skill，但 Pack 不等于 Skill

Capability Pack 可以拥有：

```text
Manifest
Profiles
Workflows
Skills
Agents
References
Context Selectors
Scripts
Validators
Rubrics
Templates
```

不要将 Pack 实现成简单的 `SKILL.md[]` 数组。

---

## 2.3 OpenContent 保持唯一正式状态管理者

不得引入第二套正式 Canon、正式 Project 状态或正式 Artifact 真源。

正式领域状态继续由 OpenContent 管理。

Capability Pack 与 Agent CLI 只允许产生：

```text
Candidate Artifact
Proposal
State Delta
Review
Diagnostic
```

Agent 不得直接批准作品。

---

## 2.4 Markdown 继续作为领域内容真源

不得因为 Narrative Pack 引入新的正式 SQLite 内容库、图数据库或 JSON Story Database。

如 Pack 内部需要：

```text
tracking-state.json
temporary cache
prompt snapshot
runtime metadata
```

它们只能属于：

```text
runtime
workspace
derived state
candidate state
```

不得与 OpenContent Markdown 真源并列。

---

## 2.5 Context 必须按任务选择

禁止默认把整个 Vault、整个项目、全部历史记录注入模型。

原则：

> Only load information whose absence could materially cause the current task to be wrong.

Context Assembler 必须成为独立能力。

---

## 2.6 新内容类型优先增加 Pack / Profile

不得因为增加小说、视频、历史叙事等能力，在 Core 中不断增加：

```python
if type == "fiction"
elif type == "video"
elif type == "history"
...
```

领域差异首先通过：

```text
Pack
Profile
Validator
Workflow
```

表达。

只有真正跨 Pack 共性的能力才能进入 Core。

---

# 3. 不允许本轮做的事情

本轮禁止以下范围扩张：

```text
不重写 OpenContent
不替换 Python Kernel
不实现微服务
不引入 Kubernetes
不引入图数据库
不实现通用 DAG/workflow 平台
不实现插件市场
不实现 Pack 在线商店
不支持移动端
不一次支持所有 Agent CLI
不一次实现多个生产 Pack
不复制 Oh Story 的整个项目目录
不把所有 Oh Story Skill 自动安装到用户全局环境
不重做现有 Publish / Evidence / Approval 系统
```

本轮只完成：

```text
Capability Pack Architecture
+
Narrative Pack
+
真实本地 CLI 闭环
```

---

# 4. Target Architecture

建议形成：

```text
opencontent/
    capabilities/
        __init__.py
        manifest.py
        registry.py
        runtime.py
        router.py
        context.py
        contracts.py
        validation.py

packs/
    narrative/
        pack.yaml

        profiles/
            general-fiction.yaml
            serial-fiction.yaml
            narrative-nonfiction.yaml

        workflows/
            plan.yaml
            write.yaml
            continue.yaml
            revise.yaml
            critique.yaml

        context/
            selector.py

        skills/
            ...

        agents/
            creator.*
            researcher.*
            continuity.*
            critic.*

        validators/
            continuity.py
            scope.py
            state_delta.py

        references/
            ...

tests/
    capabilities/
    narrative/
```

这是目标逻辑结构，不要求机械照搬目录。如果仓库现有模块组织有更合适的惯例，应服从现有工程风格。

---

# 5. Phase A — Capability Pack Contract

## 5.1 定义 `pack.yaml`

最小 Schema：

```yaml
schema: opencontent.capability-pack.v1

id: narrative
name: Narrative Creation
version: 1.0.0

description: >
  Narrative planning, writing, continuation,
  revision and critique.

profiles:
  - general-fiction
  - serial-fiction
  - narrative-nonfiction

tasks:
  - plan
  - write
  - continue
  - revise
  - critique

runtime:
  tools: required
  workspace_write: required
  session: optional
  web: optional

workflows:
  plan: workflows/plan.yaml
  write: workflows/write.yaml
  continue: workflows/continue.yaml
  revise: workflows/revise.yaml
  critique: workflows/critique.yaml

context:
  selector: context/selector.py

outputs:
  - artifact
  - proposal
  - state_delta
  - review
```

不要在 Manifest 内放大段 Prompt。

Manifest 只描述能力。

---

## 5.2 Manifest Validator

必须验证：

```text
schema version
pack id
semantic version
duplicate id
declared paths
task names
profile existence
workflow existence
runtime requirements
output contract
```

错误 Pack：

```text
不得半加载
不得静默忽略
不得继续运行
```

应返回可诊断错误。

---

## 5.3 Pack Registry

实现：

```text
discover()
validate()
register()
list_capabilities()
get_pack()
get_profile()
```

Discovery 只扫描受信任 Pack roots。

不得递归执行未知代码。

Manifest 验证完成以前不得 import Pack Python module。

---

# 6. Phase B — Capability Runtime

新增 Capability Runtime，但保持现有 Jobs 作为任务生命周期管理者。

职责划分：

```text
Jobs
= task lifetime / cancel / interrupted / receipts

Capability Runtime
= pack / workflow / context / task execution semantics

Provider
= local Agent runtime

Domain
= formal state / approval / invariants
```

不要出现两个 Job Scheduler。

---

## 6.1 Task Request Contract

定义统一请求：

```json
{
  "schema": "opencontent.creative-task.v1",
  "project": "...",
  "task": "write",
  "pack": "narrative",
  "profile": "general-fiction",
  "instruction": "...",
  "artifact": "...",
  "selection": null,
  "constraints": {},
  "runtime": {}
}
```

不得让插件 UI 直接拼复杂 Agent Prompt。

---

## 6.2 Task Router

Router 只负责：

```text
task → pack
task → profile
task → workflow
```

v1 不实现 AI 自动路由。

使用显式规则。

如果用户没有指定 Profile，可以根据项目已有配置提供推荐，但必须可见、可修改。

不要让模型暗中决定项目类型。

---

# 7. Phase C — Context Assembler

这是本阶段 P0。

建立统一的：

```text
Context Package
```

例如：

```json
{
  "schema": "opencontent.context.v1",

  "task": "write",

  "intent": {},
  "current_artifact": {},
  "must_preserve": [],
  "must_not_do": [],

  "relevant_state": {},
  "relevant_history": [],

  "open_threads": [],
  "sources": [],
  "style": {},

  "freedom": [],

  "provenance": []
}
```

Context Assembler 必须能够解释：

```text
为什么这条内容被选中
来自哪个对象
来自哪个版本
属于事实、设定、偏好还是建议
```

---

## 7.1 Narrative Context Selection

Narrative Pack 首版至少处理：

```text
当前创作目标
当前 Artifact
相关人物状态
相关人物关系
相关世界规则
当前时间线
最近必要事件
未解决伏笔
当前章节/场景计划
用户明确限制
作品风格
必要来源材料
```

不要默认加载所有人物和整个前文。

---

## 7.2 Context Budget

实现软预算。

例如：

```text
P0 必须出现
P1 高相关
P2 有预算再加入
```

不得为了命中 token budget 随意截断 P0 内容。

如果必要上下文无法在合理预算内表达，应返回诊断，而不是静默丢失。

---

# 8. Phase D — Provider Upgrade

保留当前：

```text
CodexProvider
ClaudeProvider
```

但增加执行 Profile。

现有受限路径继续用于：

```text
distill
research extraction
structured critique
classification
```

新增：

```text
creative execution
```

---

## 8.1 Execution Profiles

至少：

```text
STRUCTURED_READONLY
CREATIVE_WORKSPACE
INDEPENDENT_REVIEW
```

### STRUCTURED_READONLY

保持现有严格模式。

---

### CREATIVE_WORKSPACE

允许 Agent：

```text
读取 Pack references
读取任务 workspace
执行 Pack 允许脚本
创建候选文件
```

禁止：

```text
修改正式 Vault 内容
修改 OpenContent Kernel
修改 Plugin
修改正式 Artifact
任意操作用户其他目录
```

---

### INDEPENDENT_REVIEW

必须使用与 Creator 不同的独立 Agent context/session。

如果运行时无法证明独立：

```text
review_independence = unavailable
```

不得伪装成独立 Critic。

---

# 9. Workspace Isolation

每一次创作任务创建独立：

```text
.opencontent/runs/<run-id>/
```

建议至少：

```text
request.json
context.json
pack/
input/
candidate/
state-delta.json
review/
stdout.log
stderr.log
receipt.json
```

正式 Vault 内容只读映射或复制必要快照。

Agent 主要写：

```text
candidate/
```

完成后由 Kernel 验证并接收。

---

# 10. Phase E — Narrative Pack v1

Narrative Pack v1 只做五项生产任务：

```text
plan
write
continue
revise
critique
```

暂不实现：

```text
扫榜
自动网络抓取
封面
商业平台预测
自动发布
复杂多 Agent swarm
```

---

# 11. Narrative Profiles

## 11.1 `general-fiction`

关注：

```text
人物
因果
冲突
主题
信息释放
场景
语言
```

不得强制网文节奏。

---

## 11.2 `serial-fiction`

可以吸收 Oh Story：

```text
期待管理
章节承诺
连续状态
章尾推进
剧情模块
情绪节奏
```

但这些只属于该 Profile。

---

## 11.3 `narrative-nonfiction`

强制：

```text
事实不可虚构
未知不得写成事实
推断必须与事实区分
引用/来源保持 OpenContent provenance
```

同时允许：

```text
重新排列信息
场景化
叙事视角
节奏
悬念
意象
```

这是 OpenContent 与 Narrative Pack 结合的核心 Profile。

---

# 12. Narrative Agents v1

只实现四个逻辑角色。

## Researcher

职责：

```text
事实核对
背景理解
参考机制提取
信息缺口
```

不得创作正式事实。

---

## Creator

职责：

```text
构思
规划
场景
正文
改写
```

不得批准自己作品。

---

## Continuity

职责：

```text
人物状态
时间线
世界规则
知识状态
伏笔
前后冲突
```

关注：

> 有没有写错。

---

## Critic

职责：

```text
结构
节奏
人物可信度
表达
读者体验
作品效果
```

关注：

> 写得是否成立。

不得让 Critic 负责事实来源真实性，事实来源仍由 OpenContent/Researcher/Evidence 体系负责。

---

# 13. Oh Story Integration Policy

使用：

```text
https://github.com/zenstory-ai/oh-story-claudecode
```

作为 upstream reference。

首先记录：

```text
upstream repository
commit SHA
license
files examined
files reused
files adapted
files rejected
reason
```

建立：

```text
docs/upstream/oh-story-audit.md
```

---

## 13.1 优先吸收

重点研究：

```text
上下文选择
单章写作流程
连续创作
tracking state
outline slicing
写前准备
参考机制召回
targeted revision
continuity check
review orchestration
```

---

## 13.2 不直接吸收

不直接引入：

```text
Oh Story 项目状态系统
Oh Story 项目目录作为正式真源
全局安装逻辑
全套 CLI compatibility layer
所有平台特定配置
所有网文 rubric
固定“去 AI 味”规则
封面与扫榜链路
与 OpenContent 重复的审查/批准机制
```

---

## 13.3 Code Reuse

如果直接复制或衍生代码：

```text
确认 LICENSE
保留必要 attribution
记录 upstream commit
最小化复制
增加本项目测试
```

不要复制整个目录再删除不用部分。

---

# 14. Workflow — `write`

建议逻辑：

```text
User Instruction
      ↓
Resolve Pack/Profile
      ↓
Snapshot current project/version
      ↓
Context Assembly
      ↓
Validate context
      ↓
Create isolated workspace
      ↓
Creator execution
      ↓
Output parse
      ↓
Continuity validation
      ↓
Independent Critic
      ↓
Targeted correction if necessary
      ↓
Candidate Artifact
      ↓
Kernel Validation
      ↓
Diff
      ↓
Needs Judgment
```

用户没有要求时：

```text
最多一轮自动 targeted revision
```

禁止无限：

```text
write → critic → rewrite → critic → rewrite...
```

---

# 15. Workflow — `continue`

Continue 不能解释为：

```text
恢复最近聊天
```

必须：

```text
指定 Project
指定正式 Artifact 或候选 branch
读取当前权威状态
构造 Context Package
继续创作
```

Session continuation 可以作为优化，但不得成为作品连续性的唯一来源。

---

# 16. Workflow — `revise`

局部修改优先。

输入应包含：

```text
目标范围
问题
原文
允许改变什么
必须保留什么
```

默认：

```text
minimal necessary change
```

不得因为修改一个段落自动重写全文。

---

# 17. Workflow — `critique`

Critic 输出不要只给综合分数。

使用：

```json
{
  "issues": [
    {
      "severity": "hard|major|minor",
      "location": "...",
      "problem": "...",
      "evidence": "...",
      "impact": "...",
      "suggested_action": "..."
    }
  ],
  "strengths": [],
  "uncertainties": []
}
```

确定性错误与审美意见必须分开。

禁止：

```text
AI 味评分 = 质量
禁词数量 = 质量
单一总分 = 批准依据
```

---

# 18. State Delta

Narrative Agent 不直接改 Canon。

返回：

```json
{
  "schema": "opencontent.state-delta.v1",

  "characters": [],
  "relationships": [],
  "timeline": [],
  "world": [],
  "open_threads": [],
  "resolved_threads": [],
  "new_proposals": []
}
```

所有 delta 必须标注：

```text
observed_from_output
explicit_user_instruction
agent_inference
```

`agent_inference` 不得自动升级为正式事实。

---

# 19. OpenContent Domain Evolution

不要破坏现有研究型项目。

当前：

```text
Material
Knowledge
Claim
Evidence
Idea
Project
Artifact
Review
Publication
```

继续支持。

新增差异优先通过：

```text
Project capability/profile
Artifact protocol
Pack-specific validation
```

表达。

不要立刻增加十几个领域对象。

只有经过真实案例证明某一概念：

```text
无法作为 Markdown 内容、Artifact metadata 或 Pack state 表达
且被多个任务复用
且需要 Core 级一致性
```

才考虑升级为新的 Core object type。

---

# 20. Multiple Artifact Support

当前产品对每项目单 Artifact 的自动审查限制必须解除。

最低目标：

```text
一个 Project
可以拥有多个 Artifact
每个 Artifact
拥有独立版本
独立 Review
独立 approval state
```

例如：

```text
Chapter 01
Chapter 02
Chapter 03
Article
Video Script
```

审查必须绑定：

```text
artifact id
artifact hash/version
dependency/context hash
```

旧 Review 不得自动批准新版本。

---

# 21. Plugin UX

保持：

```text
首页
写作
发布
```

不要增加 Capability 管理后台作为主要用户入口。

---

## 21.1 写作页增加

建议：

```text
Current Work
Context
Review
```

主区域始终是内容。

---

## 21.2 Context Preview

允许用户看到：

```text
本次用了哪些资料
本次用了哪些人物状态
本次用了哪些约束
为什么这些内容被选中
```

不要默认显示内部 JSON。

---

## 21.3 Candidate Diff

支持：

```text
Accept all
Accept selected change
Reject
Edit manually
Re-run selected revision
```

注意：

```text
Apply Candidate
≠
Approve Artifact
```

这两步必须继续分离。

---

# 22. Failure Semantics

不得“尽量继续”掩盖关键失败。

以下必须 Fail Closed：

```text
Pack manifest invalid
required context missing
formal version changed
candidate output malformed
workspace escaped
independent review claimed but not actually run
state delta invalid
formal Artifact changed during generation
```

以下可以显式降级：

```text
optional reference missing
optional reviewer unavailable
native session continuation unavailable
optional tool unavailable
```

但降级必须显示在 receipt。

---

# 23. Security / Boundary Tests

必须实际测试：

```text
Agent 尝试写正式 Artifact
Agent 尝试写其他项目
Agent 尝试写 Vault 外
Agent 输出 ../ traversal
absolute path output
symlink escape
oversized output
invalid JSON
CLI crash
CLI timeout
cancel during write
Kernel restart
manual concurrent edit
stale Context Package
Pack code malformed
Pack manifest malicious path
```

不能仅测试 happy path。

---

# 24. Windows Acceptance

目标平台必须做真实 Windows 验收。

覆盖：

```text
中文 Vault 路径
包含空格路径
长路径
PowerShell
Codex native executable
Claude native executable
Obsidian desktop host
Python Kernel
Ctrl/Cancellation
Kernel restart
```

不要再次出现：

```text
只在 Python unit test PASS
但 Windows 实际运行失败
```

---

# 25. Test Pyramid

## Unit

测试：

```text
Manifest parser
Registry
Router
Context selection
Context priority
Output contracts
State delta
Validators
Path security
```

---

## Contract

测试：

```text
Core ↔ Pack
Pack ↔ Provider
Provider ↔ workspace
Candidate ↔ Kernel
Review ↔ Artifact version
```

---

## Integration

使用 fake Provider：

```text
write
continue
revise
critique
cancel
interrupted
stale input
```

---

## Real Runtime

至少测试：

```text
Codex real CLI
Claude real CLI（若本机存在且已登录）
```

不能以 Fake Provider 代替真实验收。

---

# 26. Creative Acceptance Cases

建立固定案例，不使用私人 Vault。

## Case A — Short Fiction

要求：

```text
创建一个短篇故事
产生 Candidate
Continuity PASS
Critic 实际独立执行
人工 Accept
```

验证：

```text
人物状态
情节因果
局部 revision
version invalidation
```

---

## Case B — 3-Chapter Serial

要求：

```text
Chapter 1
Chapter 2
Chapter 3
```

每章分别运行。

关闭 CLI / 新开任务后继续。

验证：

```text
人物状态连续
时间线连续
伏笔连续
不依赖聊天记忆
```

---

## Case C — Narrative Nonfiction

提供固定历史资料。

验证：

```text
事实不改变
未知不伪造
推断明确区分
叙事组织明显优于资料堆砌
```

---

## Case D — Local Revision

只修改：

```text
一个段落
```

验证：

```text
未修改其他段落
未改变事实
未引入新设定
Diff 精确
```

---

# 27. A/B Evaluation

至少比较：

```text
A. 当前 OpenContent
B. 直接给本地 CLI 精炼 Prompt
C. Oh Story 原始适用流程
D. OpenContent + Narrative Pack
```

在尽可能相同：

```text
模型
任务
输入
预算
```

条件下测试。

评价：

```text
连续性
结构
人物可信度
事实保真
作者声音
人工修改量
运行失败率
总耗时
```

允许平局。

不得为了证明新系统有价值而选择性展示样本。

若 Pack 增加流程但没有降低人工修改或提高稳定性，应优先删除流程。

---

# 28. Performance / Context Measurements

每个 run receipt 至少记录：

```text
pack
pack version
profile
task
provider
model
context size
selected context items
execution time
review mode
retry count
candidate version
```

如果 CLI 能提供 token/cost 信息，则记录；不能提供时不得伪造估算为真实值。

---

# 29. Pack Provenance

每个 Candidate 必须知道：

```text
使用哪个 Pack
使用哪个 Pack version
使用哪个 Profile
使用哪些 Skills
使用哪个 Context snapshot
使用哪个 Provider
使用哪个 Run
```

未来 Pack 升级后：

```text
旧 Artifact 仍可以追溯旧 Pack version
```

---

# 30. Backward Compatibility

现有 OpenContent 0.8.x 项目必须能够继续打开。

没有 Pack metadata 的旧 Project：

```text
保持原研究型行为
```

不得静默把旧项目转换成 Narrative Project。

如需迁移：

```text
显式 migration
+
backup
+
verification
```

---

# 31. Documentation

完成以下文档：

```text
docs/CAPABILITY-PACK-ARCHITECTURE.md
docs/NARRATIVE-PACK-v1.md
docs/PACK-AUTHORING.md
docs/upstream/oh-story-audit.md
docs/CAPABILITY-SECURITY.md
docs/CAPABILITY-VALIDATION.md
```

其中 `PACK-AUTHORING.md` 必须让未来第二个 Pack 无需阅读 Narrative Pack 全部源码即可开始实现。

---

# 32. README

README 只添加用户能够理解的说明：

```text
OpenContent supports installable creative capability packs.
Narrative Creation is the first production pack.
```

不要把内部架构大段搬进 README。

---

# 33. Codex Working Strategy

不要逐 Phase 等待用户批准。

在确认没有未授权不可逆操作以后，自主执行：

```text
Inspect
→ Design
→ Implement
→ Test
→ Real Runtime Acceptance
→ Adversarial Review
→ Correct
→ Regression
→ Document
→ Commit
```

出现失败：

```text
定位 Root Cause
→ 修复
→ 重跑受影响测试
```

不要：

```text
修一个错误
→ 打包
→ 让用户成为下一阶段测试员
```

---

# 34. Worktree Strategy

如果当前环境支持 Codex 并行工作，可以使用独立 worktree 处理低耦合任务：

```text
WT-A
Capability Contract / Registry / Manifest

WT-B
Narrative Pack / Context / Validators

WT-C
Provider / Runtime / Workspace Security

WT-D
Plugin UX

WT-E
Tests / Fixtures / Adversarial Acceptance
```

但不要同时修改同一核心文件。

最终由主工作区：

```text
review
integrate
resolve
full regression
```

如果工作量不足以证明 worktree 有明显收益，则保持单工作区。

不得为了并行而并行。

---

# 35. Required Verification Commands

基于仓库现有命令执行，并在实际环境确认。

至少：

```powershell
python scripts/verify.py
python scripts/doctor.py --runtime .
```

除此以外运行：

```text
new capability unit tests
new integration tests
real CLI acceptance
real Obsidian host acceptance
```

如果仓库实际已有更严格命令，以实际命令为准。

---

# 36. Adversarial Review Before Completion

完成编码后，独立重新审查以下问题：

### Architecture

```text
是否出现第二套正式状态？
是否出现 Core 对 Narrative 的硬编码？
是否引入了不必要的通用框架？
第二个 Pack 是否真的无需改 Core？
```

### Agent

```text
是否真的调用 CLI？
是否真的使用必要工具？
是否把工具失败伪装为成功？
独立 Critic 是否真正独立？
```

### Context

```text
有没有整库灌入？
P0 是否可能被截掉？
来源与正式状态是否混淆？
```

### Security

```text
Agent 是否能越界修改正式 Vault？
symlink / traversal 是否可能绕过？
```

### UX

```text
用户是不是被迫理解 Skill / Agent / Workflow？
主要界面是否仍以作品为中心？
```

### Creative Quality

```text
流程是否提高质量？
还是只是增加复杂度？
```

发现问题直接修复，不只写报告。

---

# 37. Kill Criteria

出现以下情况时，停止当前实现方向并重新设计局部模块：

```text
需要大规模重写 OpenContent Core 才能支持 Pack
第二个 Pack 必须复制 Narrative Core
Context Runtime 变成通用工作流引擎
Pack 可以绕过正式 Approval
Agent 可以修改正式 Artifact
真实 CLI 无法稳定运行
Pack 导致现有研究型项目回归
```

---

# 38. Definition of Done

只有同时满足以下条件才算本阶段完成。

### Architecture

```text
Capability Pack Contract 已实现
Pack Registry 已实现
Capability Runtime 已实现
Narrative Pack 已实现
Core 与 Pack 边界明确
```

### Runtime

```text
真实 Codex CLI PASS
真实 Claude CLI 在本机可用时 PASS
cancel PASS
interrupt PASS
stale version PASS
workspace isolation PASS
```

### Creative

```text
短篇 PASS
三章连续写作 PASS
非虚构叙事 PASS
局部修改 PASS
独立 Critic PASS
```

### Compatibility

```text
旧 OpenContent 项目 PASS
现有 research/evidence 流程 PASS
现有 export/publishing 流程无回归
```

### Host

```text
真实 Obsidian Desktop PASS
Windows 中文路径 PASS
Windows 空格路径 PASS
```

### Quality

```text
完整测试 PASS
无静默 fallback
无伪成功
无未说明 skipped acceptance
```

---

# 39. Final Delivery

最终一次性交付以下内容：

```text
1. 实际实现内容
2. 修改文件清单
3. 新增 Capability 架构
4. Narrative Pack 能力清单
5. Oh Story 复用/未复用审计
6. 测试结果
7. Windows 真实验收结果
8. Obsidian 真实宿主结果
9. Codex / Claude CLI 实测结果
10. A/B 创作质量结果
11. 已知限制
12. 第二个 Pack 的接入证明
13. Git commit hash
```

如果某项因为当前机器条件无法验证：

明确写：

```text
NOT VERIFIED
```

不得写成：

```text
PASS
expected to work
should work
```

---

# 40. Git Delivery

只有全部可执行验证完成后：

```text
git diff review
git status review
secret scan
generated junk check
full regression
```

然后创建一次清晰的正式提交。

如果当前远端与权限允许，并且用户现有授权包含发布：

```text
push to the intended branch
```

不得 force push。

不得改写用户已有历史。

---

# 41. 最终产品原则

实施全过程都围绕这一句话判断：

> OpenContent owns the work.  
> Capability Packs know how to create.  
> Agent CLIs do the work.  
> The human decides what becomes authoritative.

中文：

> **OpenContent 管作品；能力包懂创作；本地 Agent 负责干活；用户决定什么成为正式成果。**

如果某个实现违反这四者的职责边界，应优先删除或重构，而不是继续堆兼容层。