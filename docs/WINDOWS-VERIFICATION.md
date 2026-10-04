# Windows 完整回归与符号链接权限

三个既有测试会创建真实文件符号链接、目录符号链接和硬链接，以验证工作区和导入边界。普通 Windows 进程若没有创建符号链接的权限，且系统未开启开发者模式，创建夹具就会报 `WinError 1314`，安全断言尚未执行。

采用仓库的独立 Windows 验证入口，通过标准 UAC 授权仅提升本次测试进程。测试结束后进程退出，不修改系统注册表、开发者模式、账号权限、目录 ACL 或 UAC 设置。不需要以管理员身份运行 Obsidian 或日常插件。

在仓库目录执行：

```powershell
.\scripts\verify_windows.ps1 -PythonExe "C:\Program Files\Python312\python.exe" -Elevate
```

Python 解释器必须安装 `requirements.txt` 的固定依赖。脚本保留所选解释器，不自动安装依赖或改用另一套环境。已经有符号链接权限的普通进程可省略 `-Elevate`；否则返回 `BLOCKED` 与处理方法。UAC 被拒绝或验证失败时，入口返回非零退出码。

入口依次确认真实文件符号链接、目录符号链接和硬链接，然后运行原先失败的三项测试、完整 Python 回归、完整 Node 回归及能力模块 HTTP 流程。不会跳过或替换原有断言。预检链接只在临时目录创建并清理，验证流程使用测试数据。

每次结果保存在新的 `.execution/windows-verify-时间戳/` 中，包括 `report.json`、完整测试清单、日志和 SHA-256。测试失败、执行数与清单不符、出现跳过项、或受检查源码和测试文件在运行期间发生变化，均不能报告通过。仓库原有 `docs/verification.json` 和 `scripts/verify.py` 保持不变。

测试清单按每个测试的实际执行次数逐项比对，包括现有重复加载；不会将相同总数视为相同覆盖。`package.json` 纳入文件指纹，Node 测试命令在验证开始时固定。最终复验摘要及可核对日志见 [Windows 验证结果](WINDOWS-VERIFICATION-RESULTS.json)。

微软官方说明：[CreateSymbolicLinkW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createsymboliclinkw)；[进程令牌权限的调整范围](https://learn.microsoft.com/en-us/windows/win32/secbp/changing-privileges-in-a-token)。当前进程缺失的权限不能通过 `AdjustTokenPrivileges` 新增。

完整套件通过只证明当前环境的自动回归结果；原生 Obsidian 重新加载、真实模型调用与用户最终体验仍需要各自的验收证据。
