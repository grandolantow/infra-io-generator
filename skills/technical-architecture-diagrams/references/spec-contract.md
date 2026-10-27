# 来源与可见事实契约

JSON包含 `id,title,subtitle,source_url,paper_title,source_locator,scope_in,scope_out,facts,baseline,proposed,mechanism_notes,uncertainties`。

`facts` 为 `{id,statement,locator}` 列表。每个方案包含 `name,nodes,edges`。节点为 `{id,label,detail}`；边为 `{from,to,label,kind,temporal_scope?}`。kind采用data/control/selection/state_read/state_write/state_update/residual/communication。节点ID只表达语义身份，不编码坐标。

状态写入不一定是延迟反馈。当前求值中的状态生产/消费用 `state_write` 或data并参与DAG排序。只有已确认跨步的反馈用state_update，并标temporal_scope为next_step或next_iteration。不能因边携带状态就把它从依赖排序删除。三轮中SSD保留了此类失败，需下一轮专项回归。

用独立 `required_visual_facts` 记录哪些事实需要在图上出现，并对应可见节点、边、数学短语。scope外或背景事实不计入图示覆盖分母。不得仅凭节点边数量判断覆盖率。

布局JSON保存canvas、graphs、节点bbox和边折线；事实JSON不保存排版选择。下一步修改布局不重写来源事实。对事实的修正保留前后哈希和原因，并检查所有候选。

示例流程：冻结事实 → 生成结构不同候选 → 核对可见事实 → 实际渲染 → 改布局 → 对比未改区域。文件模板可参考主Skill附带的公开Attention Residuals例子；勿把其参数移植到新模型。
