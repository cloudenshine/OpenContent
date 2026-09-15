# OpenContent — Implementation Charter

## 1. Mission

构建一个运行在 Obsidian 之上的 **Agent-driven Content Production Operating System**。

它不是 AI 写作插件，不是 Chat with Vault，也不是新的 Agent Client。

它的目标是：

> 将一个普通 Obsidian Vault 转化为一个可以持续运行的内容生产系统，使知识、材料、想法、研究、创作、审判、发布和反馈形成可追踪、可验证、可积累的生产闭环。

核心生产链：

```text
Material
→ Knowledge
→ Idea
→ Project
→ Research
→ Claim / Evidence
→ Artifact
→ Judgment
→ Publication
→ Feedback
→ Editorial Memory
↺
```

OpenContent 必须拥有的是这条生产链的：

```text
State
Provenance
Policy
Judgment
Lifecycle
Memory
```

而不是拥有某一个模型、Agent 或发布平台。

---

# 2. Core Product Principle

## OpenContent is the control plane, not the worker.

外部 Agent 是 Worker。

例如：

```text
Codex
Claude Code
Hermes
OpenCode
ACP Agent
Future Agents
```

OpenContent 不应围绕某个具体 Agent 编写业务逻辑。

内核只认识统一能力：

```text
AgentExecutionProvider

capabilities:
- read
- write
- reason
- tools
- web
- skills
- session
```

任何具体 Agent 都只是 Adapter。

---

# 3. Product Mental Model

不要以：

```text
Current Note
Chat
Prompt
Answer
```

作为产品中心。

必须以：

```text
Content Project
```

作为中心对象。

一个 Project 至少能够关联：

```text
Goal
Audience
Thesis
Materials
Knowledge
Claims
Evidence
Artifacts
Reviews
Publications
Feedback
```

用户不是在“和 AI 聊天”。

用户是在：

> 运营一个持续推进的 Content Project。

---

# 4. Obsidian's Role

Obsidian 是：

```text
Human Workspace
Knowledge Space
Content Editor
Review Surface
Control Cockpit
```

而不是 Agent Runtime。

第一阶段定位：

```text
Desktop-first
```

插件应保持尽可能薄。

Obsidian Plugin 负责：

```text
UI
Commands
Editor integration
Project views
Production board
Content inspector
Judgment inbox
Diff / approve / reject
```

禁止把长时间运行任务、大型 Agent workflow、Browser automation、复杂后台队列全部塞入 Obsidian Plugin runtime。

---

# 5. Kernel Architecture

采用：

```text
Obsidian Plugin
        │
        ▼
OpenContent Kernel
        │
        ├── Domain Model
        ├── State Machine
        ├── Provenance
        ├── Judgment
        ├── Agent Adapters
        ├── Jobs
        ├── Policy
        └── Runtime State
```

Plugin 与 Kernel 必须有明确边界。

Kernel 不应依赖具体 Obsidian UI 才能工作。

未来应允许：

```text
CLI
Web UI
Desktop UI
Other editor
```

复用同一个 Kernel。

---

# 6. Data Ownership

必须坚持：

```text
Markdown = Human / Knowledge Source of Truth
SQLite   = Machine / Runtime State
```

## Markdown 保存

```text
Materials
Knowledge
Ideas
Projects
Claims
Evidence
Artifacts
Reviews
CONTENT.md
Editorial policies
Voice
Audience
```

## SQLite 仅保存

```text
jobs
queue
locks
sessions
runtime state
cache
execution trace
indexes
temporary state
```

原则：

> 卸载 OpenContent 后，用户的重要知识与内容仍然完整存在于 Vault。

禁止把核心内容锁进私有数据库。

---

# 7. Core Domain Model

第一阶段只实现以下九种核心对象：

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

不要提前增加几十种 Entity。

关系模型：

```text
Material
   ↓
Knowledge
   ↓
Claim ← Evidence
   ↓
Idea
   ↓
Project
   ↓
Artifact
   ↓
Review
   ↓
Publication
```

每个关系必须可以追踪来源。

---

# 8. Production State Machine

OpenContent 的核心不是生成，而是 Production State。

第一版定义：

```text
CAPTURED
↓
DISTILLED
↓
IDEA
↓
RESEARCHING
↓
ARGUMENT_READY
↓
DRAFTING
↓
REVIEWING
↓
APPROVED
↓
PUBLISHED
↓
LEARNING
```

要求：

1. 所有 Project / Artifact 必须具有明确状态。
2. 状态迁移必须有明确前置条件。
3. Agent 不允许通过“输出一句完成了”直接改变状态。
4. 状态迁移必须由可验证证据驱动。
5. Gate 未通过时不能进入下一阶段。

---

# 9. CONTENT.md

实现类似 OpenDesign `DESIGN.md` 的 Content Constitution。

每个 Vault 或 Project 可拥有：

```text
CONTENT.md
```

第一阶段结构：

```text
Audience
Voice
Editorial Principles
Evidence Policy
Citation Policy
Originality Standard
Forbidden Patterns
Quality Gates
```

