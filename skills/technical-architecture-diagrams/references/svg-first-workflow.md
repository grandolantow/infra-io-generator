# SVG-first 绘图工作流（v0.11.0 初版）

## 1. 改什么，不改什么

新图默认：**技术取证 → Semantic IR → Agent 视觉设计 → 确定性布局编译 → SVG → HTML 预览与修订**。从同一份已解析场景另导出 draw.io，供人工编辑。不再要求所有新图先生成 draw.io 再由其导出 SVG。

这不是“SVG 必然更美观”的结论。现有报告后端本来就能直接输出 SVG；本次改变的是默认制作顺序、设计/事实边界、互动预览和安全修改流程。旧模型母版、draw.io runtime、Inkscape/TikZ、历史示例与语义检查器保留。旧文件不自动迁移，不删除 golden 或已有反馈。

语义路由不变：模型主干/模块组成走 model，机制/通信/内存/调度走 report，mixed 拆分并共享事实。model 继续优先竖向主干＋有解释价值的侧边展开；report 根据实际关系选择结构，不机械竖化。报告仍先运行 selector，再由 Agent 设计，不将脚本输出视为独立生成。

语言和配色继续服从共享规范：图内英文短标签、独立中文解释；显式配色优先，model 默认 paper-clear，report/PPT 默认 huawei-plain。不能在换后端时偷偷换主题、技术事实或对象 ID。

## 2. 三层源数据

| 层 | 内容 | 修改责任 |
|---|---|---|
| `scene.semantic` | facts/provenance、nodes、typed edges、稳定语义 ID | 技术理解与事实核查；是技术事实的唯一维护源 |
| `scene.layout.views` | 图元、组合、坐标、尺寸、端口、连线路径、短标签与分区 | 绘图 Agent；多个方案可共享同一语义 |
| `scene.theme` | 显式 palette、custom_tokens、base/roles/edge 的样式覆盖 | 视觉主题；不改变语义或布局 |

输入的 `scene.json` 是需要维护的编辑源；输出目录内的 `scene.source.json` 是交付副本，`semantic.json`、`layout.resolved.json`、`diagram.source.json` 是构建快照，不建立第二套手工维护状态。全语义哈希写入 manifest，用于检查风格/布局修改没有意外改写事实；哈希相同不证明原事实正确。

兼容格式 `schema_version=1.0` 仍有效。新场景使用 `schema_version=svg-first/1`，保留原语义节点、边、事实和语言 profile，把原 `views` 移入 `layout.views`。迁移不重新设计旧图，不把导出格式变化计作新方案。

## 3. 设计 Agent 与 Layout Engine 的边界

Agent 负责图解释什么、怎么分区、哪些机制展开、用什么组件和信息密度。布局编译器只落实已经选择的规则，并产出可检查几何。不能先套一个通用 DAG 模板，再通过改标签假装完成设计。

当前实现支持：

- 原 report IR 的 rect、rounded_rect、ellipse、diamond、text 和显式折线路径；这些基础图元可以组合成张量片、区域、泳道和状态组件。
- 可选 `arrangements`：显式指定 row/column、成员、起点与间距；未列出的对象保持原位。锁定对象拒绝参与重排。
- 可选命名端口 top/right/bottom/left 与 `via` 折点。图元移动后重新计算两端；中间折点仍由设计者负责。也可保留既有完整 `points`；不得同时使用两种表示。
- 主题显式 `palette` 复用共享解析器；`auto` 必须先由语义路由解析，旧导入图不自动换色。按共享 token → base/role → 局部 style 覆盖；font_weight 映射到 SVG 和 draw.io。带短标签的图元必须保留 text_role。

**当前不是通用避障器、自动文本排版器或美学评分器。** 不自动发明布局、不做浏览器字体测量，也未增加任意曲线/复杂公式组件。超出基础图元时可采用自定义原生 SVG、Inkscape 或 TikZ，继续保留语义映射、来源和视觉检查；不能为了匹配基础导出器而简化错误。自定义组件的 draw.io 可编辑覆盖与损失必须单列，不能包装成整图图片冒充原生对象。

## 4. 可执行入口

安装时仍保留两个同级 Skill。新编译器复用 `technical-diagram-options/scripts/diagram_tool.py` 与共享语言检查器，不复制或修改旧后端。生成与单测仅使用 Python 标准库，不自动安装浏览器、字体或第三方绘图库。

