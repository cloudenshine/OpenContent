# OpenContent 0.8.0 — 开发预览，尚不适合公开发布

2026-09-09 交互调整：主入口收敛为 **首页 / 写作 / 发布**。首页说一句想写什么，可直接使用当前笔记；本地 CLI 首次自动发现并启用，沿用已有配置。稿件与对话集中在写作页，详细依据、运行记录与高级维护按需展开。研究依据、改动和验证边界见 [使用体验改造](docs/UX-RESEARCH-2026-09-09.md)。下文带版本号的旧流程说明为历史记录，当前操作以该文档为准。

**发布状态：BLOCKED。** 当前仍是 Windows 桌面开发预览。脚本通过与单次模型调用成功不代表首次使用顺畅或内容质量稳定；真实宿主操作、独立选题评审和新用户试用仍待验收。当前发现、改进与发布标准见 [公开发布差距](docs/PUBLIC-READINESS.md)。

0.8 增加离线环境自检与启动前检查；同一链接、原文/转录文件名关系和高度重合正文会归入来源组，只有一个组时不调用模型。该归组是启发式提示，不证明来源独立或论点正确。旧选题快照需要刷新范围重新生成，历史结果仍保留。

[独立试用说明](docs/TRIAL-QUICKSTART.md) 提供演示仓库、首次使用与回访表。十二轮人工编写语料可用 `scripts/evaluate_ideation.py` 重放；机器执行结果不替代独立评审。详见 [本轮阻断处理](docs/BLOCKERS-v0.8.md)。

0.7 改善基础使用：安装包携带 Python 内核，启动不再要求保留源码目录；选题前可限定目录和 2–60 份资料，默认 24 份；失败任务可检查版本后复用已完成分类。错误在当前操作旁保留，并给出重试入口。运行环境仍需 Python 3.12+ 与依赖，尚不是无需配置的一键安装。

0.6.1 修复真实 60 份资料归纳时的引文抄写失败：模型选择来源内的原文片段编号，程序保留 Markdown 和换行取回原文；未知编号或跨来源编号仍拒绝。旧失败任务保留，更新后在选题窗口刷新范围重新生成。

v0.5.1 默认在右侧栏打开，启用插件后自动挂载；旧的主窗口面板在下次打开时迁移。安装脚本要求目标是已存在的 Obsidian Vault，避免路径拼错时静默创建新仓库。

工作入口：**目标推荐材料 → 跨资料综合选题 → 项目指令台 → 改稿与配图**。创建项目时填写目标即可推荐相关本地 Markdown。“从仓库发现新选题”则先归纳资料中的主题、方法与观点，再让本地 CLI 从互补、矛盾、方法迁移和共同缺口中提出新问题。每个候选至少结合两个来源组的资料，展示读者收益、组合逻辑、论证计划、待补证项与已有项目差异；原文依据折叠展示。用过的资料可以产生新角度，重复的是问题而不是资料。详见 [v0.6 跨资料选题](docs/CORPUS-IDEATION-v0.6.md)。

项目内可持续发送讨论、改稿和配图指令。对话保存在 `OpenContent-Workspace/`，最近 12 轮与当前材料一起交给本地 CLI。改稿先展示提案，应用后原批准失效；不会自动发表。可检测并启用已登录的 Codex / Claude 原生 CLI，不覆盖其模型和推理配置。Codex 配图请求可调用其已有图像工具；没有能力时明确显示方案，只有实际 PNG/JPEG 文件才算已生成。

详细流程、CLI 命令与限制见 [v0.5 项目工作台](docs/PROJECT-WORKBENCH-v0.5.md)。

依据 `OpenContent — Codex Implementation Charter.md` 重建。以 Content Project 为中心，在 Obsidian 内运营材料、知识、论点、证据、草稿和审查。外部 Agent 负责工作，Kernel 决定状态，用户作最终判断。

保留章程的编辑内核：**Material → Knowledge / Idea → Research / Claim / Evidence → Artifact → Critic → Needs Judgment → 人工 APPROVED**。0.4 在原生捕获与编辑门禁之上，加入跨项目材料库、来源变化检查、项目计划、微信公众号草稿/发表回执、失败恢复，以及人工确认的反馈复用。

