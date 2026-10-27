# Skill 与依赖核对清单

检查范围：本次会话可见个人 Skill（执行端与云端目录）、个人停用目录、当前项目工作文件、历史提交清单及已保存的 PPT 工作流设计说明。此清单不宣称遍历了用户所有电脑、Dot 或 GitHub 私仓。

## PPT 与技术绘图

| 名称 | 证据与状态 | 本次处理 |
| --- | --- | --- |
| `technical-architecture-diagrams` | 当前唯一确认安装的自有 Skill；v0.9.7 | 完整源码在 `skills/technical-architecture-diagrams/` |
| `drawio-skill` | 用户此前要求收藏/列入提交清单；外部项目 `Agents365-ai/drawio-skill` | 收入外部 Skill 目录，不冒充自研；未复制/安装上游完整代码 |
| `plantuml-skill` | 用户此前要求收藏/列入提交清单；外部项目 `samonysh/plantuml-skill` | 收入外部 Skill 目录，适用于 UML/时序图；未复制/安装上游完整代码 |
| `huawei-html-ppt` | 项目使用的外部 PPT 主流程与样式参考 | 收入外部 Skill 目录；没有声称已完成宿主集成 |
| `ppt-workflow` | 已读取 `PPT_Workflow_Codex_Brief.md`，明确为待实现设计基线 | 设计稿已归档为 [ppt-workflow-design.md](ppt-workflow-design.md)，不创建空 Skill 冒称已实现 |
| `build-technical-presentation` | 历史对话提及的旧主流程 Skill | 当前安装目录及项目中未找到源码，登记为待恢复；不把设计稿当成其源码 |
| `baoyu-slide-deck` | 工作流设计中借鉴过布局探索思路 | 登记为参考，不加入生产执行依赖 |

## 当前绘图 Skill 内部完整性

已包含事实契约、四类结构配方、双配色解析与适配、draw.io runtime、Inkscape 测量、TikZ 校准源、HTML/PPT 适配说明、40 条人工评价、100 图索引、历史失败与迭代证据。MiniMax 双配色、竖向主干及独立 MSA 展开在仓库样例目录。

draw.io、Inkscape、TikZ、ELK、Penrose 是工具/后端或研究路线，不因曾试用就各自成为独立 Skill。ELK/Penrose 仍非默认生产路线。40/31/33/34 是结构配方编号，不是另外四个 Skill。v0.4～v0.9.x 是同一 Skill 的版本，不重复安装。原 v0.4 规范包（包含事实、评价、case-card、review-record、迭代与评测模板）完整存档在 `docs/history/v0.4/`，与 `skills/` 活跃安装目录分开。

检查到的旧同名目录仅剩脚本，无 SKILL.md；工作区的 v0.4 与 forward-test 副本属于历史或测试快照，没有当作第二个活跃版本提交。

## 其他来源

其他工程仓中的 Skill 不属于本绘图项目，未混入此库。系统/插件提供的 Presentations、PDF、文档、Library、浏览器等不属于本项目自有代码，也不复制。

## 全量范围的界限

本仓库已经覆盖当前可取得源码的绘图 Skill，并补齐 PPT 相关收藏/计划项。用户其他工作仓与本地安装未接入本环境时，不能据此宣称“所有个人 Skill 均已收齐”。
