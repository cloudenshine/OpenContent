# 从人的写作习惯重新组织 OpenContent

本次依据用户明确要求研究 Open Design 与 AILU，再调整交互。原则：用户描述意图、看结果、提出修改；程序承担环境发现、资料关联、状态推进和版本检查。复杂性不能靠让用户学习内部对象来消化。

## 证据与边界

- Open Design 固定在 `00c12c6451d9248c11a5c5122714e4d0b9f5709c`。阅读官网产品流程、HomeView、ChatComposer、firstRunGuide、agentModelSelection，以及 App.onboarding-agent-autoselect 测试。研究副本与 LICENSE 在 `ux-research/opendesign/`，不进入运行包。
- AILU 固定在 `ac04758b765985ccaa4a4248da25de1b1ee4a25f`。核对 README、运行时发现、当前文档上下文、发送与停止、内联编辑、发布预览与失效处理。没有运行 AILU，也没有把旧版研究当作当前体验实测。
- 两个竞品的结论来自一手源码与官方资料；没有宣称穷尽全部代码、实际完成竞品安装或证明新用户一定容易使用。
- OpenContent 的观察来自本轮源码检查、DOM 交互测试和真实 Obsidian 1.13.7 隔离实例。没有改动用户的 `F:\Obsidian_vault`。

## 值得学习的机制

