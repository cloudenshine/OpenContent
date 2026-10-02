# Narrative 市场采集与封面假成功修复

基线：`181dd58079948b679b8d6c229a13623f5a0c5c42`。这是本地修复与验收包，未推送、合并、部署，也未改动用户电脑。

## 改动结果

### 市场数据

- 删除未传 `raw_data` 时自动填充起点、知乎固定作品并返回成功的分支。
- 长篇提供固定官方公开榜单适配器：七猫男频/女频大热日榜首页。插件默认明确选择男频日榜；API 可选择已支持的来源 ID。不是“全网扫榜”。
- 联网采集检查 robots、HTTPS、重定向、返回类型/体积、HTML 结构、连续排名及必填信息。拒绝登录/验证跳转、抓取失败和无法可靠读取的混淆文本，不绕过阻断。
- 导入模式可粘贴按平台分组的 JSON；每条必须有真实书名、正整数 rank、公开来源 URL、带时区的实际 observed_at。导入仅表示用户提供的快照，始终标为未联网核验。
- 长篇每平台至少 3 条、短篇至少 2 条不同作品。重复 URL/作品/排名、空数据、非法数值、缺少来源或未来时间会失败，不静默凑数。
- 原始输入、标准化记录、来源快照及 SHA-256、逐条观测时间、独立分析时间与完整报告保存在 Vault 中。
- 删除固定的短篇“爆款公式”、30/60 天寿命和没有依据的商业表现断言；只输出样本统计与待验证的创作假设。
- 短篇尚无已验证的自动公开采集适配器，支持带来源的导入。起点、番茄、知乎等不在此次已验证的自动支持范围。

### 封面

- 删除无条件写入 1×1 PNG 的实现，调用已有配置的本地 CLI provider。使用现有 `stage=illustrate` 隔离工作目录与能力声明；未配置、不支持生图、工具不可用、空/部分返回均明确失败。
- 不接入新付费 API、不创建凭证、不安装生图服务。实际生成仍取决于用户已有 CLI、登录状态、运行时图片工具和账户额度；代码可用不等于所有本地 CLI 都能生图。
- 新增免费的 Pillow 解码依赖；检查完整 PNG/JPEG 解码、真实像素尺寸、平台最小尺寸、宽高比、文件/像素上限、透明/纯色占位、重复像素以及路径安全。
- 候选图像与不可变运行清单、provider、请求/提示/响应/文件哈希、实际尺寸一同保存。声明的生图工具名称属于 provider 自述，不能单凭 JSON 证明调用过某个工具；本地可证实的是文件、解码与哈希，画面质量需作者审阅。
- 显式测试 provider 的产物显示 `FIXTURE_GENERATED` 与测试标记；不会把测试图像称为生产生图。
- 移除“设为项目封面”只弹出成功通知但未持久化的按钮。当前只生成可审阅候选，不声称自动设为正式封面。

### 实际接线

修复 `/capabilities/execute` 缺少 `Path` 导入、Runtime 找不到 server 的 Jobs/provider、引用不存在 `LocalCodexProvider` 的回退。前端提交真实来源/导入数据、题材与提示，并核对成功回执。失败回执持久化，运行 ID 复用及跨平台路径穿越被拒绝。

## 使用与复核

在独立验收副本中执行，先不要覆盖现有正式 Vault：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/doctor.py --runtime .
.\.venv\Scripts\python.exe scripts/verify.py
```

Linux/macOS 对应解释器为 `.venv/bin/python`。`verify.py` 会让 Node UI→HTTP 桥使用同一个 Python 解释器。

真实公开榜单验收（只联网读取官方公开页面，临时 Vault 默认在完成后清除）：

```powershell
.\.venv\Scripts\python.exe scripts/acceptance_narrative.py --live-market
```

导入自有快照验收：

```powershell
.\.venv\Scripts\python.exe scripts/acceptance_narrative.py --import-json your-snapshot.json
.\.venv\Scripts\python.exe scripts/acceptance_narrative.py --import-json your-short-snapshot.json --short
```

如需保存证据，追加 `--vault "一个新的验收目录"`，不要指向生产 Vault。

真实封面验收必须由已有本地生图条件的环境执行。以下命令会调用已登录的现有 CLI，可能消耗该账户已有额度；本次云端修复没有执行该生成调用：

```powershell
.\.venv\Scripts\python.exe scripts/acceptance_narrative.py --live-cover --provider codex --vault "新的封面验收目录"
```

若 CLI 无生图能力，应看到明确失败和失败回执，不能靠填充占位文件“通过”。成功后仍请人工打开候选检查文字、构图和可用性。

## 验收边界

- 自动测试中的图像是明确标记的测试夹具，用于验证 provider 协议、解码、落盘和失败路径，不是真实 AI 作画验收。
- 本次未在 Windows Obsidian 真机加载插件；UI 通过执行真实插件代码、真实 HTTP 和 Runtime 的集成桥验证。
- 原仓库 3 个公众号凭证测试依赖 Windows DPAPI，Linux 上会报错；同一基线复现相同错误。本修复没有放松加密约束来制造全绿。
- 一次完整回归曾出现已有后代进程存活测试瞬时失败；独立复跑和基线复跑通过。该次失败保留在验收说明中，不能宣称从未失败。
- 公开站点 HTML、robots 和可访问性可能变化；适配器宁可失败，不自动换源或返回样例。代理环境使用已有 HTTPS 代理解析固定官方域名；无代理时做公开 IP 检查，未声称 DNS 地址被固定绑定。

最新具体测试数量与真实联网结果见同包验收结果；`docs/verification.json` 保留完整聚合输出。Linux 上该聚合的 `passed` 应保持 false，直到适用的 Windows 平台测试实际通过。

## 本次最终结果（2026-10-01 UTC）

- Node：46/46 通过，包含 7 项新增 Narrative UI 测试及真实 UI→HTTP→Runtime 导入链。
- Python：204 项，201 通过、3 个上述 Windows DPAPI 平台错误；未将其跳过或伪报全绿。
- 新增重点测试：30 项市场来源/严格数据验证、24 项封面反例、5 项 Runtime/HTTP 接线与路径安全。
- `doctor.py --runtime .`：通过；CLI 登录明确 NOT_CHECKED。
- 真实公网：2026-10-01 14:45:41 UTC，经实际适配器采集七猫男频日热榜 20 条，成功生成来源可追溯报告。HTML SHA-256 为 `41adde2a32f37aab76b47ee206f85db67e0edc8a798577f840d7fe0416434a1f`。
- 真实封面：未运行，不能宣称生产生图已经验证。
- 机器可读摘要：[narrative-acceptance-results.json](narrative-acceptance-results.json)。
