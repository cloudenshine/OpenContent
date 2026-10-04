# 三阶段交付验证（最终冻结版本）

验证日期：2026-10-04。基线为 `3c63ba76a873f5a04522853a8b81abc09836a04d`。
交付分支：`feat/wesight-delivery-20261004`。应用版本保持 0.8.2；本次是源代码改造提交，不是重新发布同版本 Release。

## 结果

| 检查 | 实际结果 |
|---|---|
| 完整 `python scripts/verify.py` | 退出 1；269 次 Python 执行 / 248 个唯一测试，266 次通过；仅 3 个既有 WinError 1314 权限失败 |
| Node UI / engine | 49/49；原有 47 项保留 |
| `lint` / `lint:compat` / `lint:controls` | 通过；lint 保留 1 条既有建议 warning，无 error |
| build / doctor | 通过；doctor 不代表 CLI 登录已验证 |
| 真实 Obsidian 1.13.7（独立合成 Vault） | 安装、启用、三主题预览、富文本处理、目标选择、Unicode 选区与图文导出通过 |
| 完整包 / 解压后冷启动 / 安装后 doctor | 6 项通过；资源齐全、ZIP CRC 有效，不含字体或依赖目录 |
| 可复现读者案例 | 3 个主题 HTML、3 页 1080×1440 PNG、可编辑文案/页面计划、来源资源与清单；重复渲染一致 |
| 源码稳定性 | 全量测试期间无漂移；打包与原生检查后逐文件哈希仍与测试快照一致 |

机器可读摘要见 [THREE-STAGE-DELIVERY-RESULTS.json](THREE-STAGE-DELIVERY-RESULTS.json)；完整套件摘要见 [verification.json](verification.json)。原始日志、故障记录和合成 Vault 留在本机 `.execution/`，不会提交公开仓库。

Python 基线原有 224 次执行（含 21 次既有重复导入执行），本次增加 45 个独立测试。没有通过重复导入 TestCase 膨胀新增数量，也没有 skip、xfail 或放宽断言制造全绿。

## 已收口的最后审查问题

| 问题 | 修复与回归 |
|---|---|
| 重算 payload_hash 后可替换未批准正文 | 全部冻结构建字段、批准身份及正文逐项比对权威构建；确认前和写入前复核；篡改不得触发 draft/add |
| 仅保留 build_id，修改其他构建字段或图片清单 | 对比完整构建快照，不信任自报 build_id；拒绝未经批准的资源上传 |
| Material 被误用为渠道母稿 | 母稿构建器验证 Artifact 类型；文件直接改写也在质量门禁中标为 STALE/BLOCKED |
| 删除母稿导致整个面板异常 | 缺失、格式错误、跨项目、递归依赖给出 STALE 诊断；面板仍可用，正式输出被阻止 |
| 重复句子无法进行准确局部改稿 | 使用原文范围与当前 base_hash 定位，可只改第二处；过期范围仍拒绝 |
| 图片字节借用非图片后缀导出 | PNG/JPG/JPEG 文件名白名单与真实完整解码共同验证 |

以上对应正常 discover 中的 `test_final_delivery_boundaries.py` 和 `test_three_stage_final_boundaries.py` 共 16 项，不是只存在于临时审查脚本中的检查。

## 明确保留的三项环境限制

- `test_output_path_rejects_internal_symlinks_and_windows_forms`
- `test_import_rejects_symlink_hardlink_and_nonregular_file`
- `test_linked_images_and_lexical_ancestor_links_fail`

本机测试进程缺少创建 Windows 符号链接的权限（WinError 1314），在制造测试对象时失败。基线复现同样情况。本次未更改操作系统权限、启用管理员模式或关闭相关测试。Junction 回归通过不能替代这三项，所以 `verification.json` 的 `passed` 保持 false。

## 验收范围

原生检查仅操作此前建立的独立合成 Vault，安装的内核字节与冻结源文件逐一核对一致。剪贴板采用真实按钮/HTTP/处理逻辑，但在 OS 写入边界截获以保留用户剪贴板；不能声称跨应用粘贴已实测。

测试中的模型响应、材料、审查和作者批准均明确为合成 fixture；PNG 是确定性排版，不是 AI 作画。已逐页检查合成输出中的文字和布局，不代表真实作品的内容或审美验收。

没有真实微信账号上传/草稿/发表测试，没有小红书平台写入，没有实际模型生成质量验收，没有部署到生产 Vault，也没有发布 Release。`LOCAL_BUNDLE_READY` 仅表示本地完整包。

复现案例：`python scripts/acceptance_three_stage.py --output .execution/new-case-directory`。输出目录须不存在且在仓库内部；不会调用真实模型或账号。
