# v0.10.0 整合来源与边界

2026-10-27，北京时间。

## 同一谱系，不降级覆盖

- 当前仓库基线：[`a6f4d16830a8dece954193ed356c122ea60296f6`](https://github.com/grandolantow/infra-io-generator/tree/a6f4d16830a8dece954193ed356c122ea60296f6)，v0.9.7。
- [v0.9.1 配色与完整备份页](https://chatgpt.com/space/page_aac42a66824c8191901c770c16369952) 实读；本地 ZIP SHA-256 `c4dc7a3660b18a6fdafc2994903d0dbc08fa686b510f553cc6c6bf008d8b7f50` 与页面一致，50 个文件。其 SKILL.md 名称也是 technical-architecture-diagrams，不是第二个独立实现。
- 整合前 v0.9.7 完整 Skill 已作本地 tar.gz 快照，SHA-256 `2bf79da516b19e2f2c53e9f72e2c5448d5fc934f46adfe29e55ccc8f3087fbf7`。可公开恢复的权威备份是上面的基线 Git commit；无需把完整依赖再次复制进仓库。
- `model-architecture.md` 完整保留 v0.9.7 正文（只新增分支说明），包括专业绘图后端、事实/编辑验收、失败边界与引用。所有既有资产和脚本实现不变。
- report 分支恢复历史用途配色意图，并归纳[第四轮最终用户反馈](https://chatgpt.com/space/page_0dd741031ae88191ab69e5e2051a06fe)的密度、紧凑、组件表达、减少大字报等方向。保留 TVM 一般、推测图只部分认可的边界，不把历史反馈扩大为全认可。

## 本次新增什么

统一入口 + model/report 按需加载；轻量 route_request 辅助；报告机制图规则；21 项路由回归；README 用例。复用既有 token 和 resolver，不改变 legacy auto，也不新增渲染依赖。

## 未宣称完成的事

没有新一轮模型训练、历史 50 篇全量重绘、10 题留出评测、图像审美评测或新后端完整渲染。路由是 Agent 语义判断加保守关键词辅助，非通用理解/生成编译器。关键词会有误判和漏判，必须复核；否定句自动退回复核，不强行猜测。

仓库分发包与个人安装实例分别管理；本提交不静默覆盖另一个对话正在修改的个人 Skill。安装时比较并备份已有本地版本，复制整个目录。
