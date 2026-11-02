# FigGenie 本地修复与验收（2026-11-02）

本次在 macOS 独立 clone 完成。基线 main 为 `cfa7b5db017b4e1d89546b79f7f886714dc42997`，分支 `fix/figgenie-pptx-shadow-and-validation`。原工作区没有该仓库；未清理、重置其他工作。远端备份 `backup/main-before-figgenie-20261102-d195af9` 和旧特性分支保留，PR #1 仍开放且未合并。

FigGenie 固定为 `c136a6aeefc6f6fe11fc615a5199cca57be3322a`，验收后 checkout 干净；没有修改上游。所有最终输出只取自对应冻结的 `fig.svg`，没有重新绘图、Scene IR、第二套坐标，也没有反向转换。

## 结果

| 检查 | 状态 | 证据/边界 |
|---|---|---|
| 两案例 × image/pptx/both | passed | 6/6；spec validate、check/lint/Chromium、适用的 embed_fonts/svg2pptx/pptx_check 均返回 0 |
| 浏览器视觉检查 | passed | 1800×990；两案例和长标签版本实际看图，无遮挡/截断/意外阴影 |
| LibreOffice 视觉检查 | passed | 四份模式 PPTX + 长标签版本；直接导出 PNG，额外阴影消失 |
| PowerPoint | not_run | CUA 长时间延迟；选中目标后“打开”不可用并返回 noWindowsAvailable，未打开目标文件；[实机尝试记录](powerpoint-qa/qa.json) |
| 导出相关测试 | passed | 22 项，含 9 项兼容处理测试（多子案例） |
| 范围内仓库回归 | passed | 101 passed + 后续 3 项 draw.io runtime passed，0 failed，1 not_run；配色另 13 项、报告契约另 24 项通过 |
| 原生 draw.io runtime | passed | 后续启用已有 Chromium 补跑 3 项，均通过；[日志](legacy-browser-regression.txt) |
| TikZ runtime | not_run | 1 项 TeX/Poppler 依赖缺失，不影响当前 FigGenie 链 |
| 旧 PDF 交付检查 | excluded | 用户中途明确取消；保留初轮日志，不再安装/修复其依赖 |
| Inkscape | not_run | 本机未安装；当前原生浏览器导出不依赖它 |
| 自动语义重连、OMML | not_run | 本次没有移动 PPT 对象测试或公式输入，不作承诺 |

详细结果：[六组命令/结构/哈希](accepted-modes/acceptance.json)、[导出测试](figgenie-tests.txt)、[范围内回归](scoped-regression.json)、[附加回归](additional-regression.json)、[视觉记录](visual-review.json)、[环境](environment.json)。

## 阴影修复边界

上游对象虽带空 `effectLst`，仍以 `effectRef idx=2` 引用带 `outerShdw` 的主题样式。封装只处理刚写入临时目录的 PPTX，按 slide → layout → master → theme 找到实际引用，仅将 shadow-only `effectLst` 的对象引用置 0。Ascend 修改 13 处，KV Offload 修改 19 处；主题本身不改。

源图显式 filter/CSS 阴影等不支持效果拒绝导出；无阴影引用、idx=0、对象显式效果保留。混合效果和不明确主题关系拒绝处理。只替换目标索引字节，验证其他 XML 不变；所有未修改 ZIP part 字节保留。测试覆盖文字、对象数、ID、几何、组和连接线、两个主题以及坏包/坏 XML。兼容处理的对象清单及前后 SHA 均写入各 manifest。

新文件完成兼容处理、pptx_check 与源哈希复核后才发布。默认拒绝非空输出目录；即使显式允许覆盖，生成、兼容、检查或源变更失败也保留原 PPTX。真实 CLI 负例见 [negative-checks/checks.json](negative-checks/checks.json)：手改标记文件 SHA 未变，禁止 SVG 效果及非法 spec 返回明确错误；非法输入不是验收失败。

## 源与产物 SHA-256

### ascend-workflow

源 `fig.svg`：`fcc19a77d3b6daaca6c8922f70ae8948156d549b893ed3f3600a0b597da4efe7`（三次完全相同）。

