# Golden 后端与职责

这是同一道题的实际工具对照，不是通用架构绘图排名。

## 默认生产分工

用户确认：draw.io 保留结构母版，Inkscape 做视觉精修；复杂公式或论文 LaTeX 集成时使用 TikZ。以下历史试验表仅记录校准证据，不要求每次生成全部后端。

1. 先维护事实记录和原生 `.drawio`，核验源与目标、运算符、候选集合和区域层级。
2. 经实际 draw.io 引擎导出 SVG，再用 Inkscape 精修；记录导出母版版本与精修文件版本，保留可编辑文字与对象，检查字体替换。
3. 精修允许改变路径几何，不允许改变边的逻辑端点、汇合含义和技术标签。若需要结构变化，先回写 draw.io 和事实记录再导出。
4. 母版更新后，识别受影响的精修并重新应用；没有稳定 ID 映射时逐项人工复核，不承诺自动回合或无损同步。
5. 使用 TikZ 时以同一事实和已批准布局为依据，保留 `.tex`；导出 SVG 中的字形轮廓不算可编辑文字。同步检查节点、端点、公式与版本。
6. 最终以精修 SVG 作为默认展示图，以 `.drawio` 作为结构编辑入口；适用时附 `.tex`。重新检查实际导出和图自身比例；需要嵌入PPT时再检查页面适配，分别注明未测试项目。


|后端|实际执行|本题定位|边界|
|---|---|---|---|
|draw.io Graph 32.6.1|原生XML导入、渲染、SVG/PNG导出、鼠标拖拽及序列化|编辑工作流主交付|完整EditorUi/Desktop未测，主版式来自模板|
|TikZ / pdfTeX|TeX编译PDF、导出SVG/PNG、修订入射端口|精密静态候选|可靠SVG把字转成路径，编辑依靠TeX|
|elkjs 0.12.0|实际layered节点/端口/edge sections，自动与模板两输出|拓扑草稿、局部布局|模板版只让局部算子自动排布|
|Penrose 3.3.1|Domain/Substance/Style编译、优化、SVG，两种子|约束研究|大多数坐标和走线被固定，不能称自动多布局|

draw.io主稿的100个vertex包含文字、区域和张量片，不是100层模型；80条edge包含query和算子边。主版式来自4个panel、5个聚合行、4个子层行和历史通道。引擎负责对象、边界连接、渲染、编辑与序列化。

TikZ使用84个显式坐标对及相对锚点。ELK模板版显式安排32个主节点、10个query和64条架构折线；ELK只排布局部算子。Penrose固定65/66个对象中心与70条走线，两种子仅改变一处注释约2.2px。质量不能归因于自动引擎。

## 原生对象与路由

- 保留未压缩mxGraphModel、语义角色与稳定ID；组内几何使用相对坐标。
- 底层Graph中明确写 `shape=ellipse;perimeter=ellipsePerimeter`；不要假设EditorUi的命名样式已加载。
- 边连接source/target，明确exitX/Y、entryX/Y和必要waypoint。主干向上、算子向下时分别指定端口。
- 只在真实汇合处加点；历史项分配不同通道与入射位置。共享线段不能替代候选来源说明。
- plain text导出用于保留SVG text；HTML标签的foreignObject兼容性另测。导出时隐藏折叠控件。
- K由候选归一化，V保留原候选；张量片的堆叠表示集合，不是串行计算。

## 运行依赖

`scripts/drawio_runtime/export.mjs` 需要Node、Playwright、Chromium与官方bundle。用 `PLAYWRIGHT_MODULE`、`CHROME_BINARY`、`--graph-js` 明确路径，输出到任务目录。

`fetch_runtime.py --out /project/.cache/drawio/app.min.js` 只接受pin中的SHA。默认通过固定 Git blob URL 获取字节；原 dev URL 只保留为来源记录。下载仍核对SHA，不绕过hash检查。本次完整源码交付保留了实际bundle和上游LICENSE；Skill不携带浏览器或依赖树。

## 通用作者 TeX 执行入口

仓库提供 `tools/render_model_tikz.py`，用于已核验、自包含的模型 TeX 画稿，实际编译 PDF 并导出 SVG/PNG。读取 `references/tikz-runtime.md` 了解依赖、显式可信源门槛、受限执行和 QA 边界。它不理解任意模型、不替代结构母版或语言角色审核。
