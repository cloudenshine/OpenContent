# Charter MVP 验收报告

验收日期：2026-09-08。对象：OpenContent 0.2 重建版。旧版 20 项测试与旧运行记录不算作本轮证据。

## 结果

**本轮 MVP 工程路径通过**：Markdown 真源、独立 Kernel、薄 Obsidian 插件、真实 Codex 四阶段执行、五轴审查、可追溯 Gate、人工决定界面，以及故障/恢复路径。

真实文章停在 REVIEWING，由用户最终验收；自动化点击 Accept 使用的是明确标注的合成软件样本。没有把合成审查写成真实内容质量结论，也没有把通过测试等同于用户认可。

## 章程 A–H 对照

| 条件 | 状态 | 本轮证据 |
|---|---|---|
| A 数据所有权 | PASS | 停用插件并移出其安装目录后，真实 Obsidian 仍可读取 26 份领域 Markdown、识别其类型。移走 SQLite，创建全新数据库，内容哈希全部不变，两个 Project 与已有批准依据重建成功。随后恢复原数据库和插件。见 data-ownership.json、obsidian-interactions.json |
| B Agent 独立 | PASS（接口层） | Domain 无具体 Provider 条件分支；同一 Kernel 由替代 FixtureProvider 完整跑通四阶段。只有 Codex 做过真实运行认证；未宣称其他产品兼容已实测 |
| C Traceability | PASS | 真实文章 5 项 Claim 各有 Evidence，并经 Knowledge 回到捕获 Material；Inspector 展示支持/反对证据和反向使用者。坏引文、缺来源、缺 Claim 标记均会阻止 Gate |
| D State correctness | PASS | 跳级、Agent 注入 APPROVED、无审查批准、仅改 Markdown 声明 state、过期审查均不能产生有效批准。最新 Critic 与人类决定绑定同一依赖版本 |
| E Human judgment | PASS（本样本） | UI 只需定义目标、选择材料和启动一次任务；四个阶段自动运行到待判断。真实五轴 PASS 后仍等待用户；合成样本在真实 UI 点击 Reject/Accept 得到不同状态 |
| F No hidden dependency | PASS | 无 Provider 的 HTTP 服务正常维护 Project；纯人工路径完整推进至 APPROVED；插件移除且 runtime 重建后知识与门禁仍可读取 |
| G Obsidian responsiveness | PASS（小 Vault） | 真实 Codex RUNNING 前后，完成 Inbox/Project 两次渲染与原生 Markdown 编辑器打开，耗时约 778ms；不是键盘延迟基准。真实宿主 1.13.7、安装器 1.8.10。见 obsidian-responsiveness.json |
| H Failure behavior | PASS（已列故障） | 引文错误/坏结构无领域写入；CAS 冲突不覆盖外部改动；多文件写故障回滚；恢复检测外部编辑时保留现场；进程超时/取消杀死拥有的子进程；失败重试与重启 INTERRUPTED 有收据 |

## 自动验证

命令：`python scripts/verify.py`。Node 语法检查、Python 编译、**22 项 unittest 全部通过**。原始输出、执行时间和源码哈希保存在 `verification.json`。

覆盖：完整状态链与 runtime 重建、No AI 人工链、越级/伪造状态、引文与来源错误、政策/正文/依赖变化、WARN/不完整事实/作者自审、反对证据、拒绝与重审、重复 ID/坏 YAML/路径越界、两写者版本冲突、journal 回滚与外部编辑保护、Provider 替换/失败重试/取消/重启、HTTP 身份/Origin/Host/坏请求、真实进程 IO/非零退出/JSON 错误/输出上限/超时与子进程清理。

这些测试使用临时 Vault；模型响应 fixture 明确标为软件测试，不代替真实 Agent 证据。

## 真实 Codex 运行

Project：`2c63e2129aea492f9545574e2e6a844f` — 真实 Agent · 从材料到编辑判断。

Job：`5ff162b60c894266aa9f58cc5a05473c`。由真实插件“推进到 Needs Judgment”按钮启动。未覆盖模型或推理强度；每次执行为独立 ephemeral 调用，具体模型配置不作为本轮已验证声明。