| 模式 | 产物 | SHA-256 |
|---|---|---|
| image | [fig.final.svg](accepted-modes/ascend-workflow/image/fig.final.svg) | `2500bde72605b1e6cd59d77d28d56bf870e9ddc76b19468096534a30fd17f7da` |
| image | [fig.png](accepted-modes/ascend-workflow/image/fig.png) | `2bad106f7a55236eef0509420439905c3d0dc89dfee46dd978d6274613440cde` |
| pptx | [fig.pptx](accepted-modes/ascend-workflow/pptx/fig.pptx) | `33e514c0b868da2ee45ea917bd8f6fbf5d9e990866a5b9ba810c29587fbbe18c` |
| both | [fig.final.svg](accepted-modes/ascend-workflow/both/fig.final.svg) | `2500bde72605b1e6cd59d77d28d56bf870e9ddc76b19468096534a30fd17f7da` |
| both | [fig.png](accepted-modes/ascend-workflow/both/fig.png) | `2bad106f7a55236eef0509420439905c3d0dc89dfee46dd978d6274613440cde` |
| both | [fig.pptx](accepted-modes/ascend-workflow/both/fig.pptx) | `663b6525a3826ef5383e4a246d0749196ac58f3b185b8cc49979409c069f5d27` |

[浏览器预览](accepted-modes/ascend-workflow/both/fig.png) · [LibreOffice 预览](libreoffice-qa/ascend-workflow-both-system-fonts/fig.png) · [未修复对照](libreoffice-qa/ascend-workflow-before-shadow-fix/fig.png)

### kv-offload

源 `fig.svg`：`be1ca122feebcf0dcab8e89d087978529326d217c0480dd6d672a667cf576348`（三次完全相同）。

| 模式 | 产物 | SHA-256 |
|---|---|---|
| image | [fig.final.svg](accepted-modes/kv-offload/image/fig.final.svg) | `50034310920ef207c76d7095227df82bdaf40fbdf6e01f448e84b431a75bc00c` |
| image | [fig.png](accepted-modes/kv-offload/image/fig.png) | `f04519f1c541650385bf5874e90bfa815ef6e6efbf847a46e495b401173707e5` |
| pptx | [fig.pptx](accepted-modes/kv-offload/pptx/fig.pptx) | `154389335024258f80281b7ad49c34e9ff4e73d002f3f556c5374bfb11498453` |
| both | [fig.final.svg](accepted-modes/kv-offload/both/fig.final.svg) | `50034310920ef207c76d7095227df82bdaf40fbdf6e01f448e84b431a75bc00c` |
| both | [fig.png](accepted-modes/kv-offload/both/fig.png) | `f04519f1c541650385bf5874e90bfa815ef6e6efbf847a46e495b401173707e5` |
| both | [fig.pptx](accepted-modes/kv-offload/both/fig.pptx) | `0e9f9715fb30e05d195e54530c0b10bf8b152b76c8192092a5a5cd6e22686bc2` |

[浏览器预览](accepted-modes/kv-offload/both/fig.png) · [LibreOffice 预览](libreoffice-qa/kv-offload-both-system-fonts/fig.png) · [未修复对照](libreoffice-qa/kv-offload-before-shadow-fix/fig.png)

image 与 both 的字体嵌入 SVG、PNG SHA 完全相同；pptx 与 both 的幻灯片 XML、原生对象清单完全相同。PPTX ZIP 时间戳可能不同，所以单独记录各文件 SHA，不要求 ZIP 整包哈希相等。

首次 `modes/` 试跑发现 FontTools 子集字体的时间戳导致嵌入 SVG 字节不同（源 SVG 与 PNG 相同），验收脚本停止；封装现为原生工具提供固定上游提交时间 `SOURCE_DATE_EPOCH`，`accepted-modes/` 六组重跑通过。首次结果保留，不作为最终交付。

## 原生对象与修改重导

| 案例 | 文本框 | 基本形状 | connector | freeform | 分组 | picture |
|---|---:|---:|---:|---:|---:|
| Ascend | 13 | 6 | 2 | 5 | 10 | 0 |
| KV Offload | 17 | 10 | 7 | 2 | 15 | 0 |

不是整页位图。存在原生文字、形状、连接线/自由路径和分组；单对象组可能由上游保留为带语义名称的独立对象。`connection_binding_count=0`，不能将原生 connector/freeform 可编辑解释成移动后自动保持语义连接。

