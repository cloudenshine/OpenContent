# 写作技能集成与验收说明

## 当前交付：质量层 1.0.2

在之前 Narrative 真数据/真实图像验证修复与 1.0.1 写作入口接线基础上，继续完成实际质量层修改。OpenContent 应用版本仍为 0.8.0，写作策略单独版本化为 1.0.2。

这次不是把两篇好稿留在包外。短运行时规则已经更新：材料中能改变理解或决定的观察；判断具体承担的选择、代价与边界；让细节解释关系、支撑操作或推动人物行动；人物有自己的需要，情绪由处境产生。末轮保持有内容的个性，不把所有稿子磨成统一的稳妥说明。原简洁 editorial 核心原样保留。

两篇后来获认可的重写，连同相同题目下的首轮两稿、诊断和适用边界，进入随插件分发的 `writing_skills/references/`。默认不注入范文全文：按虚构叙事/分析评论分别供作者选读。教程、产品介绍、短旁白不用评论结构；虚构也不强制局促、尴尬、反转或固定物件收尾。

## 接入和约束

- 通用 draft/critique、工作台 revise、Narrative plan/write/continue/revise/critique 均在真实请求装配处接入
- Narrative 依 Profile 区分虚构与证据约束写作；plan 不做全文精修；critique 不代写；revise 不越过定向范围
- research/distill/discuss/illustrate/cover/market/analyze 等非写作任务不加载
- Claim 原句/ID、引文、数据、代码、链接及人类批准门禁保持；范文不能变事实素材
- huashu-report、Humanizer-zh、oh-story 三份 MIT 来源的 commit、URL、哈希和许可证完整保留
- 未新增收费服务、账号、凭据、工具权限、自动研究或发表

## 为什么保留前面的不满意结果

1.0.0 与原版的第一次匿名模型比较没有明确胜者，1.0.1 与原版也没有明确胜者；随后六类试写仍被用户指出过于寡淡。此前评分不是现在的质量背书。完整首轮六类样稿、任务和清单保留在 `docs/writing-quality-evidence/v1.0.2/prior-six-*`。

之后的《别太大》《谁来发现它没做完》重写得到认可。它们帮助定位问题：前者让人物关系真正影响行动，后者让材料约束一个需要负责的判断。这并不意味着所有文章都必须不和谐、有反转或自称审批者。两篇认可只算这两篇的人工判断，不外推稳定跨题提升。

跨题迁移试写如有附入，沿用最终生产请求的组合指导文本，另换合成任务与输出 schema；独立写作者未看到认可范文；其正文、输入与审阅另存本目录。它仍不是用户已安装 Obsidian 中的真实模型运行，也不是与旧策略随机配对的胜率试验。

## 评测工具修复

旧 `scripts/evaluate_writing.py` 只删除 editorial_guidance 做 baseline，在加入 writing_quality 之后会让控制组仍带新层。本次改为“原简洁核心”对“同一核心 + 当前新增层”：从实际请求尾部精确移除当前补充模块并移除 trace，重装后必须逐字段相等。材料、宪章、主张、schema、原核心完全一致；版本、双方完整请求和各自哈希保存。旧历史结果不冒充这个新对照方案的产物。

可先运行 `python scripts/evaluate_writing.py --prepare-only --output dist/你的新目录`：只生成和核验配对输入，不调用 provider。真实生成需已配置本地 Codex CLI 和相应授权；运行 `--phase review` 的匿名模型评审也不等于人工验收。本次交付不为试写读取凭据或接入新服务。

## 追踪与验证

`v1.0.2/production-prompts.json` 保留三入口 18 条实际装配请求，覆盖 12 个任务/模式组合。里面项目、run ID、token 均来自一次性合成夹具，不是真实 Vault 或账号信息。补充文本哈希与组合指导文本哈希分别标注；后者只含 instructions/editorial_guidance，不冒称整份上下文。已有 request/receipt/attempt 保存实际运行依据。

最终自动验证、代码审阅和迁移样稿结果见 `v1.0.2/software-verification.json`、`code-review.md`、`transfer-review.md`（若该项存在）。捕获 provider / 模拟进程只证明软件路径，不证明文笔。

交付仅为本地可审阅源码、插件安装包、累积补丁与证据；没有远程 push、合并或部署。Linux 可跑内核/HTTP/模拟 DOM/打包测试；Windows DPAPI 与真实 Obsidian 桌面必须单列，不能把环境未覆盖说成通过。
