#一、正常成功的情况
import pytest
def test_ready_context_calls_read_only_tool_once_and_finishes_enriched() -> None: #函数签名

    #导入工具
    from app.adapters.read_only_tool_stub import ReadOnlyToolStub #导入工具替身，模拟外部只读工具，返回假数据，不真正联网
    from app.contracts.agent import AgentState #导入状态枚举，定义 CONTEXT_READY / ENRICHING / ENRICHED 等状态常量
    from app.services.agent_runtime import AgentRuntime #导入被测对象，这是核心逻辑

    #测试准备
    tool_gateway = ReadOnlyToolStub()  #创建一个 Stub 实例，这个Stub会记录自己"被调了几次、调了什么工具"，供后续断言使用
    runtime = AgentRuntime(tool_gateway=tool_gateway) #创建被测对象AgentRuntime，通过构造函数注入传入tool_gateway

    #执行：调用 runtime.run() 方法，传入四个参数
    result = runtime.run(
        state=AgentState.CONTEXT_READY,  #指定Agent的初始状态
        case_id="case-demo-001",  #D03查案系统确认的案件ID
        evidence_refs=["ev-demo-001"],  #D03查案系统确认的证据引用列表
        correlation_id="corr-d04-inspect-001", #D02接收告警系统透传的追踪ID
    )

    #断言部分：这里是边界要求
    assert result.state == AgentState.ENRICHED  #最终状态必须是ENRICHED
    assert result.tool_budget_initial == 1   #初始预算为1
    assert result.tool_budget_remaining == 0  #调用后预算归0
    assert result.tool_call_count == 1  #工具只被调用1次
    assert tool_gateway.call_count == 1  #Stub的实际调用次数为 1
    assert tool_gateway.called_tool_names == ["query_asset_context"]  #调用的工具是query_asset_context
    assert [step.state for step in result.trace] == [     #Trace 状态顺序严格为READY → ENRICHING → ENRICHED
        AgentState.CONTEXT_READY,
        AgentState.ENRICHING,
        AgentState.ENRICHED,
    ]

#二、缺输入的情况
@pytest.mark.parametrize(  # Pytest使用同一组断言运行下面7种缺失情况
    ("case_id", "evidence_refs", "correlation_id"),
    [
        ("", ["ev-demo-001"], "corr-d04-inspect-001"),
        ("case-demo-001", [], "corr-d04-inspect-001"),
        ("case-demo-001", ["ev-demo-001"], ""),
        ("", [], "corr-d04-inspect-001"),
        ("", ["ev-demo-001"], ""),
        ("case-demo-001", [], ""),
        ("", [], ""),
    ],
    #用ids给缺失情况起别名，方便在终端看到测试结果时快速定位是哪种缺失情况
    ids=[
        "missing-case-id",
        "missing-evidence-refs",
        "missing-correlation-id",
        "missing-case-id-and-evidence-refs",
        "missing-case-id-and-correlation-id",
        "missing-evidence-refs-and-correlation-id",
        "missing-all-context-inputs",
    ],
)

 #函数签名与动态接收
def test_missing_required_context_input_stops_in_manual_without_calling_tool(
    case_id: str,
    evidence_refs: list[str],
    correlation_id: str,
) -> None:
    from app.adapters.read_only_tool_stub import ReadOnlyToolStub
    from app.contracts.agent import AgentState, StopReason
    from app.services.agent_runtime import AgentRuntime

    tool_gateway = ReadOnlyToolStub()
    runtime = AgentRuntime(tool_gateway=tool_gateway)

    result = runtime.run(
        state=AgentState.CONTEXT_READY,
        case_id=case_id,  # 动态注入（可能是空字符串）
        evidence_refs=evidence_refs,  # 动态注入（可能是空列表）
        correlation_id=correlation_id,  # 动态注入（可能是空字符串）
    )

 #断言
    assert result.state == AgentState.MANUAL #输入不全，转入人工处理（MANUAL）
    assert result.stop_reason == StopReason.MISSING_CONTEXT_INPUT #给出停止原因“缺少上下文输入”
    assert result.tool_budget_remaining == 1 #预算初始是1，剩余还是1，证明了校验逻辑在消耗预算之前：输入不合法，直接拦截，不浪费资源
    assert result.tool_call_count == 0 #Agent 内部记录的工具调用次数为 0
    assert tool_gateway.call_count == 0 #工具替身（Stub）自己记录的调用次数也是 0
    assert [step.state for step in result.trace] == [
        AgentState.CONTEXT_READY,
        AgentState.MANUAL,
    ] #执行轨迹：CONTEXT_READY → MANUAL

