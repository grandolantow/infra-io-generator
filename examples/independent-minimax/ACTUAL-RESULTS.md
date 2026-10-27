# 实际执行结果

完成一张竖向模型主干和两张独立机制页，分别提供清彩论文、素雅灰蓝两套配色。母版是6份未压缩原生 `.drawio`，当前展示为6份 Inkscape SVG、6份 PNG，以及内嵌六份矢量图的自包含 HTML。

## 已执行

1. 从允许的本地材料冻结来源版本与 SHA256，建立语义节点、实际边、端口与14项必须可见的事实。配置/本地源码核对18项通过；完整论文和被委托到外部模块的 kernel / TopK 内部实现没有独立核验。
2. 用提供的官方 `app.min.js` 运行 draw.io Graph32.6.1，经 `mxCodec` 导入原生 XML，实际渲染、导出 SVG/PNG，并记录引擎状态。正式六份图均已运行，JavaScript 错误为0。布局由本次专用模板编写，引擎不承担自动论文布局。
3. 清彩版每页实际用鼠标拖动一个模块。附着边跟随；无关节点位置未变；重新序列化后，稳定 ID 与 source/target 保留。证据是独立 `.edited.drawio` / PNG，未覆盖正式母版。
4. 单独修改一份原生副本中的标签，再经官方 Graph 导出。新文字在 SVG 中可见，所有 ID、端点和节点几何保持不变。见 `evidence/label-probe.json`。
5. 六份 Graph SVG 均经 Inkscape1.2.2 实际导出为 plain SVG，再导出 PNG，并逐份运行 `--query-all`。六份各有42 /42 /36个 `text`；`foreignObject=0`，`image=0`。未把字转成路径。字体声明为 Arial，本机 Fontconfig 将 Arial 解析为 Nimbus Sans；最终 Inkscape PNG 已抽查，无缺字或溢出。Inkscape 处理是导入、原生对象保存与再导出，未声称进行了 GUI 手工精修。
6. 用实际 Graph 标签边界、模块边界与引擎折点检查，正式六份图未检出文字出框、越界、非正交直线段、非端点模块穿越、线条遮挡标签或分区边界遮字。圆角由 Graph 的 `rounded=1;arcSize=12` 导出为曲线路径。Inkscape 实测文字边界也均落在分配的对象范围内。零几何告警不代表总体审美已获认可。
7. 两套配色逐 cell 比较：ID、文字、source/target、几何、端口与非颜色样式相同。
8. Chromium1280×900、文档 JavaScript 禁用时，实际点击 HTML 配色标签，两套配色均可见三张完整图，页面无横向溢出、网络请求为0、脚本数为0。另测390×844页面容纳情况；手机全图缩放后的文字可读性没有宣称通过。
9. 用此前不存在的 `evidence/portable-reproduction/` 作为 `--out`，完整执行 `source/reproduce.py`，退出码0。新目录实际生成六份原生 XML、六份 Graph SVG/PNG、六份 Inkscape SVG/PNG 和自包含 HTML，并再次通过18项配置/源码核对、14项可见对象存在检查、正式路径/文字几何检查和无 JS 配色检查。生成器显式把原始事实及 `sources/` 复制进新目录的 `source-input/`；六份新母版与正式母版逐字节相同。

## 失败与修订

首版已保存后才修改。首版的 plain 标签长行超框、注释/分区标题碰线、末端加法圆越过区域边界，以及 MoE token→routed 专家线穿过 correction-bias 框，均记在 `evidence/first-generation/qa.json`。最后一项可能暗示错误依赖，首版明确标为技术错误。修订时保留 source/target，只调整标签换行、通道和区域留白。

首版生成后收到父 agent 的两项图面反馈：MSA 说明行超框、残差折角过尖。随后显式换行并启用真实圆角。父 agent 后来将观察沉淀为 Skill 规则；本例没有回写为首版已使用该新规则。

第一次修订后发现一处 MoE 行外文字仍压在 bias 虚线上；该版本保留在 `evidence/revision-1/`，最后仅将该注释向上移到留白。后续父 agent 复核 MSA / MoE，未提出新的关键机制错误；该复核不等于用户认可。

运行中一次执行服务出现 transport disconnected，在进程创建前失败，随后重试成功；正式引擎或 Inkscape 命令没有未解决的执行失败。

## 限制与未测

- 任意拖动后固定 waypoints 不会自动重排，独立 edit proof 中可出现斜线；本次证明的是端点附着、对象编辑与序列化，没有证明自动保持布局。
- 完整 draw.io EditorUi / Desktop、Inkscape GUI 拖动未测。
- PDF 页面导出/检查、PPT/PPTX 插入与编辑未测，本题未要求这些交付。
- 未加载权重、未运行模型推理、未验证训练损失或 vision / DSpark 内部。
- 完整 MSA 论文不在提供材料中。因果索引、local占用Top16预算、精确内容注意力和 unbiased 路由权重按提供的事实绘制；本地配置/模型代码只能对其中部分设置与调用关系提供交叉核对。
- 这轮仍偏模块流程图式表达，不声称达到已有 golden、用户认可、全自动布局或独立留出泛化。

检查报告为 `evidence/final-qa.json`、`evidence/browser-qa.json`、`evidence/inkscape-commands.json`；首版和修订证据独立保留。生成源码、原始输入副本、固定 runtime 与许可证均已附带。
