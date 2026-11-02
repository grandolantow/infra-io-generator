# infra-io-generator

轻量封装 **FigGenie 原生绘图 + 个人偏好/精选样例 + 同源双目标输出**。

一张图只理解和设计一次：`brief.md → spec.json → plan.md → fig.svg`。
**fig.svg 是唯一几何与视觉源**；不新增 scene IR，不从 PNG/PDF/PPTX 反推另一终稿。

- `image`（默认）：SVG + 高分辨率 PNG。
- `pptx`：原生可编辑 shapes/text/connectors/groups，内部仍保留 canonical SVG。
- `both`：同一个 SVG SHA-256 分别导出，不再次调用绘图 Agent。

## 使用

安装本仓 `skills/` 两个同级目录；两个既有 Skill 名称均保留，新任务进入同一薄封装。
另行安装 [FigGenie](https://github.com/Sleepy-Avacado/FigGenie-paper-diagram-skill)，checkout 到
`c136a6aeefc6f6fe11fc615a5199cca57be3322a`，依其文档准备依赖。上游代码、图库与字体不复制进本仓。

> 使用 technical-architecture-diagrams 画 Ascend 算子工作流，huawei-plain，presentation，图片和可编辑 PPT 两种都要。

Agent 按 FigGenie 原生流程完成一次设计、绘制、检查与看图；然后运行：

```bash
python skills/technical-architecture-diagrams/scripts/figgenie_export.py fig.svg \
  --spec spec.json --upstream /path/to/FigGenie-paper-diagram-skill \
  --output-format both --display-intent presentation --out delivery-v1
```

参数也接受 `--output_format`；`png/svg/图片 → image`，`ppt/可编辑 PPT → pptx`，`两种都要 → both`。
paper/presentation 决定设计时的字号与观看尺寸，**不是在导出时独立重新排版**。封装是标准库 Python，不在 image 路径加载 PPTX 依赖，也不会自动安装软件。

详见 [迁移与兼容](docs/figgenie-migration.md)、[偏好配置](skills/technical-architecture-diagrams/config/figgenie.json)、[修复验收摘要](reports/figgenie-local-20261102/VALIDATION.md)（[迁移时历史记录](examples/figgenie/VALIDATION.md)）。

## 边界

manifest 记录源 SVG/spec 哈希、固定上游 revision、参数、命令与输出哈希。结构检查与视觉验收分开；字体替换、公式降级、失败、未运行如实记录。PPT 对象可编辑不承诺语义拖动重连，也不同步人工 PPT 修改回 SVG。

默认拒绝非空输出目录，防止覆盖人工改动。只有明确许可才用 `--overwrite`。修改先改 brief/spec/SVG，再一次性重导所需格式。

## Legacy 保留

旧实现、偏好、评价样例、快捷脚本均保留；完整旧入口文档见 [迁移前 README](docs/legacy/figgenie-migration/README.md)。PDF、HTML debug、draw.io、TikZ 仍可显式选择 legacy，不再作为默认交付或开发重点。

本分支基于 main `d195af9`，没有合入 `feat/svg-first-workflow` / PR #1 的独立 scene.json/布局引擎。旧 feature 分支与 PR 保持不变，便于回退比较。

## 测试

```bash
python -m unittest discover -s tests -v
python tools/check.py
```

无浏览器/TeX/绘图运行时的检查不能据此声明视觉通过；实际执行结果见验收记录。
