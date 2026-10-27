# 用途与可调配色

本文件的 legacy auto 行为适用于 **model 分支**。v0.10.0 新 report 分支先经 `scripts/route_request.py` 选出显式 palette：PPT → huawei-plain，paper/未指定 → paper-vivid；模型默认不变。完整优先级为颜色覆盖 > 显式 palette > 分支/用途默认。下面 resolver 的 auto 命令不自动识别 report。

## 默认与覆盖

- 默认 `palette=auto` → `paper-clear`（清彩论文）：沿用用户认可的 M3.1-Flash 浅底彩色方案，论文与 PPT 均保持此默认。
- 可选 `blue-neutral`（素雅灰蓝）：低饱和蓝灰、浅灰分区，正文保持深色。
- `huawei-plain`（华为朴素）与 `paper-vivid`（旧明艳论文）仍可显式选择；指定模板的样式要求优先，不因 target=ppt 自动改色。
- 显式 `palette` 覆盖用途默认；`--custom` 的稀疏颜色覆盖优先级最高。`palette=custom` 必须提供覆盖文件，基础仍来自 target 默认。
- `blue-neutral` 是此前朴素蓝灰方向的可选变体，非 Huawei 仓库主配色。
- 配色与结构、事实、语言分别选择。功能框及术语英文，图中短注释和箭头说明用英文，可独立阅读的长段说明用中文。

配置文件是 `references/palettes.json`；可以改预设 token 或使用命令行覆盖，不需要改绘图布局代码。禁止把换色算成不同结构方案。

## 执行

```sh
python scripts/resolve_palette.py --target ppt --format json --output palette.json
python scripts/resolve_palette.py --target paper --format css --output palette.css
python scripts/resolve_palette.py --target ppt --palette paper-vivid --format drawio --output styles.json
python scripts/resolve_palette.py --target ppt --palette custom --custom custom.json --output palette.json
python scripts/test_palettes.py
```

`custom.json` 示例：`{"accent":{"primary":"#9A1F2F"},"compute":{"fill":"#E4F0F9"}}`。

JSON 输出是渲染无关 token；CSS 输出 `--diagram-*` 变量；drawio 输出可合并到 cell style 的样式片段。生成新图时应按语义对象读取相同 resolved token，并保留已有 shape、geometry、source、target 等属性。

已有图可用 `scripts/apply_palette.py input.svg --output recolored.svg --map mapping.json --target ppt`。SVG 映射为 `{"#OLDHEX":"compute.fill"}`，仅改六位 hex 的颜色属性或内联 style；不重写样式表、不解释任意 CSS。drawio 映射为 `{"cell-id":{"fillColor":"compute.fill","fontColor":"text.primary"}}`，只改已有颜色属性，不修改对象 ID/连接/坐标；仅支持未压缩原生 XML。不同角色共享同一源色时，不要用全局源色映射强行拆语义，回到原生对象逐 cell 配置。缺失映射、不支持格式和无效颜色会报错，不默默继续。

配色解析不是绘图引擎：仍按主规范在真实后端渲染验收。不得宣称此扩展已完成 huawei-html-ppt 仓库集成。

## 样式约束

明确选择 huawei-plain 时，文字、图例和注释保持黑／灰／红；红用于重点，不为所有模块加红边。类别可借助编号、线型和区域标记识别，不能只依赖颜色。灰色辅助文字不能无限缩小；保持主体字号与对比。论文用更鲜明填充与边线，但避免彩虹装饰及大面积重色。

矩阵密度按信息需要选择，已有用户偏好尽量4行以上；不要为配色造数据。空间不足拆图，不无限缩字号。换色不能改变实线/虚线代表的事实边界。

## 来源和边界

PPT 主色来自 `LookAround0301/huawei-html-ppt` commit `cb1a8d2de0490ab5c01cb4c5d1a46ee3fcfc3ecd`：
- [style-guide](https://github.com/LookAround0301/huawei-html-ppt/blob/cb1a8d2de0490ab5c01cb4c5d1a46ee3fcfc3ecd/skills/huawei-html-ppt/references/style-guide.md)
- [two-style/style.css](https://github.com/LookAround0301/huawei-html-ppt/blob/cb1a8d2de0490ab5c01cb4c5d1a46ee3fcfc3ecd/skills/huawei-html-ppt/assets/two-style/style.css)

精确主色：`#FFFFFF` 背景、`#1D1D1A` 正文、`#666666` 辅字、`#F2F4F6` 面板、`#AEB8C0` 边线、`#C00000` 强调。语义角色到主色的映射是本扩展选择，不冒充仓库已有统一适配 API。论文与蓝灰变体是本 Skill 的语义预设，不声称仓库原有主题。

保持已有 v0.9 的原生 draw.io 与 TikZ 后端、事实契约、用户评价和失败回归。此次只增加配色路由与颜色适配，不改架构生成逻辑，也不重新声称历史评估全通过。

## 已验证样例

M3.1-Flash 680×1660 主图及独立 MSA 展开使用同一原生结构切换「清彩论文／素雅灰蓝」。换色必须保持节点 ID、标签、端点、坐标、线型与画布不变；通过精确源色映射或对象角色实施，不按色相猜测。低饱和方案仍用标签、分区、实虚线区分机制，不能靠颜色单独承载事实。

语言规范以共享 `text-language.md` / `language-profile.json` 为准；图题、分区标题、图例、箭头叙述和来源限制均属于绘图 QA，不移交给 PPT 才处理。