| 机制 | 一手证据 | 本项目决策 |
|---|---|---|
| 从目标开始，项目结构由系统生成 | [Open Design HomeView](https://github.com/nexu-io/open-design/blob/00c12c6451d9248c11a5c5122714e4d0b9f5709c/apps/web/src/components/HomeView.tsx)、[官方产品流程](https://open-design.ai/) | 首页只要求一句写作意图，自动生成文章标题和默认读者；自选资料入口仍保留。 |
| 当前文档自然进入上下文，可明确移除 | [AILU chatView 387–507](https://github.com/mcncarl/ailu/blob/ac04758b765985ccaa4a4248da25de1b1ee4a25f/src/ui/chatView.ts#L387) | 显示“使用当前笔记：名称”及复选框；提交绑定笔记字节哈希，内容改变则拒绝旧快照。 |
| 发现已有工具，减少重复配置 | [AILU discovery 47–173](https://github.com/mcncarl/ailu/blob/ac04758b765985ccaa4a4248da25de1b1ee4a25f/src/runtime/discovery.ts#L47) | 启动时优先显式配置、其次上次选择、首次才自动选择发现的工具。发现可执行文件不等于登录验证；不偷偷发送测试提示。 |
| 自动默认值不能覆盖用户选择 | [Open Design onboarding 测试 210–252](https://github.com/nexu-io/open-design/blob/00c12c6451d9248c11a5c5122714e4d0b9f5709c/apps/web/tests/components/App.onboarding-agent-autoselect.test.tsx#L210) | 上次工具失效时提示修复，不能静默换供应商。Open Design 当前测试还明确禁止在首次引导未完成时抢选 Agent，不能概括为任何时候都自动选择。 |
| 对话、稿件、修改在同一工作空间 | [Open Design 产品介绍](https://github.com/nexu-io/open-design/tree/00c12c6451d9248c11a5c5122714e4d0b9f5709c)、[AILU inlineEdit 91–121](https://github.com/mcncarl/ailu/blob/ac04758b765985ccaa4a4248da25de1b1ee4a25f/src/ui/inlineEdit.ts#L91) | 写作页合并稿件与对话；改稿仍需采用，旧版本提案仍不能覆盖新正文。选区内联修改尚未实现，不把整篇改稿冒充内联编辑。 |
| 发送与停止共用主按钮，键盘与按钮条件一致 | [AILU chatView 591–653](https://github.com/mcncarl/ailu/blob/ac04758b765985ccaa4a4248da25de1b1ee4a25f/src/ui/chatView.ts#L591)、[Open Design ChatComposer 3237–3257](https://github.com/nexu-io/open-design/blob/00c12c6451d9248c11a5c5122714e4d0b9f5709c/apps/web/src/components/ChatComposer.tsx#L3237) | 运行时发送变停止；空输入不发请求，Ctrl/⌘+Enter 与按钮共用禁用状态。生成不完整时不能显示成成功。 |
| 出错保留输入和工作，而非重新开始 | [Open Design ChatComposer 草稿存储](https://github.com/nexu-io/open-design/blob/00c12c6451d9248c11a5c5122714e4d0b9f5709c/apps/web/src/components/ChatComposer.tsx#L6813) | 本次已保证刷新与发送失败保留输入；创建成功而启动失败时直接留在保存的文章中。未发送输入跨应用重启恢复尚未实现。 |
| 预览与交付共用当前稿，旧检查自动失效 | [AILU publishingStudioView](https://github.com/mcncarl/ailu/blob/ac04758b765985ccaa4a4248da25de1b1ee4a25f/src/ui/publishingStudioView.ts#L1459) | 保留内容哈希、批准、发布确认和回读核验；把内部依据放到详情，不能为了少一步而静默发表。 |

## 当前问题与实际修改

| 原来的负担 | 本次修改 |
|---|---|
| 七个同级导航，让人自己判断下一步 | 首页、写作、发布三个主入口；材料库、待处理稿件、连接设置进“更多”。 |
| 创建前要求项目名、目标、读者，然后再选材料 | 首页一句话开始；当前笔记默认勾选，可取消。无笔记先讨论，有笔记自动保存资料并发起起草。标题和读者在自选资料流程中成为可选设置。 |
| 已发现 CLI 仍需要展开面板手动启用 | 首次自动启用已发现的本地工具，沿用模型与推理配置。 |
| 项目页铺开八类对象，讨论另开入口 | 稿件与对话同页；资料详情、规划、手动对象维护折叠。 |
| 选择材料后再经过一次“预览并开始”弹窗 | 写作页显示资料数量；点“写成初稿”直接提交当前版本，后端继续校验版本。 |
| Accept / Artifact / Quality Gate 等内部术语 | 常用入口改为“确认定稿”“当前稿件”“检查已通过”；技术日志保留在运行记录。 |
| 正文打开不断分栏 | 改为复用已有正文标签；没有时开标签，不再横向拆分编辑区。 |

## 验收方式

- `python scripts/verify.py`：语法、界面契约、后端流程、版本冲突、恢复、打包等全量检查；最新结果见 [verification.json](verification.json)。
- [writing-ui.test.cjs](../tests/writing-ui.test.cjs)：一句话开始、资料范围、失败保留输入、避免重复创建、停止、快捷键和直接继续创作。
- [test_cli_bootstrap.py](../tests/test_cli_bootstrap.py)：首次自动发现、保留显式配置、已选工具失效不切换、无工具/配置损坏时保留手动工作能力。
- [native-verification.json](ux-research/native-verification.json)：真实 Obsidian 的 11 项交互检查。项目与资料通过真实 Kernel HTTP 保存；模型任务入口被明确截获并模拟失败，因此没有模型执行或成功生成证据。
- [native-tab-verification.json](ux-research/native-tab-verification.json)：最终正文标签复用检查，连续打开两次前后均为一个 Markdown 标签，侧栏无横向溢出。
- [首页截图](ux-research/home-native.png)、[写作页截图](ux-research/writing-native.png)。截图来自本次隔离仓库，不是设计稿冒充产品。

## 尚未完成的产品体验

这次完成了入口与默认写作流程的改造，不代表整个产品已经达到“小学生都会用”。首次安装仍依赖 Python 和依赖包；生产仍使用固定阶段与整段响应；编辑器内的选区修改、流式结果、未发送草稿跨重启恢复、发布页的进一步收敛，以及无指导的新用户实测，仍需要继续做。公开发布状态仍为 BLOCKED。

本次没有将新版本安装到用户日常仓库，也没有发送消息、实际发表或切换用户模型。源码目录没有 Git；修改前界面与核心连接代码备份在 `archive/ux-before-20260909/`。回退时只恢复代码与插件文件，保留用户文章。