本次在 [long-label-source/fig.svg](long-label-source/fig.svg) 把 Vector 标签改为两行 “Generate Vector / from workload”，只更新对应 spec 版本与标签，再运行 both；没有编辑 PPTX 后反推。源 SHA 从 `fcc19a77d3b6daaca6c8922f70ae8948156d549b893ed3f3600a0b597da4efe7` 变为 `8f4e1e36a253ab0bdf3342d014ebed3eccba0c240ef86cce3f66dd7c56de9099`。

[稳定性检查](long-label-source/stability.json) 证明全部 SVG ID 相同，仅 `n:vector` 组变化，所有边与无关模块不变；PPTX 语义对象名称保留，去除上游重新分配的数字 ID 后也只有 `n:vector` 不同。新增文本会使部分 primitive 数字 ID 变化，不能承诺跨重导数字 ID 稳定。兼容处理自身不改变任何数字 ID。

[长标签浏览器预览](long-label-export/fig.png) · [可编辑 PPTX](long-label-export/fig.pptx) · [LibreOffice 预览](libreoffice-qa/long-label-system-fonts/fig.png)。

## 实际接口与复现

```sh
python tools/validate_figgenie_exports.py \
  --upstream /path/to/FigGenie-paper-diagram-skill \
  --out /new/empty/acceptance-directory
```

每个 manifest 保存完整命令、返回码、日志位置和 `SOURCE_DATE_EPOCH`。链路为 `spec_validate.py spec.json` → `check.py fig.svg --spec spec.json --scale 3 --out-dir checks --no-preview`（内部执行 lint 与 Chromium 渲染）→ image/both 的 `embed_fonts.py`；pptx/both 调用 `svg2pptx.py`、本仓兼容处理、`pptx_check.py`。PNG 直接来自原生 check 渲染，不通过 PPTX 或 PDF。

image 单独在 `.figgenie-image-venv` 运行，实际确认未安装 python-pptx 和 lxml，输出成功：[manifest](image-without-pptx/manifest.json)。封装自身仍仅用 Python 标准库。

LibreOffice 检查使用 `soffice --headless --convert-to png:impress_png_Export`，输出仅为 QA 图，不参与最终导出。详细命令与 SHA 见 [libreoffice-qa/commands.json](libreoffice-qa/commands.json)。系统字体路径仅通过检查进程的 `FONTCONFIG_FILE` 指定，没有改系统配置。

## 版本与剩余 warning

- Python 3.11.0；Playwright 1.61.0；Chromium 149.0.7827.55/revision 1228；python-pptx 1.0.2；FontTools 4.68.0。
- LibreOfficeDev 26.8.0.0.alpha0，build `2c87e51eeaa2b413ff4ae097b2705eea1995d8e5`。PowerPoint 已安装版本 16.113.4，运行状态以上方实机结果为准。
- 两个 spec 都有 330 pt 高度超过论文双栏 p95 313 pt 的 warning：此处是 presentation 场景，未更改冻结几何。
- Ascend lint 0 errors / 1 warning：四档字号 9/10/11/16 pt；KV lint 0 errors / 4 warnings：同一字号警告、两条 1 pt 边缘对齐差、容器标题偏心 4.2 pt。已目视检查，内容可读且连线完整；不宣称严格 lint 零警告。
- SVG 的 TeX Gyre Heros 由上游在本机映射到 Helvetica Neue / Microsoft YaHei。字体/抗锯齿/箭头细节不保证跨浏览器与 Office 像素一致。
- 默认沙箱首次阻止 Chromium MachPort；经正常授权运行原生检查后成功，不改安全或网络设置。
- LibreOffice 初次默认字体配置发生衬线回退，已拒绝该结果；指定本机字体路径后重渲染，字体与布局正常，stderr 为空。
- 旧 PDF 交付检查初轮出现 9 失败（缺 pdftotext），之后用户明确取消该范围；Poppler 安装已中止，已安装依赖未自动卸载。旧记录保留在 regression.txt，不列为当前 FigGenie 失败。

PowerPoint 检查未通过到实际文件打开阶段，因此不记 visual failed 或 passed，而记 `not_run`。该限制仍需在 PowerPoint 手动打开交付文件补验。自动化在打开对话框阶段失去可靠窗口控制，未保存或改写任何源/产物/已有用户文档。