所有参与生产的 Agent 都必须能够读取同一 Content Constitution。

不要通过大量隐藏 System Prompt 实现核心规则。

优先使用：

```text
human-readable
editable
versionable
filesystem-native
```

的 Markdown。

---

# 10. Provenance Is a First-Class Feature

必须建立：

```text
Editorial Provenance
```

不是普通双链。

系统应能够回答：

```text
这句话从哪里来的？
这个观点基于什么？
哪些 Evidence 支持它？
哪些 Evidence 反对它？
哪些 Artifact 使用过这个 Claim？
这篇文章由哪些 Knowledge 演化而来？
```

典型关系：

```text
Source
↓
Material
↓
Knowledge
↓
Claim
├── supporting Evidence
├── opposing Evidence
└── confidence
↓
Artifact
↓
Publication
```

Provenance 不应只是 UI 装饰。

它必须影响：

```text
Quality Gate
Fact Check
Review
Reuse
```

---

# 11. Judgment Is the Primary Intelligence Layer

OpenContent 最重要的 AI 能力不是 Writer。

而是：

```text
Judgment Engine
```

第一阶段至少实现五个 Quality Axis：

```text
Evidence
Logic
Originality
Voice
Utility
```

每个 Artifact 可以得到：

```text
PASS
WARN
FAIL
```

及证据说明。

例：

```text
Evidence       PASS
Logic          PASS
Originality    WARN
Voice          PASS
Utility        FAIL

Publish Gate   BLOCKED
```

Critic 可以提供意见。

但 Gate 才决定能否进入下一生产状态。

---

# 12. Human Role

OpenContent 的设计原则：

> Automate everything that does not require judgment.

用户不应该承担大量手动“加工”。

系统应自动完成：

```text
整理
关联
提炼
研究
生成
检查
转换
状态推进建议
```

只在真正需要人类判断时进入：

```text
Needs Judgment
```

典型场景：

```text
核心观点存在冲突
证据不足
方向需要选择
Critic 与 Creator 分歧
重大事实争议
发布前最终确认
```

用户角色应该主要是：

```text
Direction
Judgment
Taste
Decision
```

而不是流水线操作员。

---

# 13. Required Primary UI

第一版不要把 Chat 作为首页。

必须优先实现以下四个界面。

## 13.1 Production Board

显示整个内容生产系统的状态：

```text
Captured
Distilling
Ideas
Researching
Drafting
Reviewing
Ready
Published
```

用户一眼知道：

> 现在系统里有什么，分别推进到哪里。

---

## 13.2 Judgment Inbox

只显示需要用户决定的事项。

例如：

```text
Project: Agent × PKM

Current Thesis A
...

Alternative Thesis B
...

Critic Recommendation: B

[Accept B]
[Keep A]
[Challenge Again]
[Inspect Evidence]
```

---

## 13.3 Content Inspector

打开任意 Artifact 后显示：

```text
Project
Stage
Thesis

Evidence Score
Logic Score
Originality Score
Voice Score
Utility Score

Claims
Supported
Contested
Unsupported

Derived From
Used By
Outputs

Gate Status
```

---

## 13.4 Project View

展示：

```text
Goal
Audience
Thesis
Materials
Knowledge
Claims
Evidence
Artifacts
Reviews
Publications
```

---

# 14. Agent Integration

第一版只实现一个稳定 Agent Adapter 即可。

推荐优先：

```text
Codex
```

但 Domain 和 Kernel 不得硬编码：

```text
if agent == codex
```

必须从一开始保留 Provider abstraction。

第一阶段接口至少支持：

```text
run()
resume()
cancel()
capabilities()
```

Skill 也应通过 filesystem discovery 接入，而不是复制进 OpenContent。

---

# 15. External Dependency Principle

核心系统必须能够在以下状态运行：

## Level 0 — No AI

仍然具备：

```text
Project
State
Material
Knowledge
Claim
Evidence
Review
Publication tracking
Provenance
```

## Level 1 — Generic LLM

增加：

```text
summarize
distill
classify
rewrite
critique
```

## Level 2 — Agent Runtime

增加：

```text
research
multi-step execution
tools
skills
project operations
```

## Level 3 — External Integrations

增加：

```text
web
MCP
publishing
analytics
RSS
CMS
```

任何 Level 2 / Level 3 能力都不能成为核心数据模型的所有者。

---

# 16. Do Not Rebuild Existing Ecosystem

第一阶段禁止重新建设：

```text
Generic Chat UI
RAG system
Embedding engine
Semantic Search
Model manager
Prompt marketplace
Generic MCP manager
Claude clone
Codex clone
Generic publisher
CMS
Cloud sync
Team collaboration
Mobile agent runtime
```

这些已经有成熟方案。

OpenContent 的竞争力必须集中在：

```text
Lifecycle
State
Provenance
Judgment
Policy
Memory
```

---

# 17. Relationship With Products Like Ailu

不要复制 Ailu。

Ailu 型产品解决：

