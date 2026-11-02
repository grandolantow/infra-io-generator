# SVG-first 改造记录

基线：`grandolantow/infra-io-generator@d195af99001bde5ef7e7a723890918839fe6df01`。

本次只改绘图工作流；没有修改 `operator-shape-derivation` 的算子开发流程。

## 已实现

1. 统一 Skill 的新图默认链路切为 Semantic IR → Agent 布局设计＋确定性编译 → SVG → HTML。既有 model/report/mixed 分工、模型竖向主干、selector、配色与语言规范保留。
2. 路由新增 `rendering` 策略，默认 `svg-first`；`drawio-legacy` 可显式选择。旧 `parts[].runtime` 字段不移除，兼容旧调用方。
3. 新增 `svg_pipeline.py`：旧报告 IR 分层迁移、row/column 约束、命名端口、共享主题、SVG 主输出和同源 draw.io 导出。
4. 新增自包含 HTML 查看器：切换视图、缩放、点击/键盘选择、关系高亮、事实来源和保存 SVG。无 CDN/外部字体依赖。
5. 增加语义指纹、渲染 ID 命名空间、输出修改检测。手工修改后的 SVG/draw.io 不会被静默覆盖；不宣称无损双向同步。

执行说明见 [SVG-first 工作流](../skills/technical-architecture-diagrams/references/svg-first-workflow.md)。

## 实际验证

- `python -m unittest discover -s tests -p test_svg_first.py -v`：**40 项通过**。覆盖生成、分层迁移、语义不变、布局与端口、样式映射、语言检查、碰撞/越界、输入转义、原生编辑对象、确定性重建和人工修改保护。
- 复用此前 Ascend 工作流的三个视图，迁移前后语义 SHA-256 一致：`3de2cdde9e24ca8e3a67f89c2f4756502840bb9dec0b42bf88459d817b2f4076`。这是迁移回归，不是重新设计三版图。
- Chromium/Playwright 实测三个回归视图和一个新编译器接线样例：视图切换、鼠标选择、键盘选择、缩放、复位、SVG 保存可执行；没有重复 DOM ID、画布外文字、页面脚本错误或外部资源请求。
- 390px 视口检查没有文档级横向溢出；技术图的细节阅读仍可放大，不宣称手机缩小状态可读性等同桌面。
- 实际查看了回归图的桌面截图。原布局的文字/连接总体可见；没有把格式迁移解释为美观提升，也没有进行新的用户偏好验收。

浏览器使用生成 HTML 的原始字节调用 `set_content`；该环境的 `file://` 导航受策略限制，因此未把原生文件导航记为通过。没有运行 draw.io EditorUi/GUI 拖动、PDF/PPT 导出或全仓测试套件。此次使用固定提交的相关文件做定向验证，不将局部测试推广为全仓或全部模型兼容性结论。

## 依赖完整性

以下实际参与定向验证的旧文件与基线 Git blob SHA 一致，未改写：

| 文件 | Git blob SHA |
|---|---|
| `technical-diagram-options/scripts/diagram_tool.py` | `6eabad38743c5dce74503e97d91d71c8ec5dc759` |
| `technical-architecture-diagrams/scripts/check_language.py` | `a41ecc073ad1058fb32920970b69399b153f434f` |
| `technical-architecture-diagrams/references/language-profile.json` | `638c3606f8ca985ea385bc01ab828857b0df2844` |
| `technical-architecture-diagrams/scripts/resolve_palette.py` | `d2f0b380c59f866ca16652df5b9121bc8c3b9dce` |
| `technical-architecture-diagrams/references/palettes.json` | `bb115da68bf8cf0c7dc3a469c3129c5f4594ea6d` |

## 仍需区分的范围

当前布局编译器不是自动美学设计器或全局避障器；复杂组件、原生 PPT、任意 SVG/draw.io 回读、Canvas 后端未在此次实现。独立绘图 Agent、参考对照、默认 3–4 个实质不同方案和编号 PDF 归档仍由高层工作流负责。更换展示链路不证明画质提高；后续质量对照应固定事实、主题、设计预算与修改任务。
