# K01 - 边界复述
输入是已准备上下文
唯一工具是只读 `query_asset_context`
成功链是三状态、两次向前迁移；异常可转 `MANUAL`

**核心数据*
Agent本身不创造这些ID，它只是 D03 （查案服务）的下游消费者
- case_id：来自ContextResult，它是D03的查案业务服务在成功调用Stub后，从外部系统（目前是假数据）获取并保存的
- evidence_refs：来自ContextResult，它是D03绑定好的证据引用列表
- correlation_id：来自D02告警接收服务中，创建Investigation时生成的追踪标识，在D03查案业务服务中被透传并保存在ContextResult中
今天Agent运行时，在初始化时的时候，必须通过ContextResult来获取它们，不可以自己凭空生成
*Agent的运行规则*
— 一次只读调用
边界：Agent在一次完整的调查中，最多只能调用一次外部工具，这个工具必须是只读的，不能执行任何修改、删除或写入操作
— 预算初始1
边界：当Agent Runtime被创建时，它的工具调用预算被硬编码为1。这切断了Agent陷入死循环或产生巨额API费用的可能性
- 成功消费到0仍进入ENRICHED
边界：当Agent成功执行了那唯一的一次工具调用后，预算从1变为0。预算归零且任务完成，这是正常的成功路径。此时状态必须转为ENRICHED，流程正常结束。
- 无循环 
边界：Agent的执行逻辑不是循环的，代码中不出现while True或类似的递归重试机制。状态只能单向流转：CONTEXT_READY → ENRICHING → ENRICHED（或异常终止）

*问答*
1.输入：D04 运行开始前必须从 D03 实际拿到什么？请写出三个字段及其当前真实值；如果某项缺失，请明确写“缺失”。
-必须拿到已准备上下文，三个字段是case_id（当前真实值"case-demo-001"）、evidence_refs（当前真实值"ev-001"）、correlation_id（真实值，因为每次请求是动态生成的，或由上游业务请求一并传入,在查案业务里也保留这个真实值）
2.输出：正常完成时，Agent的最终状态、工具调用次数、剩余预算和执行轨迹应是什么？人工出口时必须保留什么？
-正常完成时，Agent的最终状态应该是ENRICHED，工具只调用1次，剩余预算为0，执行轨迹是CONTEXT_READY → ENRICHING → ENRICHED，包含一条记录，记录query_asset_context被调用了1次，以及返回的结果摘要，人工出口时必须保留`stop_reason`与`trace`
3.完成定义：允许的成功状态迁移是什么？唯一工具叫什么？成功调用后预算变成多少，为什么仍然算成功？
-允许的成功状态迁移意思就是只允许走这一条路径：CONTEXT_READY → ENRICHING → ENRICHED，走完就停，绝不循环。唯一工具叫做query_asset_context，成功调用后预算变成0。仍然算成功是因为预算从1变为0就是正常消耗，工具调用已成功完成，数据已增强。
4.失败出口：缺输入、工具超时、调用前预算为 0、试图发起第 2 次调用，分别应进入什么状态？哪些情况必须使用 stop_reason=TOOL_BUDGET_EXHAUSTED？
-四种情况都是进入MANUAL状态，调用前预算为 0、试图发起第 2 次调用这两种情况必须使用stop_reason=TOOL_BUDGET_EXHAUSTED
5.smoke 命令：D04 聚焦测试的完整命令是什么？
-`python -m pytest tests/test_agent_minimal_flow.py`