```text
Current Markdown
→ Agent editing
→ Preview
→ Transform
→ WeChat / Feishu / X Draft
```

OpenContent 解决：

```text
Material
→ Knowledge
→ Idea
→ Project
→ Research
→ Evidence
→ Artifact
→ Judgment
→ Publication
→ Learning
```

Ailu 类型能力未来应通过：

```text
Publishing Adapter
External Tool Adapter
```

接入。

OpenContent 应拥有 lifecycle，而不是渠道。

---

# 18. MVP Scope

第一版只构建一个真正闭环。

必须包含：

```text
1. CONTENT.md

2. Content Project

3. Material / Knowledge / Claim / Evidence

4. Production State Machine

5. Single Agent Adapter

6. Artifact model

7. Judgment Engine

8. Quality Gate

9. Provenance

10. Judgment Inbox

11. Production Board
```

暂时不要实现：

```text
Publishing automation
Analytics
Feedback learning
Multi-agent orchestration
Marketplace
Team collaboration
Cloud
Mobile
```

---

# 19. Reference MVP Workflow

第一版必须能完整跑通：

```text
用户创建 Project
↓
选择若干 Material
↓
系统提炼 Knowledge
↓
形成 Idea / Thesis
↓
进入 Research
↓
生成 Claim
↓
绑定 Evidence
↓
形成 Argument
↓
生成 Draft Artifact
↓
Critic Review
↓
Quality Gate
↓
出现 Needs Judgment
↓
用户 Accept / Reject
↓
Artifact → APPROVED
```

这条链必须真正工作。

不要用 mock 状态假装完成。

---

# 20. Acceptance Criteria

MVP 只有满足以下条件才能算完成。

## A. Data ownership

删除插件后：

```text
Project
Knowledge
Claims
Evidence
Artifacts
Reviews
```

仍然可读。

---

## B. Agent independence

更换 Agent Adapter 不需要修改 Domain Model。

---

## C. Traceability

任意 Artifact 中的重要 Claim 都能追溯到：

```text
Evidence
Knowledge
Material
```

---

## D. State correctness

不存在：

```text
Agent says "done"
→ directly APPROVED
```

所有关键状态迁移都有 Gate。

---

## E. Human judgment

用户只需要在真正存在决策意义的地方介入。

---

## F. No hidden system dependency

无 Codex/Claude 时，核心 Project/State/Provenance 仍能运行。

---

## G. Obsidian responsiveness

长时 Agent 操作不得阻塞 Obsidian 主 UI。

---

## H. Failure behavior

外部 Agent、Kernel 或任务失败时：

```text
不得损坏 Vault
不得伪造成功状态
必须保留可诊断状态
```

---

# 21. Engineering Priorities

优先级：

```text
Correct domain model
>
State correctness
>
Provenance
>
Judgment
>
Agent integration
>
UI polish
>
Extra features
```

不要因为 UI 漂亮而牺牲生产模型。

不要因为 Agent 能力强而绕过状态机。

不要用复杂 Multi-Agent 架构补偿错误的数据模型。

---

# 22. Architecture Philosophy

优先：

```text
simple
filesystem-native
local-first
replaceable
observable
reversible
verifiable
```

避免：

```text
monolithic plugin
hidden prompt magic
provider lock-in
opaque database state
premature multi-agent
premature cloud
speculative abstractions
```

---

# 23. First Implementation Task

开始编码前，先完成以下工作，但不要停下来等待用户批准：

1. 审计 Obsidian Plugin 可用 API 和桌面运行边界。
2. 设计最小 Domain Schema。
3. 设计 Markdown/frontmatter representation。
4. 设计 Kernel / Plugin boundary。
5. 设计 State Machine。
6. 设计 Provenance model。
7. 设计 AgentExecutionProvider interface。
8. 设计 Quality Gate。
9. 产出第一版目录结构。
10. 写最小 vertical slice。
11. 用真实 Obsidian Vault 验证完整 MVP workflow。
12. 修复直到验收链完全通过。

优先做一个真正可运行的垂直切片，不要先创建大量空模块。

---

# 24. Product North Star

始终用下面这个问题判断某个功能是否应该加入：

> 这个功能是否让用户更少地管理工具，而更多地只做真正需要人类判断的事情？

如果答案是否定的，不要优先实现。

最终目标不是：

> 帮助用户更快写一篇文章。

而是：

> 让一个人的知识库逐渐具备类似成熟内容机构的生产能力、质量控制能力和经验积累能力。

最终形态：

```text
                    Human
             Direction / Judgment
                      │
                      ▼
                OpenContent
                      │
         Production Control Plane
                      │
     ┌────────────────┼────────────────┐
     ▼                ▼                ▼
 Knowledge          Agents          Tools
     │                │                │
     └────────────────┼────────────────┘
                      ▼
                  Artifacts
                      │
                      ▼
                  Judgment
                      │
                      ▼
                 Publication
                      │
                      ▼
                   Learning
                      │
                      └──────────↺
```

这就是整个项目最本质的目标。