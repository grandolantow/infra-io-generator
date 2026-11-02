---
name: technical-diagram-options
description: 兼容技术机制绘图入口；默认委托 FigGenie 原生工作流，从唯一 SVG 输出图片或可编辑 PPTX。原候选选择器与 draw.io 实现作为 legacy 保留。
---

# 技术机制绘图兼容入口

新任务读取并执行同级 `../technical-architecture-diagrams/SKILL.md`，使用同一 FigGenie 绘图流程和 output_format，不再默认生成 3–4 版或 PDF。Intake、语义设计、SVG、检查与导出复用上游。

语言仍为 **diagram-en-prose-zh**，详见 `../technical-architecture-diagrams/references/text-language.md`。机制图根据实际流程、映射、通信和状态选择结构，不机械采用竖向模型主干。

旧 scripts/select_options.py、diagram_tool.py、schemas、参考和样例完整保留，显式 legacy 请求可继续调用。原入口文档见 docs/legacy/figgenie-migration/technical-diagram-options.SKILL.md。legacy 的多方案、PDF 和 diagram IR 不用于新 FigGenie 路径，不建立第二套坐标或独立 PPT 引擎。
