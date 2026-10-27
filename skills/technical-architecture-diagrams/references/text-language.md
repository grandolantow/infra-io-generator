# 绘图文本语言规则

默认 profile：`diagram-en-prose-zh`。共享机器配置为 `language-profile.json`，适用于图本身和图周边文字，规则归绘图产物，不归 PPT 主流程。

## 按语义角色，不按框内外

- **图中短标签与短注释用英文**：功能节点 `node_label`、图内短标题 `diagram_title`、分区短标题 `section_title`、图例 `legend`、箭头旁短注释 `edge_annotation`、图中其他短注释 `short_annotation`。箭头在框外不代表要改中文。
- **可脱离图独立阅读的长段解释用中文**：`prose`。包括详细机制解说、来源边界和限制段落；即使被大容器包住也仍是 prose。不是按字数阈值自动划分。
- **术语、缩写、模型名、公式、变量保持英文/符号**：`technical_term`、`model_name`、`formula`、`variable`；紧凑引用 `source_citation` 保持来源写法。中文 prose 中可嵌入 `PCP`、`KV Cache`、`K3`、`QKᵀ`。
- 中文长段与英文图内短注释可以同时出现。不能把整段英文说明伪标为技术术语，也不能为通过检查改变公式或技术含义。
- 不静默翻译用户或来源文本；语言修改须保持事实、稳定 ID、参数与数据。显式其他语言需求应记录 override 并复核，不伪称通过本 profile。

## 正反例

| 语义角色 | 正例 | 反例/需改 |
|---|---|---|
| node_label | `KV Cache` | `键值缓存模块` |
| edge_annotation | `copy on hit` / `on eviction` | `命中时复制`（作为图中箭头短注释） |
| section_title | `Communication` | `通信阶段`（作为图内分区短标题） |
| legend | `Compute` / `Communication` | 图内短图例一律改中文 |
| prose | `命中后只复制所需条目；KV Cache 的有效期由请求状态决定。` | 可脱离图阅读的整段英文解释 |
| formula / variable | `QKᵀ / √d` / `h_t` | 为满足中文检查改写公式 |

## 显式标注与检查

报告 IR 设置 `language_profile`；每个有文字的 glyph/path 记录 `text_role`，视图 title/scope 使用 `title_text_role`/`scope_text_role`。常见 title 是英文 diagram_title，长 scope 是中文 prose，但作者必须按实际用途明确标注。顶层 `surrounding_texts` 记录宿主展示的 `{id,text,text_role}`；图周边 prose 同属绘图 QA，需与实际 HTML 可见文本核对，不能只检查图中央。

模型 draw.io 中每个有 value 的 mxCell 记录 `text_role`。显式角色不随容器坐标变化。共享检查器支持两类源：

```sh
python scripts/check_language.py --input diagram.json --format report --profile diagram-en-prose-zh --output language-qa.json
python scripts/check_language.py --input model.drawio --format model --profile diagram-en-prose-zh --output language-qa.json
```

检查仅覆盖显式角色完整性与有限字符提示，**不判断短文本/长段的真实语义**。英文角色含汉字会失败；prose 不含汉字仅提出疑点，不把汉字检测当语义证明。角色与术语例外仍需人工/Agent复核。

QA 绑定 profile 和输入 SHA-256。`contract_status=pass` 只表示合同检查无失败，`semantic_review=not_run` / `status=needs_review` 保留语义复核边界；还须实渲染核对完整性与可读性。PPT adapter 仅透传 profile、调用 checker、消费状态，不另建规则、不自动翻译。