#三、工具超时的情况
#这是针对运行时异常中断的测试
def test_tool_timeout_stops_in_manual_without_retry() -> None:
    from app.adapters.read_only_tool_stub import ReadOnlyToolStub
    from app.contracts.agent import AgentState, StopReason
    from app.services.agent_runtime import AgentRuntime

    tool_gateway = ReadOnlyToolStub(mode="timeout") #模拟网络超时
    runtime = AgentRuntime(tool_gateway=tool_gateway)

#执行触发
#执行轨迹：当run()被调用时，Runtime会先通过输入校验，
#然后将状态切换为ENRICHING，接着去调用tool_gateway.query_asset_context()
#就在这一瞬间，Stub因为mode="timeout" 抛出了超时异常，被 Runtime 捕获
    result = runtime.run(
        state=AgentState.CONTEXT_READY,
        case_id="case-demo-001",
        evidence_refs=["ev-demo-001"],
        correlation_id="corr-d04-inspect-001",
    )

#断言
    assert result.state == AgentState.MANUAL #最终状态是MANUAL，说明Runtime捕获了异常并切换到了人工处理
    assert result.stop_reason == StopReason.TOOL_TIMEOUT #停止原因是工具超时
    assert result.tool_budget_remaining == 0 #预算初始是1，调用了一次工具就超时了，所以剩余预算为0
    assert result.tool_call_count == 1 #Agent 内部记录的工具调用次数为 1
    assert tool_gateway.call_count == 1 #工具替身（Stub）自己记录的调用次数也是 1
    assert tool_gateway.called_tool_names == ["query_asset_context"] #调用的工具是query_asset_context
    #执行轨迹：CONTEXT_READY → ENRICHING → MANUAL，说明Runtime在ENRICHING阶段捕获了异常并切换到了人工处理
    assert [step.state for step in result.trace] == [
        AgentState.CONTEXT_READY,
        AgentState.ENRICHING,
        AgentState.MANUAL,
    ] 

#四、调用前预算为0
def test_zero_budget_before_call_stops_in_manual_without_calling_tool() -> None:
    from app.adapters.read_only_tool_stub import ReadOnlyToolStub
    from app.contracts.agent import AgentState, StopReason
    from app.services.agent_runtime import AgentRuntime

    tool_gateway = ReadOnlyToolStub() #创建一个Stub实例，这个Stub会记录自己"被调了几次、调了什么工具"，供后续断言使用，注意！这里创建的是正常模式的Stub，没有传mode="timeout"，这意味着外部工具本身是健康的、随时可以响应
    runtime = AgentRuntime(tool_gateway=tool_gateway, initial_tool_budget=0)

#执行触发
    result = runtime.run(
        state=AgentState.CONTEXT_READY,
        case_id="case-demo-001",
        evidence_refs=["ev-demo-001"],
        correlation_id="corr-d04-inspect-001",
    ) #三个字段全都有值，且初始状态是合法的CONTEXT_READY

    assert result.state == AgentState.MANUAL #最终状态是MANUAL，说明Runtime捕获了预算不足的情况并切换到了人工处理
    assert result.stop_reason == StopReason.TOOL_BUDGET_EXHAUSTED #停止原因是工具预算耗尽
    assert result.tool_budget_initial == 0 #初始预算为0
    assert result.tool_budget_remaining == 0 #剩余预算为0
    assert result.tool_call_count == 0 #Agent内部记录的工具调用次数为0
    assert tool_gateway.call_count == 0 #工具替身（Stub）自己记录的调用次数为0
    assert [step.state for step in result.trace] == [
        AgentState.CONTEXT_READY,
        AgentState.MANUAL,
    ] #执行轨迹：CONTEXT_READY → MANUAL，说明Runtime在CONTEXT_READY阶段就发现预算不足，直接切换到了人工处理

#五、第2次调用企图
def test_second_tool_call_attempt_stops_in_manual_without_another_call() -> None:
    from app.adapters.read_only_tool_stub import ReadOnlyToolStub
    from app.contracts.agent import AgentState, StopReason
    from app.services.agent_runtime import AgentRuntime

 #测试准备
    tool_gateway = ReadOnlyToolStub() #使用正常模式的Stub，且默认预算为1
    runtime = AgentRuntime(tool_gateway=tool_gateway)

#执行连续发起两次攻击（runtime.run() 负责检查预算）
    first_result = runtime.run( #第一次调用：合法输入，预期走通成功路径，消耗掉唯一的1点预算
        state=AgentState.CONTEXT_READY,
        case_id="case-demo-001",
        evidence_refs=["ev-demo-001"],
        correlation_id="corr-d04-inspect-001",
    )
    second_result = runtime.run( #第二次调用：输入合法，但此时预算是0，模拟重复提交
        state=AgentState.CONTEXT_READY,
        case_id="case-demo-001",
        evidence_refs=["ev-demo-001"],
        correlation_id="corr-d04-inspect-001",
    )

