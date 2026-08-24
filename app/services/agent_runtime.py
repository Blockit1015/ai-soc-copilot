#真正的执行文件
from app.contracts.agent import (
    AgentRunResult,
    AgentState,
    RunStep,
    StopReason,
)
from app.ports.tool_gateway import ToolGateway, ToolTimeoutError

#构造函数,接收外部注入的工具（tool_gateway）和初始预算
class AgentRuntime:
    def __init__(
        self,
        tool_gateway: ToolGateway,
        initial_tool_budget: int = 1, #初始预算默认为1
    ) -> None:
        self._tool_gateway = tool_gateway
        self._tool_budget_initial = initial_tool_budget
        self._tool_budget_remaining = initial_tool_budget
        self._tool_call_count = 0
        self._trace: list[RunStep] = []
        self._has_run = False

#定义运行方法，接收外部传入的参数
    def run(
        self,
        *,
        state: AgentState,
        case_id: str,
        evidence_refs: list[str],
        correlation_id: str,
    ) -> AgentRunResult:
        if self._has_run:
            return self._stop_repeated_run()

        self._has_run = True
        self._append_state(state) #记录初始状态,记入黑匣子（Trace）

        #检查状态和参数的合法性，如果不合法就返回人工处理结果
        if state != AgentState.CONTEXT_READY:
            return self._manual_result(StopReason.INVALID_STATE_TRANSITION)

        if not case_id or not evidence_refs or not correlation_id:
            return self._manual_result(StopReason.MISSING_CONTEXT_INPUT)

        if self._tool_budget_remaining < 1:    #检查预算
            return self._manual_result(StopReason.TOOL_BUDGET_EXHAUSTED)

 #通过所有校验后，正式进入ENRICHING状态，先扣预算、记录，再去调用外部工具
        self._append_state(AgentState.ENRICHING)
        self._tool_budget_remaining -= 1
        self._tool_call_count += 1

#调用外部工具查询资产上下文，如果超时就返回人工处理结果
        try:
            self._tool_gateway.query_asset_context(
                case_id=case_id,
                evidence_refs=evidence_refs,
                correlation_id=correlation_id,
            )
        except ToolTimeoutError:
            return self._manual_result(StopReason.TOOL_TIMEOUT)

     #成功路径：工具调用成功，就进入ENRICHED状态，记录状态并返回结果
        self._append_state(AgentState.ENRICHED)
        return self._result(state=AgentState.ENRICHED)

    def _stop_repeated_run(self) -> AgentRunResult:
        if self._tool_budget_remaining < 1 or self._tool_call_count >= 1:
            return self._manual_result(StopReason.TOOL_BUDGET_EXHAUSTED)
        return self._manual_result(StopReason.INVALID_STATE_TRANSITION)

    def _manual_result(self, stop_reason: StopReason) -> AgentRunResult:
        self._append_state(AgentState.MANUAL)
        return self._result(
            state=AgentState.MANUAL,
            stop_reason=stop_reason,
        )

    def _append_state(self, state: AgentState) -> None:
        self._trace.append(RunStep(state=state))

    def _result(
        self,
        *,
        state: AgentState,
        stop_reason: StopReason | None = None,
    ) -> AgentRunResult:
        return AgentRunResult(
            state=state,
            tool_budget_initial=self._tool_budget_initial,
            tool_budget_remaining=self._tool_budget_remaining,
            tool_call_count=self._tool_call_count,
            trace=list(self._trace),
            stop_reason=stop_reason,
        )
