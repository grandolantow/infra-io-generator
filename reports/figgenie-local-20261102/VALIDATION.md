# FigGenie 导出修复验收摘要（2026-11-02）

基线 main：`cfa7b5db017b4e1d89546b79f7f886714dc42997`。FigGenie 固定 revision：`c136a6aeefc6f6fe11fc615a5199cca57be3322a`（干净 checkout，未修改上游）。完整输出、manifest、日志、失败尝试和视觉对照保留在本地归档，不随修复 PR 提交。

## 结果与边界

| 项目 | 结果 |
|---|---|
| Ascend、KV Offload × image/pptx/both | 6/6 passed；同案例三次源 SVG SHA 相同，design_invocations=0 |
| 原生链路 | spec_validate、check/lint/Chromium；image/both 的 embed_fonts；pptx/both 的 svg2pptx、兼容处理、pptx_check 均通过 |
| 同源比较 | image/both 的嵌入字体 SVG、1800×990 PNG 哈希相同；pptx/both 幻灯片 XML 与对象清单相同 |
| 浏览器视觉检查 | 两案例与长标签版实际看图通过，标签、箭头、主要布局正常 |
| LibreOffice 视觉检查 | 四份模式 PPTX 与长标签版实际渲染/看图通过；Ascend 13 处、KV Offload 19 处额外主题阴影消失 |
| 可编辑性 | Ascend：13 文本框、6 基本形状、2 connector、5 freeform、10 组；KV：17、10、7、2、15；两者 picture=0 |
| 长标签重导 | 源 SVG 的 Vector 标签改为两行；SVG ID、边、无关模块不变；PPT 语义名称保留，primitive 数字 ID 由上游重新分配 |
| image 无 PPT 依赖 | 在未安装 python-pptx/lxml 的独立环境实际导出通过 |
| 覆盖与错误处理 | 默认拒绝人工输出；显式覆盖时生成/修正/检查/源变更失败保留旧 PPTX；禁止 SVG 效果、非法 spec 报错验证通过 |
| 自动化回归 | 104 passed（含 22 项导出测试和 3 项 draw.io runtime），另配色 13、报告契约 24 passed；当前范围 0 failed |
| not_run | PowerPoint UI 连接延迟、目标打开未完成并返回 noWindowsAvailable；Inkscape 未安装；1 项 TikZ runtime 缺依赖 |
| excluded | 旧 PDF 交付检查按用户要求排除；未继续安装或修复其依赖 |

原生对象可编辑不代表移动后自动保持语义连接；本次 connection_binding_count=0，没有验证语义重连或 OMML。PowerPoint 已安装不等于视觉通过。

## 源与输出 SHA-256

每个案例的 image/both 共用下表 SVG、PNG 哈希。PPTX ZIP 时间戳可能不同，分别记录两个文件哈希；不声称 ZIP 整包字节可重现。

### ascend-workflow

源 fig.svg：`fcc19a77d3b6daaca6c8922f70ae8948156d549b893ed3f3600a0b597da4efe7`。

| 输出 | SHA-256 |
|---|---|
| image/both SVG | `2500bde72605b1e6cd59d77d28d56bf870e9ddc76b19468096534a30fd17f7da` |
| image/both PNG | `2bad106f7a55236eef0509420439905c3d0dc89dfee46dd978d6274613440cde` |
| pptx PPTX | `33e514c0b868da2ee45ea917bd8f6fbf5d9e990866a5b9ba810c29587fbbe18c` |
| both PPTX | `663b6525a3826ef5383e4a246d0749196ac58f3b185b8cc49979409c069f5d27` |

### kv-offload

源 fig.svg：`be1ca122feebcf0dcab8e89d087978529326d217c0480dd6d672a667cf576348`。

| 输出 | SHA-256 |
|---|---|
| image/both SVG | `50034310920ef207c76d7095227df82bdaf40fbdf6e01f448e84b431a75bc00c` |
| image/both PNG | `f04519f1c541650385bf5874e90bfa815ef6e6efbf847a46e495b401173707e5` |
| pptx PPTX | `154389335024258f80281b7ad49c34e9ff4e73d002f3f556c5374bfb11498453` |
| both PPTX | `0e9f9715fb30e05d195e54530c0b10bf8b152b76c8192092a5a5cd6e22686bc2` |

长标签版源 SHA：`8f4e1e36a253ab0bdf3342d014ebed3eccba0c240ef86cce3f66dd7c56de9099`。源图仍是唯一几何来源，没有重绘、Scene IR 或 PNG/PDF/PPTX 反向转换。

## 复现与环境

```sh
python -m unittest discover -s tests -p "test_figgenie*.py" -v
python tools/validate_figgenie_exports.py \
  --upstream /path/to/FigGenie-paper-diagram-skill \
  --out /new/empty/acceptance-directory
```

复现脚本会重新生成六组输出、完整实际命令、返回码、manifest、哈希和对象清单；其通过状态仅表示结构检查，视觉结果需另行实际看图。原生工具使用固定上游提交时间 SOURCE_DATE_EPOCH，避免 FontTools 子集时间戳差异；不修改源 SVG。

环境：Python 3.11.0、Playwright 1.61.0、Chromium 149.0.7827.55（revision 1228）、python-pptx 1.0.2、FontTools 4.68.0；LibreOfficeDev 26.8.0.0.alpha0（build 2c87e51eeaa2b413ff4ae097b2705eea1995d8e5）；PowerPoint 16.113.4（not_run）。

LibreOffice 仅以 soffice --headless --convert-to png:impress_png_Export 做 QA。默认精简字体配置曾发生衬线回退；通过检查进程的 FONTCONFIG_FILE 指向本机字体目录后重渲染通过，无系统设置修改。

保留 warning：两个 spec 的 330 pt 高度超过论文双栏 p95 313 pt（样例为 presentation）；Ascend lint 0 errors/1 warning（四档字号）；KV lint 0 errors/4 warnings（四档字号、两条 1 pt 对齐差、容器标题偏心 4.2 pt）。TeX Gyre Heros 在本机 PPT 映射到 Helvetica Neue / Microsoft YaHei，不保证跨渲染器像素一致。