适合定期写教程、研究说明与知识通讯的桌面作者。当前是可试用版本，仍需 Python Kernel；尚未上架社区目录或获得真实用户留存数据。[市场与产品决策](docs/MARKET-STRATEGY.md)、[四周试点](docs/PILOT-PLAN.md)、[0.3 验收](docs/VALIDATION-v0.3.md)。

数据保存和可选 Agent 的外部处理范围见 [隐私说明](PRIVACY.md)。本地启动 Agent 不代表模型离线运行。

产品目标是完整内容生命周期。v0.4 已实现公众号协议链与本地闭环，真实账号投递仍待本地账号配置和实际联调；模拟协议通过不代表真实发表。安装后从“发布与反馈”连接账号，见 [公众号接入指南](docs/WECHAT-SETUP.md) 与 [v0.4 验收](docs/VALIDATION-v0.4.md)。对 Gemini Notebook / Open Notebook 的补充比较及范围纠偏见 [完整生命周期决策](docs/NOTEBOOK-COMPETITION-AND-FULL-LIFECYCLE.md)。

## 立即体验

工作区保留历史 `validation-vault/` 与旧版真实 Obsidian 1.13.7 记录；它们不是 0.8 的宿主验收。打开 OpenContent 的 **Judgment Inbox**，可查看《让知识与内容有据可查》的五轴评价与证据。旁边的合成软件验收项目只验证门禁。

本机实际使用的 Vault 为 `F:\Obsidian_vault`，插件更新需安装到该路径；`validation-vault/` 的安装不代表用户仓库已更新。旧版代码、数据和报告保留在 `archive/pre-charter-v0.1/`，不参与当前运行。

## 安装到指定 Vault

需要桌面 Obsidian 1.8+、Python 3.12+、PyYAML 6.0.3、Mistune 3.2.0。插件不需要 npm 构建。

```powershell
cd "D:\Workspaces\codex_work\OpenContent"
python -m pip install -r requirements.txt
python scripts/install_plugin.py --vault "你的 Vault 路径" --configure
```

在 Obsidian 的社区插件设置中启用 OpenContent。命令面板提供工作板、项目、审查、材料库和发布与反馈入口。首次打开时，先离线检查所选 Python、依赖、内核和 Vault 写权限，检查通过后 Kernel 才在后台启动；插件设置可以指定 Python、项目目录和 Codex **原生可执行文件**。Codex 留空时仍能手动维护完整领域链。

安装脚本将三份界面文件及 `kernel-0.8.0/` 内核写入选定 Vault 的 `.obsidian/plugins/opencontent/`；替换前备份至 `.opencontent/install-backups/`，失败时尝试恢复原文件。`--configure` 将运行目录设为该内核，保留其他项目与账号配置。脚本不替你关闭安全模式。不要同时为同一 Vault 手动启动另一服务；服务会拒绝重复实例。

## 日常操作

0.4 增加的后半程：批准稿 → 准备公众号草稿 → 预览并确认 → 微信草稿回读 → 再次确认发表 → 查询实际发表结果 → 记录反馈 → 接受经验 → 创建下一项目。计划日期是管理信息，不会自动发表。来源变化会阻止旧版本投递；材料库可比较、刷新并跨项目复用。详细边界见 [实施契约](docs/LIFECYCLE-IMPLEMENTATION.md)。

