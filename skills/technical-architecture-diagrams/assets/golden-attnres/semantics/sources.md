# Attention Residuals golden 来源与范围

- 固定论文：[arXiv:2603.15031v1](https://arxiv.org/pdf/2603.15031v1)。Fig.1为三方案；§2把Attention/MLP各视为子层；§3.1 Eq1–4为Full；§3.2 Eq5–6和Fig.2为Block。
- 官方仓库：[MoonshotAI/Attention-Residuals](https://github.com/MoonshotAI/Attention-Residuals)。通过GitHub插件读取README，并锁定commit `85e22310fe5ee860b4a023de312d791de8a5a5e6`，README blob `a8cc8834a75d384891481d7d414853cafc1407e9`。
- 固定代码说明：[README at commit](https://github.com/MoonshotAI/Attention-Residuals/blob/85e22310fe5ee860b4a023de312d791de8a5a5e6/README.md)。其中block_attn_res说明候选、keys、values、softmax候选轴，forward维护局部和并区分attention/MLP聚合参数。
- arXiv HTML v1转换不完整，数学核验以PDF为准。
- 统一教学示例：4子层、2块，每块2子层。不是模型真实深度、固定层型、默认block_size或最优N。
- 实际工具成图、检查与范围见 drawio-review.json、backend-reviews-refined.json 和各后端 trial/qa 记录；这些不是用户审美认可。

关键边界：当前partial是Block候选之一（块内第一子层除外），局部和只含原始子层输出。Standard固定单位系数不能替成softmax均匀平均。
