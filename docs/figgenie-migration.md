# FigGenie 收缩迁移

## 基线与回退

2026-11-02 核查 main 为 `d195af99001bde5ef7e7a723890918839fe6df01`；
`feat/svg-first-workflow` 为 `ca4ab107d46b4b089b83472ce348f1fffe94c286`，领先 3 提交，PR #1 未合并。
本分支从 main 新建，不将 PR #1 的 scene.json / 独立布局引擎带入。旧工作区含 staged 文件，未改动；使用独立 clone。

旧两 Skill 入口文档快照在 `docs/legacy/figgenie-migration/`，脚本、资产、偏好原路径保留。
`route_request.py`、`prepare_diagram_brief.py`、selector、diagram_tool 等旧低级 API 签名不变；
它们属于 legacy，不作为新 FigGenie 流程的隐藏阶段。旧 target=ppt 仍表示 legacy 用途；
新 `display_intent=presentation` 表示单图观看尺寸，`output_format=pptx` 才表示文件格式。

## 唯一来源和权限

Agent 使用上游 brief/spec/plan 设计一次 canonical fig.svg。导出器没有模型调用、设计或排版代码。
image/pptx/both 对同一 SVG 只做原生工具编译。manifest 绑定每个输出的 source_svg_sha256，
并在每个工具前后检查源 SVG/spec 未变化。文件 SHA 只证明字节关联，不证明技术事实或审美正确。

输出目录必须与源目录分开；默认非空拒绝。`--overwrite` 表示调用者已经取得覆盖许可，
不会自动清空目录，也不修改输入文件。人工改过 PPT 或 SVG 后先另存版本，禁止反推另一终稿。

## 上游与依赖

锁定 revision 在 config/figgenie.json，需干净 checkout。依次调用原生 spec_validate.py、check.py、embed_fonts.py、
svg2pptx.py 和 pptx_check.py；check 的 PNG 作为高分辨率 PNG，SVG 字体嵌入版为 fig.final.svg。
上游字体资产只从已安装 checkout 读取，不复制入仓库。

image 不导入 python-pptx，也不运行 PPT exporter；pptx/both 才运行该脚本。
封装不安装任何依赖。公式须先在上游 tex_fill 完成指标与路径；没有 MathJax 时显式文本降级，
不触发上游的自动 npm 安装。没有 Office XSL 则按上游降级为可读文本，并保留 warning。
警告、字体映射、公式是否原生须在最终交付中说明，不能因为进程返回 0 就宣称保真。

## 格式约束

保留稳定 ID、viewBox、DOM 顺序；要求 viewBox 从 0 0 开始。
直接拒绝上游不支持的 use、foreignObject、switch、gradient、filter、clipPath、mask、隐藏/裁剪属性和 CSS stylesheet；
用 presentation attributes/inline style。当前封装也保守拒绝 tspan（包括带样式/定位的多行）：上游 PPT exporter 可能合并文字而丢失行布局，须在 canonical SVG 中使用同一组内的独立 text 元素表达各行；不要仅凭 pptx_check 通过宣称文字保真。原生 lint 负责其余检查。无整图位图 fallback。
稳定语义 ID 放在顶层 g 上，PPT 对象名称保留它们；primitive XML ID 由原生 exporter 重新分配，不承诺逐个 XML ID 相同。嵌套 g 在上游会被扁平化，本封装保守拒绝，采用顶层语义组和视觉容器表达层次。PPTX 原生 objects 可编辑，但不保证语义重新路由，组内对象与图像可能各有不同编辑边界。

## 验收

两个原生例子及三模式、修改重导记录见 examples/figgenie。单元测试使用假的上游脚本仅验证
调度与拒绝覆盖，不冒充真实视觉验收。实际输出需要看浏览器 PNG 与 PPT 渲染图，核对长标签、
箭头、字号与层次；结构测试和视觉通过分开，not_run 明确标记。


## 新导出 PPTX 的主题阴影兼容处理

本仓只对本次 `svg2pptx.py` 写入临时目录的全新文件执行兼容处理，不读取/修复已有最终 PPTX。
根据 slide → layout → master → theme 的真实关系，找到对象 `p:style/a:effectRef` 引用的样式。
只有该样式的 `effectLst` 仅包含阴影，且对象没有明确的非空 `effectLst/effectDag` 时，才将引用索引置为 0。
无阴影引用、idx=0、对象显式效果均保持。混合效果、歧义关系或 themeOverride 拒绝处理；不改主题文件。
源 SVG 的 filter、CSS stylesheet、text-shadow/box-shadow 等不支持特性会明确拒绝，不会删掉设计者要求的效果。

只替换目标索引的原始 XML 字节，并验证其余 XML 完全不变；其他 ZIP part 保留原始字节。
manifest 的 `pptx_compatibility` 记录修改对象、主题、前后文件 SHA-256 与不变量。
完成兼容处理、`pptx_check.py` 和源哈希复核后才发布最终 PPTX。即使显式 `--overwrite`，
上述步骤失败也不替换已有 PPTX；无覆盖授权时仍拒绝非空输出目录。

FontTools 的嵌入子集默认含当前时间。封装为原生工具设置上游固定提交时间对应的 `SOURCE_DATE_EPOCH`，
记录于 manifest，使同源 image/both 字体嵌入 SVG 可重复；不改源 SVG、不重画、不引入第二套坐标。
PPTX ZIP 时间戳可能导致两次文件 SHA 不同；验收另外比较解包后的幻灯片 XML，不声称 ZIP 字节可重现。

本地六组验收、浏览器/Office 视觉检查、完整哈希与剩余警告见
[2026-11-02 本地验收记录](../reports/figgenie-local-20261102/VALIDATION.md)。