在仓库根目录运行：

```bash
# 路由：默认返回 rendering.primary=svg-first；旧 runtime 字段保留兼容。
python skills/technical-architecture-diagrams/scripts/route_request.py \
  --request 'workflow dataflow' --intent report --target ppt

# 原 report IR 无语义改写迁移；拒绝覆盖已有场景源。
python skills/technical-architecture-diagrams/scripts/svg_pipeline.py \
  split old.diagram.json --out scene.json

# 验证和构建同源 SVG / HTML / draw.io。
python skills/technical-architecture-diagrams/scripts/svg_pipeline.py check scene.json
python skills/technical-architecture-diagrams/scripts/svg_pipeline.py \
  build scene.json --out-dir build/my-diagram

# 仓库内的小型编译器接线样例，不是质量评测样例。
python skills/technical-architecture-diagrams/scripts/svg_pipeline.py \
  build examples/svg-first/workflow.scene.json --out-dir build/svg-first-smoke

python -m unittest discover -s tests -p test_svg_first.py -v
```

`--no-drawio` 明确关闭该次编辑导出。`--renderer drawio-legacy` 选择历史路由；旧模型原生格式不由 `split` 猜测转换。Canvas 尚未实现，路由不会返回一个虚假的 Canvas 可用后端；有大量实时对象需求时单独建立场景、成本和验证方案。

## 5. HTML 展示与编辑输出

默认展示端是单文件 HTML，内嵌 SVG/CSS/JavaScript，不依赖 CDN、服务器或外部字体。支持视图切换、缩放、模块点击/键盘选择、直接相邻关系高亮、事实/来源查看，以及保存当前 SVG。没有自动播放执行时序；图中相邻关系不能证明执行并发、时间长度或性能。

各 SVG 使用 view ID 命名空间，避免同页的 marker/节点 ID 相互污染；`data-semantic-ref` 保持稳定。文字保留 `<text>`，不会自动转成路径或位图。HTML 是查看器，不是拖拽编辑器。

draw.io 由同一份解析后场景导出原生 cell、文字与连接器，而不是从 SVG 像素重新识别。节点 ID/边端点/语义关系必须对应；字体度量、文本偏移和精修效果不承诺像素一致。结构检查、实际 EditorUi 渲染和 GUI 拖动是三项不同验证。

**不承诺无损双向同步。** 用户直接改 SVG/draw.io 后，先比对改动并回写场景，或明确将该文件作为新的编辑分支。构建器根据上一版 manifest 检测已修改/未跟踪的输出文件，默认拒绝覆盖；只在完成核对并明确要丢弃这些改动时使用 `--overwrite-edits`。

## 6. QA 与交付

技术事实 → 几何/端点 → 实际浏览器渲染 → 参考对照和审美修订 → 多格式验证，保持这个顺序。程序检查成功不能升级成视觉通过，也不能证明独立绘图 agent 确实执行。

程序会检查已有语义/语言契约、有限坐标、边端点归属、画布越界和 ID 冲突。已有近似线段穿越/文字溢出告警保留，须实际查看；不会假称所有几何问题自动修复。HTML 以真实渲染测字体和可点击性，至少检查最终展示尺度、长标签、密集节点与反馈边。

新增构建产物：`scene.source.json`、`semantic.json`、`layout.resolved.json`、`diagram.source.json`、每视图 SVG、`preview.html`、可选 `diagram.drawio`、`structural-qa.json`、`build-manifest.json`。manifest 的未运行层级保持 `not_run`，外部视觉/浏览器验证另存报告，不回填虚构通过。

高层任务继续使用既有 brief/delivery 协议，默认 3–4 个**实质不同**方案、编号 PDF 归档与明确主版选择。该脚本不生成 PDF/PNG/PPT，也不替代独立设计委托；需要这些交付时调用真实导出流程并实检。没有相应工具时记录 blocked/not_run。示例和已有图的编译回归不是一次新的多方案设计，也不宣称独立 Agent 或优质样例验收。

## 7. 与旧路径比较的方法

固定同一技术事实、用途、主题与修改任务，分别比较语义正确性、可读性、信息组织、人工修改成本和实际迭代次数。不要只比较改造前后的文件后缀。只改变编译/预览链路的回归实验只能说明兼容性；要证明画质提高，必须增加独立设计、同预算生成和用户评价。
