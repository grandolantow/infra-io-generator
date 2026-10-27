# MiniMax M3.1-Flash 独立架构图

本例仅从提供的 `technical-facts.json`、原始 config / README / 模型代码建立语义与布局。没有读取此前生成的 MiniMax 图、布局或生成器。

- [可切换配色的离线 HTML](minimax-m31-flash.html)：默认「清彩论文」，可切换「素雅灰蓝」，无 JavaScript 也可使用。
- [模型主干 draw.io](native/model-paper-clear.drawio) · [SVG](figures/model-paper-clear.svg) · [PNG](figures/model-paper-clear.png)
- [MSA 机制 draw.io](native/msa-paper-clear.drawio) · [SVG](figures/msa-paper-clear.svg) · [PNG](figures/msa-paper-clear.png)
- [MoE 机制 draw.io](native/moe-paper-clear.drawio) · [SVG](figures/moe-paper-clear.svg) · [PNG](figures/moe-paper-clear.png)
- 灰蓝版采用相同文件名，将 `paper-clear` 替换为 `blue-neutral`。
- [事实与可见事实清单](technical-facts.json) · [实际检查与未测项](ACTUAL-RESULTS.md) · [结构化 QA](evidence/final-qa.json)

`native/` 是结构母版；`graph/` 是实际官方 Graph 导出；`figures/` 是经 Inkscape 再导出的当前展示图。SVG 保留原生文字和矢量对象，未将整图嵌入为单个图片。主干画布为1000×2200；MSA为1360×1880；MoE为1420×1780。

## 复现

要求 Python、Node、Inkscape、Playwright 与 Chromium。依赖不在此脚本中安装。固定的官方 Graph 字节集中在仓库 `third_party/drawio/`；本目录保留 runtime 脚本、SHA pin 与许可，避免重复分发。命令中显式传入 `--graph-js`。

```bash
python source/reproduce.py \
  --graph-js ../../third_party/drawio/app.min.js \
  --chrome /path/to/chrome-headless-shell \
  --playwright /path/to/playwright/index.mjs
```

可用 `--input` 指定另一份同结构原始输入，用 `--out` 指定输出目录；也可使用 `CHROME_BINARY`、`PLAYWRIGHT_MODULE`、`NODE_BINARY`。默认输入为本包的 `source-input/`。换色不修改事实、稳定 ID、节点坐标、端口或连线种类。

此入口已用全新的 `evidence/portable-reproduction/` 输出目录完整执行，退出码0，重新生成六份母版、Graph 导出、Inkscape 图与离线 HTML，并通过事实/几何/无 JS 配色检查。新输出目录也保留 `source-input/`，不依赖旧输出目录中的输入回退。见 [新目录复现记录](evidence/portable-reproduction-result.json)。布局生成器是本模型的专用模板，不是把任意模型 JSON 自动编译为论文图的通用工具。

## 证据边界

首版错误和修订没有覆盖删除：见 `evidence/first-generation/`、`evidence/revision-1/`。本例目前为 agent 自检通过，仍是模块与数据流式抽象；没有用户审美验收，也不声称达到既有 golden。完整 MSA 论文未包含在允许读取的原始材料里，算法限定依照提供的事实绘制，并与本地配置/代码中可核对的部分分别记录。

仓库整理时未包含内部浏览器截图或完整的新目录复现副本；保留原生/SVG/QA 和新目录结果摘要。若需独立提取本示例，先运行 `python runtime/fetch_runtime.py --out runtime/app.min.js` 获取校验过的 bundle，再使用默认 --graph-js。原始输入许可证随 sources 一并保留。
