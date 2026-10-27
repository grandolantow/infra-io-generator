# 技术架构图绘制 Skill v0.4 — 初版规范包

## 本包是什么

根据当前对话四批40条参考图评价和用户补充，新整理的轻量Skill规范与后续验证计划。目的为交给Codex或其他执行Agent实施；不是一个已经接通并验证的绘图产品。

主入口：`SKILL.md`。阅读结果概览：`SUMMARY_CN.md`。实施交接：`HANDOFF-CODEX.md`。

## 已完成

- 转录40条用户评价：24好、10一般、6差。
- 区分明确偏好、候选解释和工程约束。
- 定义四种布局配方与多方案策略。
- 提供语义契约、案例卡、反馈记录与评测任务模板。
- 提供数据与文件一致性检查脚本。

## 未完成 / 不应误读

- 未包含40张原图，未重新核验历史论文名称、年份、图号与图片来源。
- 未获得和检查旧的“24条候选规则”实现包；本包不是对那一包的已验证覆盖更新。
- 未实现通用布局/渲染器，未生成本Skill的实际图示，未测出优于旧方案的结果。
- 未安装到Codex，未修改或合入 `huawei-html-ppt` 仓库。
- 未制作第五批参考图；后续优先验证成图，只有出现具体覆盖缺口才补新参考。

## 评价数据的边界

40是展示记录数，不是去重原图数。01/18以及04/26、06/25有重复或疑似重复关系，需原图资产进一步核对。整体评分不能直接归因到颜色、连线或某种模块。

## 文件结构

```text
SKILL.md
SUMMARY_CN.md
HANDOFF-CODEX.md
references/
  rules-v0.4.md
  layout-recipes.md
  evidence-and-limits.md
  iteration-plan.md
data/
  ratings-40.json
  rules-v0.4.json
templates/
  diagram-spec.json
  case-card.json
  review-record.json
eval/
  tasks-template.json
scripts/
  check_bundle.py
VERIFICATION.md
manifest.json
```

## 本地检查

在本目录执行 `python scripts/check_bundle.py`。此命令仅校验规范文件、样本转录、规则引用与模板的一致性，不验证图片视觉效果、技术事实或绘图质量。

规则版本与执行模型版本应分开记录。实现时先读目标仓库现状，复用其已有渲染与导出能力，不因本规范推翻现有系统。