1. 打开普通笔记，可选中一段，用命令 **捕获当前笔记 / 选区**（或编辑器/文件右键菜单）保存到现有项目或直接新建。捕获不调用模型、不改写源笔记；同项目相同来源与内容自动去重。Web Clipper 笔记的 `source` URL 会随材料保存。
2. 通过 **继续上次内容项目** 或首页 **继续工作** 回到写作。需要更多材料时使用 Project View 的 **选择 Vault 材料**。首页优先呈现待判断稿件，完整阶段总览可展开。
3. 点击 **预览材料并开始创作**，核对材料、共同规则及发送范围，再选择 **开始创作**。Kernel 从当前阶段继续提炼、论证、起草、Critic；每一步先验证再保存。预览后资料改变会在首个 Agent 调用前拒绝启动。重审与失败重试也先展示当前范围。
4. **Judgment Inbox** 显示需要决定的草稿。WARN/FAIL 时 Accept 禁用；打开 **Inspect Evidence / Diff**，沿 Claim 检查 Evidence、Knowledge、Material，在原生编辑器中修订后 Challenge Again。
5. 五轴 PASS 后，人工输入决定人和理由。Accept 绑定当前内容与依赖版本；Reject 保留理由并请求修订。修改正文、材料、主张、项目目标或 CONTENT.md 后，旧批准不再有效。
6. Inspector 的 **交付 Markdown / Ailu** 仅在当前版本已批准时可用，生成并打开供读者阅读的 Markdown。它移除内部主张标记，不自动附加来源脚注；溯源与审查保留在本地，作者主动写入的链接和引用保留。可交给其他工具继续处理；Ailu 实际导入与平台发表尚未实测。微信正文采用相同规则，见 [v0.4.2 输出规则](docs/READER-OUTPUT-v0.4.2.md)。

交接输出在 `OpenContent-Exports/`，校验收据在 `.opencontent/handoffs/`。重复导出相同版本无副作用；交接文件被手工改写后拒绝覆盖。来源 URL 查询串与片段会移除，依赖这些参数的链接需要作者补正；正文中自行写入的敏感信息也请在交付前检查。

运行任务时可以继续操作 Obsidian。任务区支持取消、诊断和从当前 Vault 继续；模型失败不等于内容完成。插件关闭会请求 Kernel 取消其拥有的任务并退出，重新启动后的中断记录可重试。

无 AI 时，用 Project View 的“手动补充与状态推进”、原生 Markdown 编辑器、Inspector 的人工 Critic Review 完成相同门禁链。高级手动对象表单需填写关系 ID；日常自动流程不要求逐对象填写表单。

## 数据布局

```text
Vault/
  CONTENT.md                         # 可编辑的共同宪章
  OpenContent/
    Material/<id>.md
    Knowledge/<id>.md
    Idea/<id>.md
    Project/<id>.md
    Project/<id>/CONTENT.md           # 可选项目补充宪章
    Claim/<id>.md
    Evidence/<id>.md
    Artifact/<id>.md
    Review/<id>.md                    # Critic 和人工决定均为 Review
    Publication/<id>.md               # 投递意图、远端回执、人工记录、反馈与决定
  .opencontent/
    runtime.sqlite3                  # 仅 jobs、运行状态、写锁
    runs/<id>/                       # 请求、响应、stdout/stderr 诊断
    transaction.json                 # 写入期间临时恢复 journal
```

**Markdown 是内容真源，不是数据库导出物。** 人工编辑后下次读取即生效。SQLite 不保存权威文章、知识或批准；删除插件与重建数据库不会删除这些内容。Job 收据和执行日志仍需随 `.opencontent` 备份，丢失它们会丢运行诊断，不会丢领域内容。常规备份请备份整个 Vault。

稳定 ID 关系及类型字段见 [Schema](docs/SCHEMA.md)。删除 ID、破坏 YAML、重复 ID、断开溯源会阻止推进；不要把错误清理成假成功。可在原生编辑器修正。写入失败有 journal；如果恢复时发现外部编辑，保留现场并报告冲突。

## Kernel 与 Provider

```powershell
python -m opencontent --vault validation-vault board
python -m opencontent --vault validation-vault inspect <object-id>
python -m opencontent --vault validation-vault serve --codex "Codex 原生可执行文件路径"
```

`serve` 只监听 127.0.0.1，默认随机端口，启动时输出 JSON 连接信息。随机 token 是本地控制凭据，不应贴到公共页面。插件通过 `requestUrl` 使用 Bearer token；浏览器 Origin 与错误 Host 被拒绝。

