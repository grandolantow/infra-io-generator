# 外部 Skill 收藏

用户曾要求把 draw.io 与 PlantUML 纳入收藏/提交清单。下表保留它们与 PPT 主流程的入口；这些上游不是本仓库作者自研代码，也没有自动安装或导入其最新实现。

| 项目 | 入口 | 定位 |
| --- | --- | --- |
| draw.io Skill | https://github.com/Agents365-ai/drawio-skill | 原理、方案和架构图的外部 Skill；本仓库默认执行链路已有独立原生 Graph 导出脚本 |
| PlantUML Skill | https://github.com/samonysh/plantuml-skill | UML、时序/执行流程的外部 Skill；不替代当前论文架构图主后端 |
| Huawei HTML PPT | https://github.com/LookAround0301/huawei-html-ppt | 外部 HTML PPT 工作流/样式来源；宿主完整集成尚未验证 |

登记状态为 `catalog-only`：未在本次整理中核实上游当前提交、许可证或安装行为。以后引入源码时应保留上游身份、版本和许可证，再实际验证；不能把历史试用记成当前版本已测试。

`external-skills.json` 保存同一份机器可读清单。收藏入口存在不等于完整代码已收齐，详情见 [Skill 核对清单](skill-inventory.md)。