#断言
    assert first_result.state == AgentState.ENRICHED #第一次调用成功，最终状态是ENRICHED
    assert second_result.state == AgentState.MANUAL #第二次调用失败，最终状态是MANUAL
    assert second_result.stop_reason == StopReason.TOOL_BUDGET_EXHAUSTED #打上TOOL_BUDGET_EXHAUSTED（预算耗尽）的标签
    assert second_result.tool_budget_remaining == 0 #第二次调用前预算已经是0
    assert second_result.tool_call_count == 1 #第二次调用前，Agent内部记录的工具调用次数是1
    assert tool_gateway.call_count == 1 #第二次调用前，Stub必须确认自己总共只被触碰过 1 次
    assert tool_gateway.called_tool_names == ["query_asset_context"]
    assert [step.state for step in second_result.trace] == [
        AgentState.CONTEXT_READY,
        AgentState.ENRICHING,
        AgentState.ENRICHED,
        AgentState.MANUAL,
    ] #执行轨迹：CONTEXT_READY → ENRICHING → ENRICHED → MANUAL，说明Runtime在第二次调用时发现预算不足，直接切换到了人工处理

#六、非法迁移——从处理中、已完成或人工终态重新发起运行
   #非法初始状态的情况
@pytest.mark.parametrize( #穷举所有非法初始状态
    "starting_state_name",
    [
        "ENRICHING",
        "ENRICHED",
        "MANUAL",
    ],
    ids=["restart-from-enriching", "restart-from-enriched", "restart-from-manual"],
)
def test_non_entry_state_cannot_start_another_successful_run(
    starting_state_name: str,
) -> None:
    from app.adapters.read_only_tool_stub import ReadOnlyToolStub
    from app.contracts.agent import AgentState, StopReason
    from app.services.agent_runtime import AgentRuntime

    tool_gateway = ReadOnlyToolStub()
    runtime = AgentRuntime(tool_gateway=tool_gateway)
    starting_state = AgentState[starting_state_name]
#带着非法状态去执行
    result = runtime.run(
        state=starting_state,
        case_id="case-demo-001",
        evidence_refs=["ev-demo-001"],
        correlation_id="corr-d04-inspect-001",
    )
#断言
    assert result.state == AgentState.MANUAL #Runtime会捕获非法状态并切换到人工处理
    assert result.stop_reason == StopReason.INVALID_STATE_TRANSITION #打上INVALID_STATE_TRANSITION（非法状态迁移）的标签
    assert result.tool_budget_remaining == 1 #预算初始是1，剩余还是1，证明了校验逻辑在消耗预算之前，输入不合法，直接拦截
    assert result.tool_call_count == 0 #Agent 内部记录的工具调用次数为 0
    assert tool_gateway.call_count == 0 #工具替身（Stub）自己记录的调用次数也是 0
    assert [step.state for step in result.trace] == [
        starting_state,
        AgentState.MANUAL,
    ] #执行轨迹：非法初始状态 → MANUAL

#非法迁移路径的情况
def test_success_trace_does_not_skip_enriching_state() -> None:
    from app.adapters.read_only_tool_stub import ReadOnlyToolStub
    from app.contracts.agent import AgentState
    from app.services.agent_runtime import AgentRuntime

  #使用合法的输入和工具替身，触发成功路径，拿到它的result.trace，然后检查这条轨迹
    tool_gateway = ReadOnlyToolStub()
    runtime = AgentRuntime(tool_gateway=tool_gateway)
    result = runtime.run(
        state=AgentState.CONTEXT_READY,
        case_id="case-demo-001",
        evidence_refs=["ev-demo-001"],
        correlation_id="corr-d04-inspect-001",
    )

    transitions = list(zip(result.trace, result.trace[1:])) #提取状态迁移对
    allowed_transitions = { #合法的状态跳转
        (AgentState.CONTEXT_READY, AgentState.ENRICHING),
        (AgentState.ENRICHING, AgentState.ENRICHED),
    }
  #断言
    assert result.state == AgentState.ENRICHED #最终状态必须是ENRICHED
    assert result.tool_budget_remaining == 0 #调用后预算归0
    assert result.tool_call_count == 1 #Agent 内部记录的工具调用次数为 1
    assert tool_gateway.call_count == 1  #工具替身（Stub）自己记录的调用次数也是 1
    assert transitions #确保有状态迁移发生
    assert all(
        (from_step.state, to_step.state) in allowed_transitions
        for from_step, to_step in transitions
    ) #确保所有状态迁移都是合法的（正向断言）
    assert (AgentState.CONTEXT_READY, AgentState.ENRICHED) not in {
        (from_step.state, to_step.state)
        for from_step, to_step in transitions
    }  #确保没有跳步的非法状态迁移（反向断言）
