---
name: technical-architecture-diagrams
description: 使用 FigGenie 原生流程绘制有来源的 AI Infra 技术图，融合个人偏好和精选样例；从唯一 canonical SVG 输出图片、原生可编辑 PPTX 或两者，不重复设计、不建立第二套坐标。
---

# FigGenie 驱动的技术图示

默认 `output_format: image`；“可编辑 PPT”选 `pptx`，“两种都要”选 `both`。
`display_intent: paper | presentation` 与输出格式独立；这是单张技术图，不是整套幻灯片制作。

## 一次设计，两个导出目标

1. 读取用户材料、约束及 `config/figgenie.json` 的精选偏好。按需读取既有参考记录，保留来源与授权边界；不复制 FigGenie 图库或字体到本仓。
2. 找到用户安装的 FigGenie checkout，核对配置中固定 revision。读取其原生 SKILL、Intake、brief/spec、参考检索、measure_text/place_text、SVG、检查及 PPTX 规范。使用原生工具，不自建并行设计器。
3. 一次技术理解写入 `brief.md`、原生 `spec.json` 和 `plan.md`。记录事实与推断、箭头意义、分支条件、前提；仅源码相关任务记录实际 repository/commit/path，不建通用审计器。
4. Agent 生成并修订 **唯一 `fig.svg`**。它是最终坐标、路径、样式、文字、层次、稳定 ID 和绘制顺序的唯一来源；spec 保存技术结构意图，禁止新造重叠 scene.json。
5. 使用上游 check.py 完成 spec validate、lint、浏览器 PNG；实际看图后修订。paper 按印刷尺寸检查；presentation 在设计时增大字号和间距，并按目标观看尺寸看图，不能机械放大印刷默认字号。
6. 冻结 SVG 后调用 `scripts/figgenie_export.py`。导出只调用上游，不执行绘图 Agent、不重复布局。image 得 SVG+PNG；pptx 得原生对象 PPTX；both 同 hash 派生两者。内部保留 brief/spec/plan/check/manifest。
7. PPTX 必须跑上游 pptx_check，解包核对 text/shapes/groups/connectors/freeforms，并用真实 PPT 渲染器渲染查看。结构通过不等于视觉通过。未运行如实标 `not_run`，失败不得称验收完成。

```bash
python scripts/figgenie_export.py /path/to/fig.svg \
  --spec /path/to/spec.json --upstream /path/to/FigGenie-paper-diagram-skill \
  --output-format both --display-intent presentation --out /path/to/new-delivery
```

封装只依赖 Python 标准库；image 不导入或安装 python-pptx。上游绘图依赖按其文档单独安装，pptx/both 才需 python-pptx；公式的原生 OMML 另需 Node/MathJax 和 Office XSL，缺失明确记录文本降级。不会自动安装依赖。禁止整图栅格化冒充可编辑 PPTX。

## 个人偏好

浅底论文图；模型主干＋有意义的局部机制展开；真实数据流、残差、分支与反馈；克制配色和圆角。可选 `huawei-plain` 素雅灰蓝。精选样例 #31/#40 为主要结构参考，#33/#34 作为局部机制备选，按现有 reference records 的事实和授权边界使用。

语言沿用 **diagram-en-prose-zh**：节点、图内标题、箭头短标签英文，独立长解释中文。详见 `references/text-language.md`。这不是强迫任意机制采用模型主干布局。

## 修改与诚实边界

修改先回 brief/spec/fig.svg，重渲染后重新导出所请求格式。稳定 ID 尽量保留，移动模块同时调整相关路径，无关模块不变。不得直接改生成 PPTX 再反推 SVG；PPT 原生对象可编辑不等于拖动后语义路由自动更新，手改 PPT 不同步 SVG。

默认拒绝非空输出目录，避免覆盖人工改动；仅用户明确授权时用 `--overwrite`。源文件永不由导出器覆盖。manifest 记录 source_svg_sha256、固定上游 revision、参数、命令日志及输出 SHA。unsupported SVG 元素报告失败，不静默整图转位图。字体替换及公式降级保留在上游日志，交付时说明。

## 旧能力与回退

原两个 Skill 名称及旧 CLI 继续可用；直接调用 technical-diagram-options 也默认进入此流程。旧 draw.io / HTML / PDF / TikZ / selector / route_request 等实现、样例和偏好未删除，明确要求 legacy 时才使用。迁移前完整入口保存在 docs/legacy/figgenie-migration。未合并的 `feat/svg-first-workflow` / PR #1 不自动合入；该旧实验的 scene IR 不是本流程的几何源。