# K04 - runtime + API
*检查：*
*1.场景一：正常成功*
进入 `ENRICHING`，预算减 1，调用一次工具，然后进入 `ENRICHED` 
断言 Runtime 和 Stub 调用次数为 1、剩余预算为 0、完整 trace
路径：CONTEXT_READY → ENRICHING → ENRICHED
*2.场景二：缺输入*
在工具调用前进入 `MANUAL`，停止原因：`MISSING_CONTEXT_INPUT`
覆盖7种字段缺失的组合情况；预算仍为 1、调用次数为 0
路径：CONTEXT_READY → MANUAL
*3.场景三：工具超时*
已发起一次调用并消费预算，随后进入 `MANUAL`，停止原因：`TOOL_TIMEOUT`
断言调用一次、不重试、预算为 0、
路径：CONTEXT_READY → ENRICHING → MANUAL
*4.场景四：调用前预算为 0*
不调用工具，直接进入 `MANUAL`，停止原因：`TOOL_BUDGET_EXHAUSTED`
Runtime 和 Stub 调用次数均为 0
路径：CONTEXT_READY → MANUAL
*5.场景五：第 2 次调用企图*
首次成功；第二次在触碰 Stub 前停止，停止原因：`TOOL_BUDGET_EXHAUSTED`
Stub 总调用次数仍为 1，保留首次完整 trace 后追加 `MANUAL`
路径：CONTEXT_READY → ENRICHING → ENRICHED → MANUAL
*6.场景六：非法迁移*
非`CONTEXT_READY`的入口在消费预算前进入 `MANUAL`，停止原因：`INVALID_STATE_TRANSITION`
覆盖`ENRICHING`、`ENRICHED`、`MANUAL`三种入口，并禁止成功路径跳过 `ENRICHING`
三种路径：
ENRICHING → MANUAL（从 ENRICHING 非法启动）
ENRICHED → MANUAL（从ENRICHED非法启动）
MANUAL → MANUAL（从MANUAL非法启动）

*自测题*
1. 为什么今天的运行时不能在工具超时时继续重试？为什么成功调用消费预算到 0 后仍应进入 `ENRICHED`？请结合工具预算和停止条件说明。
- 工具超时后不能继续重试，是因为工具预算只有1，且禁止循环和重试。
成功调用消费预算到0后仍应进入ENRICHED，因为预算表示最多允许调用几次，不是剩余预算必须大于0才算成功。
- 依据：预算1 → 进入ENRICHING → 调用工具 → 预算0，如果工具成功返回，说明工作已经完成，因此进入ENRICHED。如果工具超时，这一次调用已经发生，预算也已经用完，因此进入MANUAL，输出TOOL_TIMEOUT，不能再次调用。只有两种情况停止原因是TOOL_BUDGET_EXHAUSTED：调用前预算为0和试图发起第 2 次调用。
- 项目证据：/app/services/agent_runtime.py和/tests/test_agent_minimal_flow.py
- 边界：只允许一个只读工具query_asset_context的教学替身。不能增加重试、循环、其他工具、真实网络、RAG 或模型调用。工具超时只能转交 MANUAL，不能伪造成功的结果。
2. `CONTEXT_READY → ENRICHING → ENRICHED` 中，每次迁移分别证明了什么？
- 两次迁移分别证明了：已经满足调用前条件和工具已经成功完成。
- 依据：CONTEXT_READY → ENRICHING 证明了以下几件事：初始状态合法，请求中的case_id、evidence_refs、correlation_id字段都存在，调用前预算至少为1，Runtime准备发起唯一工具的调用；ENRICHING → ENRICHED证明了以下几件事：query_asset_context 已成功返回，工具实际只调用1次，预算已正常消费到0，不需要继续调用工具，运行可以结束。
- 项目证据：/app/services/agent_runtime.py和/tests/test_agent_minimal_flow.py
- 边界：ENRICHED 只表示本次业务任务已按规则完成，但是不代表已经作出安全结论、完成真实资产调查或允许自动处置。
3. 当缺少 `evidence_refs` 时，为什么应记录 `MANUAL`、`stop_reason` 与 `trace`，而不是构造一个结果继续运行？
- 因为 Runtime 没有获得证据输入，就不能可靠地调用工具或构造enrichment结果。stop_reason 说明为什么停止，trace 说明流程在哪里停止。如果构造结果继续运行，把没有证据伪装成已经完成enrichment，属于伪造结果，后续的业务服务也不可靠了
正确行为是记录：state: MANUAL
stop_reason: MISSING_CONTEXT_INPUT
trace: CONTEXT_READY → MANUAL
tool_call_count: 0
预算保持为 1、调用次数为 0，证明输入校验发生在工具调用之前。
- 项目证据：/app/services/agent_runtime.py和/tests/test_agent_minimal_flow.py
- 边界：不会自动补齐证据、猜测没写的字段、查询真实系统或用模型生成替代证据。缺少输入只能诚实停止并交给人工处理。