Provider 统一接口为 `run / resume / cancel / capabilities`。Domain 内无具体 Agent 判断。Codex adapter 使用已安装的原生 CLI，不覆盖模型和推理强度。每阶段使用新的 `--ephemeral --sandbox read-only` 执行；写作与 Critic 不共享会话。`resume` 明确是新尝试，不宣称恢复原生会话。

本阶段研究限于**用户已捕获材料内的论证与证据整理**，没有自动联网抓取。Provider capabilities 描述该受限工作模式，不能当作操作系统权限沙箱证明；Codex 自身的工具与访问权限仍由其运行配置控制。进程组管理负责取消/超时后终止拥有的子进程。

Skill 从用户配置的路径发现 `SKILL.md`，最多 8 份、每份 50 KB。默认不扫描整个用户目录、不复制第三方技能；请求包含共享 CONTENT.md、所选技能和所选项目资料。

CLI 的 `apply <json-file>` 支持 `create_project/add/advance/review/decide`；同名参数与 Kernel 方法一致。HTTP 路由、状态门禁和示例见 [Schema](docs/SCHEMA.md)。

## 范围和验证边界

- 0.4 包含人工确认的公众号投递与反馈复用；不含定时自动发表、自动统计、正文图片上传、多 Agent 编排、模型管理、语义检索、团队、云和移动端。
- 五轴审查是带理由的判断，不是事实真伪或原创性的数学证明。精确引文匹配只能证明摘录存在；重要事实是否完整由 Critic/人工明确判断。
- CONTENT.md 的八个章节会传给 Agent；程序直接检查章节、Forbidden Patterns 列表、主张标记、原文摘录、80 字符下限、五轴结果与版本绑定。自由文本政策依赖审查解释，不是假装支持任意自然语言规则执行。
- 本地单用户信任模型，决定人是署名，不是登录鉴权。拥有 Vault 写权限的人可以修改 Markdown；本产品不提供防同机管理员伪造的数字签名。
- 单服务写锁与哈希比较防止常见并发覆盖。外部编辑器不参与 Kernel 锁，最终哈希检查与原子替换之间仍有很小的竞态窗口。多文件 journal 保证可恢复，不承诺跨应用分布式事务。
- 自动生产按新对象追加；当前自动 Critic 支持每个 Project 一个 Artifact。手动对象和审查可处理额外 Artifact。未做大型 Vault、移动端、团队或多平台稳定性验收。

运行 `python scripts/verify.py` 重现当前自动测试。当前工作流证据见 [0.4 验收](docs/VALIDATION-v0.4.md)；先前真实 Codex 四阶段证据见 [0.2 验收记录](docs/VALIDATION.md)，它不是本版重新调用模型的收据。架构取舍见 [ARCHITECTURE](docs/ARCHITECTURE.md)。

## 回退

停用插件后，Markdown 继续留在 Vault。需要回退插件版本时，从 `.opencontent/install-backups/` 恢复三份插件文件；配置单独保留。旧版应用整体在 `archive/pre-charter-v0.1/`，其数据库结构与本版不同，应在旧目录独立运行，不能把旧 DB 覆盖进新 Vault。

本次市场改进前的 0.2 源码快照另存为 `archive/pre-market-v0.2.zip`。回退时配套恢复 Kernel 与插件，不覆盖当前 Vault；新增 Material 字段兼容旧读取，交接稿是独立 Markdown。0.2 不提供新的捕获与交接 API。

0.4.1 默认仅送入公众号草稿箱，个人未认证账号在微信后台完成发表后登记链接。API 发表需在账号配置中明确启用，并仍受微信权限限制；详见 [个人账号权限结论](docs/WECHAT-PERSONAL-ACCOUNT.md)。

0.8 安装器按版本写入 `kernel-0.8.0/`，旧内核原目录保留，避免运行服务的工作目录锁阻止更新。ZIP 手工安装仍使用 `kernel/`；插件优先选择与当前版本匹配的随包内核，外部自选源码目录保持显式选择。升级后的当前 Obsidian 进程不会热替换：下次停用再启用后才加载新版。回退先停用插件，再恢复同一备份中的界面文件和 data.json，旧版本内核目录已保留；同版重装若该版内核正占用，仍需先停用插件。
