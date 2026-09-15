# v0.5 项目工作台

v0.6 已替换本页旧版的“逐篇笔记生成选题”逻辑，当前流程见 [跨资料选题](CORPUS-IDEATION-v0.6.md)。目标推荐材料和项目指令台继续保留。

## 用户路径

1. 工作台 → 创建 Project → 填写目标。停止输入 500 ms 后自动推荐笔记，展示相关词、原文片段及已有项目关联；勾选后一次提交项目与材料快照，原笔记不变。
2. 工作台 → 从仓库发现新选题，或同名命令。v0.6 先分类提炼再跨资料综合，允许复用已有材料，按问题与论点检查重复；展开排除结果可继续已有项目。
3. 项目 → 讨论 / 改稿 / 配图，或命令“项目指令台：讨论、改稿与配图”。每次选择 CLI 与任务类型后发出自然语言指令；可取消运行任务，失败指令可带回输入框重新发送。
4. 改稿返回完整提案，核对当前正文与提案后点“应用改稿（原批准失效）”，随后可点“重新审查这篇稿件”。旧正文存入 Artifact 的 versions。旧批准失效，材料或稿件变化后旧提案不能覆盖新内容。
5. 配图返回方案和实际文件两种结果。方案可复制；实际文件导入 `Attachments/OpenContent/<project>/` 并展示。默认不擅自插入正文，可复制图片 Markdown。公众号正文图片上传仍未接入，插入图片后需在微信后台排版，不能声称 API 图文闭环已完成。

## 本地 CLI

指令台会检测本机 Codex、Claude 的原生可执行文件，显式启用后保存 Vault 的 CLI 选择。复用用户已有登录、默认模型、推理配置；不安装 CLI、不读取或展示认证文件。Codex 讨论/改稿使用只读执行；配图使用本次独立运行目录，允许调用现有图像工具。Claude 当前适配器关闭工具，支持讨论、改稿和配图方案，未承诺直接生图。

项目对话历史由 OpenContent 传入，不伪称原生 CLI session resume。完整对话是可读 Markdown，重启后恢复；上下文携带最近 12 轮，早期约定若需长期强制执行，应写入 CONTENT.md。生产流水线也接收最近对话中的用户编辑方向，助手建议不成为事实证据或人工批准。

```powershell
python -m opencontent --vault D:\YourVault providers
python -m opencontent --vault D:\YourVault discover --goal "知识溯源"
python -m opencontent --vault D:\YourVault discover --ideas
python -m opencontent --vault D:\YourVault history PROJECT_ID
python -m opencontent --vault D:\YourVault talk PROJECT_ID --message "请换一个开头" --mode revise --provider codex
python -m opencontent --vault D:\YourVault talk PROJECT_ID --message "为第二节生成流程图" --mode illustrate --provider codex
```

`talk` 独占该 Vault 的 Kernel 服务锁。插件已运行时使用指令台；不要再启动第二个 Jobs 所有者。发现和读取命令不执行模型。讨论的常规时限沿用配置，配图至少允许 480 秒；取消或超时会终止所属 CLI 进程树。

## 检索边界

目标推荐材料仍为本地中文双字词和英文词项检索，按词项频率、标题相关性排序，可解释、无需向量库。v0.6 的选题综合使用两阶段 CLI 推理；语义重复判断仍可能误判或漏判，排除理由可见。

排除隐藏目录、下划线目录、OpenContent 领域对象及生成目录、附件、node_modules、链接目录；最多扫描 3000 篇、总计 30 MB，单篇 500 KB，界面显示截断。目标推荐查询仅在本机发生；选题综合在点击开始后发送最多 60 篇资料摘录及既有项目摘要，详见 PRIVACY.md。创建时复核笔记字节哈希，变化时拒绝旧选择，避免部分创建。

## 验证边界

自动回归覆盖相关性选择、重复排除、越界路径、失效快照、对话持久化、旧提案拒绝、批准失效、图片方案与文件区分、取消和 HTTP 鉴权。完整结果见 verification.json。真实 CLI 验收另存私有运行目录，软件 fixture 不冒充真实生图。实际 Obsidian 宿主的新界面交互尚需验证；本轮没有把 JS 语法检查写成宿主 UI PASS。

本机真实 Codex 已完成两轮对话，第二轮正确复用第一轮约定，历史重启读取通过。真实配图首轮触及 150 秒通用超时；独立提高配图时限后，新一次请求生成并导入了 1254×1254 PNG，已查看文件并核对哈希。摘要证据见 workbench-runtime-v0.5.json。Claude 的原生程序与参数已检测，未执行真实模型请求。
