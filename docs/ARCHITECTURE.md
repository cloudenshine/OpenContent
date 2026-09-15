# Charter 重建决策与实施边界

本轮依据根目录《OpenContent — Codex Implementation Charter.md》重建。该文档是用户指定的产品规格；验收事实以运行证据为准。旧版完整保留在 `archive/pre-charter-v0.1`，不作为新系统运行依赖。

## 编码前决策

1. **Obsidian API**：桌面 CommonJS 插件使用公开 `Plugin`、`ItemView`、`Modal`、`PluginSettingTab`、`Vault`、`Workspace`、`requestUrl` API。`FileSystemAdapter.getBasePath()` 提供桌面 Vault 路径；manifest 声明 desktop-only。Node 仅用于启动独立 Python 服务，不在插件内运行 Agent 工作流。官方定义：https://github.com/obsidianmd/obsidian-api/blob/master/obsidian.d.ts 。Obsidian CLI 的 eval/plugin/screenshot 能用于真实宿主验收：https://obsidian.md/help/cli 。CLI 需要 1.12+ installer，须实测本机可用性。
2. **最小 Schema**：仅 Material、Knowledge、Claim、Evidence、Idea、Project、Artifact、Review、Publication 九种对象。共有 `oc_id/type/title/project/created/derived_from`；类型特有字段由 Kernel 验证。所有对象正文为 Markdown，YAML frontmatter 保存结构字段。稳定 ID 解析关系，正文附可点击文件链接。
3. **真源**：`OpenContent/<Type>/<id>.md` 与 Vault/Project `CONTENT.md` 是唯一领域真源。SQLite 只存 jobs/运行日志及写锁。清除 runtime 数据库后从 Markdown 直接读取，无内容恢复数据库步骤。
4. **边界**：Plugin → authenticated loopback JSON API → Python Kernel → Provider。CLI 复用 Kernel。浏览器来源不可获得随机服务 token；插件只连接本机，不向公共网络开放。单个服务绑定一个 Vault。
5. **状态**：CAPTURED → DISTILLED → IDEA → RESEARCHING → ARGUMENT_READY → DRAFTING → REVIEWING → APPROVED；PUBLISHED/LEARNING 保留为手动 publication tracking，MVP 不自动发布或学习。每次迁移重新检查材料、提炼、论点、主张证据链、草稿、审查及人工决定。frontmatter 的状态声明本身不构成通过凭据。
6. **溯源**：Knowledge→Material，Claim→Knowledge，Evidence→Material 且引用原文，Artifact→Claim，Review→Artifact 的内容及依赖哈希。支持与反对证据明确分开；有反对证据必须在审查中处理。Inspector 反向查询使用者。
7. **Provider**：`run(request, workspace, cancel_event)`、`resume(...)`、`cancel(...)`、`capabilities()`。默认 Codex 适配器实现，Domain 不识别具体运行时。resume 是可诊断失败任务的新尝试，绑定新输入快照，不谎称支持 provider 原生 session continuation。Skill 从配置路径发现 SKILL.md 并在请求中引用，不复制第三方 Skill 入项目。
8. **Judgment**：Evidence/Logic/Originality/Voice/Utility 五轴 PASS/WARN/FAIL + 理由。确定性 Gate 验证引用、链路、内容契约、审查新鲜度；语义判断由 Critic/人工承担，不能被分数代替。五轴通过后仍需明确人工批准。Agent 响应仅可生成指定阶段的候选数据，不能提交批准。
9. **持久性**：写前快照比较；单 Kernel 写锁；多文件写 journal 可恢复。人工外部修改、删除、重复 ID、坏 YAML 均使验收失败并显示诊断。外部编辑器不参与锁，最后一次 hash 检查与原子替换之间仍有极小竞态；自动生产采用追加新对象，尽量不覆盖正文。
10. **目录**：`opencontent/` 独立内核、`plugin/` 可直接安装插件、`templates/CONTENT.md` 可编辑宪章、`tests/` 领域与故障验证、`scripts/` 安装与真实验收、`validation-vault/` 本工作区专用 Obsidian Vault、`docs/` 证据。不会直接改用户 F 盘现有知识库。

## 为什么不沿用旧架构

独立 Web 表单+SQLite 内容真源违背章程数据所有权；将其继续扩展会增加迁移成本。完整重写领域/存储/UI，复用已验证的进程树生命周期工具即可。选择 Python+PyYAML 和无需打包的 JavaScript 插件，减少当前环境新增工具链；代价是首次使用需 Python，本阶段不伪装成独立桌面安装包。

## 验收计划

逐项验证 A–H：卸载/删 runtime 后 Markdown 完整；替换 Provider 无 Domain 改动；双向溯源；跳级/伪造 done/过期审查拒绝；一次任务自动走到 Needs Judgment；No AI 手动路径；真实 Obsidian 中运行任务时 UI 继续响应；超时/取消/重启/坏输出/并发编辑不伪造成功。测试 fixture 的批准仅作为软件门禁验收，实际文章最终判断保留给用户。

## v0.4：公众号及反馈

lifecycle.py 管理来源快照、跨项目复用、计划及人工经验。publishing.py 管理持久化投递意图、确认、恢复与反馈入口所用回执；publishing_adapters.py 只实现当前所选 WeChat 官方接口。正文渲染使用固定版本 Mistune；本地预览 iframe 禁止脚本、表单、网络与顶层导航。身份、正文、批准版本和草稿快照共同绑定投递意图。credentials.py 封装用户 DPAPI / 环境变量。

保留薄插件与 Kernel 结构；没有引入任务服务器、CMS、向量数据库或新增领域类型。用户明确指定首个渠道后，取消了未启用的 WordPress 适配草案，避免维护无当前需求的第二套接口。网络期间不持有 Vault 锁；本地提交仍沿用既有 journal/CAS。

具体状态和能力边界以 [v0.4 实施契约](LIFECYCLE-IMPLEMENTATION.md) 和 [微信接入指南](WECHAT-SETUP.md) 为准。旧版“无发布自动化”的表述仅适用于原 MVP 基线。
