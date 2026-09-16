# OpenContent

Obsidian 桌面插件：把本地笔记做成可追溯、可审查、由作者最终批准的内容项目。

首页写一句想写什么，即可用当前笔记开始。写作页集中稿件与对话，发布页处理交付与公众号草稿。材料、知识、主张、证据、草稿和审查都保存在 Vault 的 Markdown 里；Python Kernel 负责状态与门禁，外部 CLI（Codex / Claude）负责生成，人工批准才算完成。

当前版本 **0.8.0**，适合桌面作者试用。尚未上架 Obsidian 社区插件目录。MIT 许可。

## 它做什么

- **从笔记到成稿**：捕获当前笔记或选区，提炼知识与主张，起草文章，独立 Critic 五轴审查，作者亲自批准。
- **证据必须来自原文**：研究阶段绑定真实 Knowledge / Material；引文必须能在材料正文中定位。改写数字、否定词或编造来源会被拒绝，不会被“修好”成另一条证据。
- **选题走正式内核**：本地扫描只召回候选素材组。真正选题走 `/ideation`：片段编号、来源组、分类与综合。采用候选会创建绑定证据快照的项目，而不是只把一句话塞进输入框。
- **作者始终做最终决定**：改稿先出提案再应用；正文、材料或宪章变化后旧批准失效；不会自动发表。
- **数据在你的仓库里**：Markdown 是内容真源。SQLite 只保存任务与锁。卸载插件不会删除文章。

工作链：

```text
Material → Knowledge / Idea → Claim / Evidence → Artifact → Critic → 人工 APPROVED
```

主入口：**首页 / 写作 / 发布**。

## 环境要求

- Windows 桌面 [Obsidian](https://obsidian.md/) 1.8+
- Python 3.12+
- PyYAML 6.0.3、Mistune 3.2.0（见 `requirements.txt`）
- 可选：已安装并登录的 Codex 或 Claude 原生 CLI（无 AI 时仍可手动维护材料与审查）

## 安装

克隆本仓库，安装依赖，再把插件写入已有 Vault：

```powershell
git clone https://github.com/cloudenshine/OpenContent.git
cd OpenContent
python -m pip install -r requirements.txt
python scripts/install_plugin.py --vault "你的 Vault 路径" --configure
```

然后在 Obsidian 中关闭安全模式，启用社区插件 **OpenContent**。首次打开会离线检查 Python、依赖、内核和 Vault 写权限；通过后 Kernel 才在本机回环启动。

安装脚本会把界面文件和 `kernel-0.8.0/` 写入 `.obsidian/plugins/opencontent/`，替换前备份到 `.opencontent/install-backups/`。`--configure` 使用随包内核，并保留其他项目与账号设置。不要同时为同一 Vault 再手动启动一份 Kernel。

试用包与演示仓库见 [独立试用说明](docs/TRIAL-QUICKSTART.md)。

## 日常使用

1. 打开一篇笔记，首页写目标读者问题；可勾选“使用当前笔记”。
2. 需要跨资料选题时，用命令面板 **从仓库发现新选题**。先核对目录与篇数，再综合生成候选；采用后会创建绑定来源快照的项目。
3. 在写作页预览材料范围，开始创作。Kernel 按 distill → research → draft → critique 推进；每步先验证再保存。
4. Judgment Inbox 显示待判断稿件。WARN/FAIL 时不能批准。打开证据链与 Diff，在原生编辑器修订后再审。
5. 五轴 PASS 后，填写决定人与理由。Accept 绑定当前正文与依赖版本。
6. 已批准版本可导出读者 Markdown，或准备公众号草稿。草稿复制与正式成品复制是两条路径：未批准稿可以复制预览，但不能当成已定稿发布。

无 AI 时，用项目视图的手动补充、原生编辑器和人工 Critic Review 走同一套门禁。

## 数据布局

```text
Vault/
  CONTENT.md                         # 可编辑的共同宪章
  OpenContent/
    Material/  Knowledge/  Idea/  Project/
    Claim/     Evidence/   Artifact/  Review/  Publication/
  OpenContent-Workspace/             # 项目对话
  OpenContent-Exports/               # 已批准读者稿
  .opencontent/                      # 任务、诊断、写锁（不是内容真源）
```

稳定 ID 与字段见 [Schema](docs/SCHEMA.md)。隐私范围见 [PRIVACY.md](PRIVACY.md)。

## 设计原则

- **证据先于正文**：无效 Knowledge ID 不会被改绑到项目里的另一条知识；引文必须是材料原文切片。
- **研究底稿与读者成品分离**：research 可保存问题、观察、竞争解释与缺口；这些进入后续写作与审查，但不作为读者正文。
- **表达可以自然，事实边界不能放松**：默认仍检查主张原句。opt-in 的 Artifact v2 允许忠实转述，但必须有正文片段绑定，并由 Critic 确认语义保真。
- **Kernel 是权威，插件是界面**：批准、导出、发表状态以 Kernel 当前版本检查为准，不以页面上一次渲染为准。

## 开发与验证

```powershell
python scripts/verify.py
python scripts/doctor.py --runtime .
```

当前自动套件覆盖 Node 语法、39 项前端/引擎测试、Python 编译与 112 项内核测试。架构见 [ARCHITECTURE](docs/ARCHITECTURE.md)。

## 当前范围

OpenContent 在已捕获材料内做论证与证据整理，不自动联网抓取。公众号链路需要本机配置账号，模拟协议通过不代表已经发表。自动 Critic 目前限定每个项目一个 Artifact；额外稿件用人工审查。

尚未完成：社区插件目录上架、无 Python 的一键分发、多产物自动审查、大规模 Vault / 移动端 / 团队验收。已知缺口与发布标准见 [公开发布准备度](docs/PUBLIC-READINESS.md)。

## 文档

| 主题 | 文档 |
| --- | --- |
| 安装与试用 | [TRIAL-QUICKSTART](docs/TRIAL-QUICKSTART.md) |
| 项目工作台 | [PROJECT-WORKBENCH-v0.5](docs/PROJECT-WORKBENCH-v0.5.md) |
| 跨资料选题 | [CORPUS-IDEATION-v0.6](docs/CORPUS-IDEATION-v0.6.md) |
| 公众号接入 | [WECHAT-SETUP](docs/WECHAT-SETUP.md) |
| 隐私 | [PRIVACY.md](PRIVACY.md) |
| 架构 | [ARCHITECTURE](docs/ARCHITECTURE.md) |

## 许可

[MIT](LICENSE)。第三方声明见 [NOTICE.md](NOTICE.md)。
