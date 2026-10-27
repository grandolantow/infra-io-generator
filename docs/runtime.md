# 运行与依赖

## 原生导出

```sh
node skills/technical-architecture-diagrams/scripts/drawio_runtime/export.mjs \
  --input examples/minimax-m31/paper-clear/portrait.drawio \
  --out build/portrait \
  --graph-js third_party/drawio/app.min.js \
  --chrome /path/to/chrome \
  --move msa
```

`--input` 必填；源文件为未压缩原生 mxGraphModel。`--page` 从 0 开始，尺寸读取所选页面的 `pageWidth/pageHeight`；未声明有效尺寸时报错。`--move` 仅生成独立编辑探针，不覆盖母版。普通样例入口自动定位 Playwright 自带浏览器。

输出包括 SVG、内部截图、渲染状态和运行检查 JSON。内部截图只作 QA，展示 PNG 由 Inkscape 从最终 SVG 导出。该链路测试官方 Graph 类，不测试完整 Desktop/EditorUi。

官方 JS 保留在 `third_party/drawio/`，加载前必须核对 SHA256。版本和来源见同目录 pin；滚动 upstream 更新后不能跳过校验。仓库不包含 Chromium 二进制、node_modules 或 Python 虚拟环境。

## 精修

`tools/render_example.py` 会去除浏览器专用 `light-dark()` 回退样式，为路径设置圆角连接，在 Inkscape 导出保留文字的 SVG 与展示 PNG。该处理只覆盖本仓库样例的已知后处理，不代替逐图视觉设计；改动技术结构时先改 draw.io。

原始 draw.io 和 Inkscape SVG 不自动双向同步。渲染脚本保留母版 SHA256；母版变化后需重新精修与复核。

## 三种事实记录

- `references/example-attention.json`：旧拓扑草稿 schema，含 baseline/proposed，供 `validate_spec.py` 使用。
- `assets/golden-refined/facts.json`：四子层、S=2 专用语义检查。
- `examples/minimax-m31/facts.json`：固定模型版本及可见事实记录；不应传入旧 baseline/proposed 校验器。

这些格式并未统一为通用论文到图形编译接口。

旧 `render.py` 与 `check_editability.py` 仅用于历史拓扑草稿；其固定画布和 SVG 布局移动测试不代表生产图使用它，也不代表原生 GUI 编辑。

## TikZ 模型静态后端

已审阅的自包含 TeX 可通过 `python tools/render_model_tikz.py --input authored-model.tex --out-dir build/model --engine xelatex --trusted-source` 编译和导出。需要完整可用的 TeX formats/classes/TikZ 与 Poppler，不仅是编译器二进制；缺依赖明确失败。详细安全与语义边界见 [TikZ runtime](../skills/technical-architecture-diagrams/references/tikz-runtime.md)。不涉及浏览器，不自动安装依赖，也不把 TeX→图形检查说成科学或语言验证。

高层独立绘图交付校验需要 `requirements.txt` 中的 jsonschema，以及 Poppler 的 `pdfinfo`/`pdftotext`，用于实际打开编号方案归档 PDF 并检查页数/编号映射。工具缺失时报阻塞，不以文件扩展名代替 PDF 解析；编号可提取不等于页面视觉质量通过。
