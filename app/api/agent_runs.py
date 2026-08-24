#负责把外部的HTTP请求翻译成 Runtime 能懂的参数
#并把Runtime的结果翻译回JSON返回给前端
from fastapi import APIRouter
from pydantic import BaseModel, Field, StrictStr
from app.adapters.read_only_tool_stub import ReadOnlyToolStub
from app.contracts.agent import AgentRunResult, AgentState
from app.services.agent_runtime import AgentRuntime

#定义 HTTP 请求体的结构，外部调用方必须按照这个格式传数据
class AgentRunRequest(BaseModel):
    state: AgentState = AgentState.CONTEXT_READY
    case_id: StrictStr = ""
    evidence_refs: list[StrictStr] = Field(default_factory=list)
    correlation_id: StrictStr = ""

    class Config:
        extra = "forbid" 

#创建一个独立的路由器/接口，会被 main.py 挂载到总控制台
router = APIRouter()

#定义这是一个 POST 接口
@router.post(
    "/api/v1/agent-runs", #URL
    response_model=AgentRunResult, #这个接口返回的数据必须符合 AgentRunResult 契约
    response_model_exclude_none=True,
)

def run_agent(request: AgentRunRequest) -> AgentRunResult:
    runtime = AgentRuntime(tool_gateway=ReadOnlyToolStub())
    return runtime.run(
        state=request.state,
        case_id=request.case_id,
        evidence_refs=list(request.evidence_refs),
        correlation_id=request.correlation_id,
    )
