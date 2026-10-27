---
name: technical-architecture-diagrams
description: 绘制有来源、可编辑的 AI Infra 模型架构图与技术报告图。根据语义目标路由到模型主干/模块结构，或机制、通信、内存、时序与定量解释；混合任务拆分后共享事实。支持 draw.io、Inkscape、按需 TikZ 和可调配色。
---

# 技术图示：统一入口

执行版本：v0.10.2。统一入口调用两个独立实现：technical-architecture-diagrams 用于模型架构，technical-diagram-options 用于机制与技术报告；现有模型后端和资产保留。

## 先决定要解释什么

按用户希望读者理解的关系选分支，不按文件格式、论文来源或 PPT/paper 选分支：

| 语义目标 | 分支与必读规范 |
|---|---|
| 模型全貌、层级主干、Attention/MoE 等模块组成及其连接 | `references/model-architecture.md` |
| 机制如何工作：并行通信、调度时序、内存/KV 映射、算法步骤、量化推导、性能与取舍 | 先读 `../technical-diagram-options/SKILL.md`，再读 `references/technical-report.md` overlay |
| 同时解释模型位置和内部机制/实验 | 拆成两类子图，各读相应规范；共用事实、术语、来源版本和对象 ID 映射 |
| 只有“画 Attention”“做张 PPT”或模型名字 | 信息不足，不凭名字猜结构。先给架构/机制两种简短选择；如上下文已有明确目标则沿用，无须重复询问 |

“技术报告中的模型结构图”仍走模型分支；“论文中的 KV cache 映射”仍走报告分支。一个 MoE 模块连接图与一个 MoE dispatch 通信图可以属于不同分支。混合图不强制三栏，也不为填满页面添加解释框。

先记录 `intent`、`target`、`palette`、必要事实及依据。可运行 `scripts/route_request.py` 得到保守的关键词建议与配色结果；它不理解完整自然语言，否定、引用、上下文含糊时要求语义复核，不能替代 Agent 判断。用 `--intent model|report|mixed` 记录复核结果。未知意图返回 `needs_clarification`，不默默生成模型框图。

## 原报告能力的实际入口

report 子任务使用 `../technical-diagram-options/scripts/select_options.py` 从 task JSON 选择结构；按其 schemas 和 generation contract 制作 diagram IR，再由 `../technical-diagram-options/scripts/diagram_tool.py` check/render 导出。用户问题不是 diagram IR，不能把路由建议当作已经完成生成。运行接口示例见仓库 README；安装必须保留两个同级 Skill 目录。model 仍使用现有专业后端，不以报告示例生成器覆盖。

## 配色独立配置

- **model**：保留 v0.9.7 行为，PPT/论文均默认 `paper-clear`。
- **report**：采用用途默认，PPT → `huawei-plain`；paper/未指定 → `paper-vivid`。
- **mixed**：默认分别解析子图；若需要统一风格，显式选择同一 palette，不隐式把模型改成报告配色。
- **显式颜色覆盖 > 显式 palette > 分支与用途默认**。换色不改变事实、布局、节点 ID 或语言。

共用 `references/palette-config.md` 的 token 与适配规则。旧 `scripts/resolve_palette.py` 保持兼容的 model 默认；报告不能直接依赖它的 auto，必须通过路由结果的显式 palette 调用。新路由脚本也可输出完整 resolved tokens。`custom` 的基础色来自相应分支默认。

## 共用事实与交付契约

先读取 `references/spec-contract.md`。固定论文/官方实现版本及图号，区分事实、推断、未知；不能因风格需要造矩阵数值、性能曲线或通信操作。图上必须可见核心事实，不只写进 metadata。

默认语言 profile 为 `diagram-en-prose-zh`：图中功能标签、短注释与箭头说明英文，可独立阅读的长段解释中文，术语/缩写/模型名/公式/变量保留英文符号。两分支必须读取 `references/text-language.md`，并使用 `scripts/check_language.py`；按语义角色而非矩形包含关系判定，不能把“可中文”当任选。密度来自真实图元而非大段文字；保持正常字号，复杂推导分步拆图。颜色承担语义但不是唯一编码。

按 `references/golden-backends.md` 使用 draw.io 结构母版、Inkscape 精修 SVG，复杂公式/LaTeX 才按需 TikZ。矩阵、时序和图表仍交付可编辑原生对象/数据源，不把整图位图称为可编辑。使用已有运行时实际渲染；缺依赖注明未测，不以手写 SVG 冒称已跑 draw.io。

交付事实清单、可编辑源、展示图和检查结果；HTML 可离线查看。嵌入 PPT 时再读 `references/html-ppt-integration.md`，独立验收容器适配，不先把所有图压成 16:9。多方案应有真实组织差别，不把换色或改圆角当结构创新。

先核验技术/可见事实，再检查端点、遮挡、字体、留白和实际导出折点，再做审美对照。原生对象可编辑、SVG 文字可编辑、GUI 拖动分别记录；没做标未测。只有用户反馈可标用户认可，测试通过不是美观或泛化通过。

接口与适用边界见 `references/integration-provenance.md`。路由测试不等于图像质量或泛化评测。
