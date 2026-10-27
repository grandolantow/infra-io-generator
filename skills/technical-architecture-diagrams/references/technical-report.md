# 技术报告叠加规则（不是原 Skill 的替代品）

先加载同级独立包 `../technical-diagram-options/SKILL.md`：它提供 selector、generator、规则、公开来源索引、schemas 和合同测试。本文件是额外配色与设计 overlay，不代替该实现。所有路径按统一入口 Skill 根目录解析。

目的：让读者理解机制、过程、资源组织与设计取舍，而不是把每个主题改画成大字号流程框。论文来源并不代表模型分支；PPT 来源并不代表本分支。

## 从核心问题选择图元

| 要回答的问题 | 可选表达 | 必须看见的约束 |
|---|---|---|
| 计算/数据如何移动 | 数据流、功能区、局部展开 | 操作与数据边区分，真实端点/汇合 |
| 多 rank 如何协作 | 分片/拓扑、rank swimlanes、通信时序 | shard ownership、collective 类型、通信前后状态 |
| 缓存与地址如何映射 | memory blocks、token strips、逻辑→物理映射 | residency/lifetime/ownership 不混淆，不把复制画成分片 |
| 调度为何有效 | timeline、队列、阶段对照 | 时间轴、依赖和重叠依据；无数据不画精确时长 |
| mask、量化或变换如何作用 | matrix、数值小例、公式步骤 | 行列含义、维度、变换前后对应；示例值标 illustrative |
| 状态如何更新 | 状态读写、跨步反馈 | 本步依赖与下一步反馈分开 |
| 搜索/推测如何分支 | tree、accept/reject 路径 | 分支条件、剪枝/接受条件 |
| 优势/代价多大 | quantitative chart、受控机制对照 | 数据出处、单位、基线、条件与误差；无数据不造曲线 |

允许组合：例如一张整体通信示意 + 一张 per-rank timeline。不是固定排版菜单；先由事实决定结构。只有真正必要的关系才能成为箭头。

## 视觉偏好与局部修订

- 使用真实矩阵单元、张量片、memory block、token strip、时间条和小组件再组合；避免全是宽大圆角框/大字报。
- 圆角可柔和，但不得掩盖端口/数据方向。适度密集、紧凑布局，减少无意义大留白，不挤到线条文字互相遮挡。
- 矩阵有足够真实信息时可展示 4 行以上；这是密度偏好，不是硬性造行要求。复杂推导拆成数张，一图承担一个主要问题。
- 色彩可清晰丰富但避免大面积重色；不是所有节点灰白，也不是全部饱和色。图例、标签与线型保留不依赖色觉的区分。
- 删去标题式大文字和装饰性标语，缩短辅助注释，不用无限缩字解决空间问题。
- 原图可访问时同时给出原图来源、结果与改动说明。仅参考其信息组织，不抄成不适合当前事实的固定模板。

## 配色与实际实现

PPT 默认 `huawei-plain`，论文和未指定用途默认 `paper-vivid`；`blue-neutral`、`paper-clear` 及自定义可覆盖。主色来源及 exact tokens 共用 `palette-config.md`，图内英文短标签/短注释与可独立阅读的中文长段解释不随配色变化。

```sh
python scripts/route_request.py --intent report --target ppt --request 'PCP communication timeline' --output route.json
python scripts/resolve_palette.py --target ppt --palette huawei-plain --output palette.json
```

第二条中的 palette 应取第一条对应子任务结果；显式自定义必须一并传给 resolver，不能遗失覆盖。使用统一事实 JSON、稳定对象 ID 和真实绘图后端；性能图保留绘图数据与脚本，不承诺现有专用模型模板能自动生成任意机制图。

## 评估

分别检查逻辑清晰、布局舒服、信息密度、语义配色、组件表达和来源正确性；先列可复现问题再局部修正。结构与质量需按当前任务单独核验；路由与合同测试不能证明所有主题均达到参考图质量。

独立报告入口也必须消费共享 `text-language.md` 与 `language-profile.json`；不能依赖仅统一入口加载的 overlay。
