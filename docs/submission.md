# 提交准备

当前提交目标为 `grandolantow/infra-io-generator`，分支为 `main`。2026-10-27 在 dot 云端确认目标为空仓库且连接账号有写权限，基础检查通过。

历史整理记录曾以 `Songzeyu666/infra-io-generator` 为目标且连接只读；`reports/source-inventory.json` 保留当时核验快照，不代表当前目标或权限。

提交前需核对所连接账号对目标仓库有写权限；只读连接可以完成检查和本地复现，不能执行远端首个提交。

账号切换完成后，在实际提交环境核对当前身份和目标仓库；浏览器、GitHub 连接器和本机 gh CLI 的登录可能分别管理。不要在聊天中粘贴 PAT、密码、私钥或恢复码。

首个提交建议包含 Skill、仓库工具、样例、检查摘要和第三方声明。忽略 build、缓存、浏览器、依赖树和内部 QA 截图。正式发布由仓库所有者决定项目许可证；draw.io 的第三方许可证单独保留。

推荐首个提交标题：`Add editable technical architecture diagram skill and reproducible examples`。
