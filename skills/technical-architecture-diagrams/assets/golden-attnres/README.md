# Attention Residuals 原生draw.io样例

固定四子层、S=2的Standard/Full/Block对照。`build_golden.py` 是专用架构模板；事实JSON记录来源、候选核验和hash，换JSON不会自动改变结构。不是任意事实的绘图编译器。

从任务目录运行：

```bash
python /path/to/skill/assets/golden-attnres/drawio/build_golden.py \
  --output-dir ./attnres-output
python /path/to/skill/assets/golden-attnres/semantics/verify_drawio_contract.py \
  ./attnres-output/attention_residuals.drawio --out ./attnres-output/checks.json
```

实际导出与编辑证明：

```bash
CHROME_BINARY=/path/to/chrome PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs \
node /path/to/skill/scripts/drawio_runtime/export.mjs \
  --input ./attnres-output/attention_residuals.drawio \
  --out ./attnres-output/attention_residuals \
  --graph-js /project/.cache/drawio/app.min.js --move f_layer3
```

`--move` 保存独立编辑证明，不覆盖主稿。默认plain标签导出原生SVG文字。完整EditorUi/Desktop未测。

先学习语义、相对组坐标、公共锚点、端口和路线，再为新论文建立事实与模板。不要删掉难画的候选边去适配样例。来源见 `semantics/sources.md`；Skill不内置论文原图。