| 阶段 | Run ID | UTC 起止 | 结果 |
|---|---|---|---|
| distill | 22d1067008004cc2a8747cc8db9bd843 | 08:50:03–08:50:47 | COMMITTED |
| research | aeed940aacf34eec9bcda8c05f21716c | 08:50:47–08:51:52 | COMMITTED |
| draft | b9c10aa07dc14f08ab578091d9785218 | 08:51:53–08:52:34 | COMMITTED |
| critique | f5ac05aeeabc4375902d2021838d1c62 | 08:52:35–08:53:18 | COMMITTED |

产物《让知识与内容有据可查》：`9db0eba7dddc4a07a46d5df7ffdf45d8`。五轴 PASS，确定性 Gate PASS，`approved=false`，Project/Artifact 均 REVIEWING。总运行约 195 秒。材料为本地明确标注的设计备忘录；不是自动联网研究，也不是外部研究结论。

`runtime-evidence.json` 保存收据、阶段历史、当前 Gate 和请求/响应文件哈希。原始请求与响应在专用 Vault 的 `.opencontent/runs/`，未打入发行包。

## 真实宿主交互与恢复

- 使用 `--user-data-dir=<工作区>/.validation-profile` 启动独立 Obsidian，加载已安装更新包 1.13.7；用户 F 盘 Vault 与原 Obsidian 进程未修改/关闭。
- 通过真实 DOM 按钮创建 Project、打开材料选择弹窗、勾选笔记并启动任务。验证页面不是浏览器中仿造的插件界面。
- 合成 Artifact `82c7bb494c1548e6950bd8751a034b7c`：Reject → revision inbox；Accept → APPROVED。决定人显式为“自动化软件验收（合成样本）”。
- 使用 Obsidian `Vault.process` 修改合成草稿，Gate 变为 BLOCKED；Inspector 的 Diff 显示新旧正文。带比较条件恢复原始文本后批准恢复有效。
- 真正移出插件安装文件、重建 runtime 后读取 Markdown，随后恢复原运行收据及插件。插件重新加载可自动启动 Kernel，保留上述两个项目状态。
- 四个界面已实际渲染；截图为 `obsidian-board.png`、`obsidian-inbox.png`、`obsidian-inspector.png`。窗口为 1024×800 的桌面宿主；未做手机验收。

## 验证中发现并处理的问题

1. Modal 表单字段 `build`/`title` 与宿主内部实现冲突，弹窗未显示。改为 `buildForm`/`formTitle` 后，在真实宿主完成创建、选择材料与决定表单验证。
2. 旧安装器缺少 Obsidian CLI 启动器；没有把帮助命令失败包装成 CLI 成功。改用隔离 Obsidian 实例的 renderer 调试接口验证真实宿主。
3. 首次在受限环境启动的宿主不能持续访问所需运行能力；经批准在同一专用配置中重新启动，完成实际 Agent 执行。未关闭用户现有应用。
4. 批准后的外部修改需要展示有效状态与原始声明的差异；Board/Inspector 计算有效 REVIEWING，而不偷偷覆盖用户 Markdown 历史。

## 实际限制

单本地信任用户、单服务、每项目自动 Critic 一个 Artifact。Reviewer 为署名而非团队身份。自然语言政策由审查解释，程序门禁只执行文档列出的确定性规则。研究仅在捕获材料范围内，Skill 为显式文件发现，resume 为新尝试。没有自动发布/分析/反馈学习/云/移动端。未做大型 Vault 压力测试、真实作者长期试用或第二种真实 Agent 认证。外部编辑器与 Kernel 的最后写入检查之间仍有很小竞态，已提供 journal、哈希与冲突保留；不声称是跨应用分布式事务。

## 自评

按 agent-self-evaluation 技能：Accuracy 4/5（真实宿主/真实 Agent/故障证据齐全，但不把语义质量当客观事实）；Completeness 4/5（章程 MVP 覆盖，长期使用和大 Vault 未验收）；Clarity 4/5（数据真源、合成样本与用户批准分开）；Actionability 4/5（可安装插件、启动说明、可重跑验证与恢复脚本）；Conciseness 4/5（文档较多，但入口集中在 README）。平均 4.0/5。优先改进：在真实日常项目中验证人工决策负担和较大 Vault 的扫描延迟。
