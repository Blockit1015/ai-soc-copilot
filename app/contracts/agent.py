#契约层
from enum import Enum
from pydantic import BaseModel, Field, StrictInt

#AgentState有四个状态
class AgentState(str, Enum):
    CONTEXT_READY = "CONTEXT_READY"
    ENRICHING = "ENRICHING"
    ENRICHED = "ENRICHED"
    MANUAL = "MANUAL"

#停止原因的归因
class StopReason(str, Enum):
    MISSING_CONTEXT_INPUT = "MISSING_CONTEXT_INPUT"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_BUDGET_EXHAUSTED = "TOOL_BUDGET_EXHAUSTED"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"

class RunStep(BaseModel):
    state: AgentState

    class Config:
        extra = "forbid"

#运行结果的完整契约
class AgentRunResult(BaseModel):
    state: AgentState
    tool_budget_initial: StrictInt = Field(..., ge=0)
    tool_budget_remaining: StrictInt = Field(..., ge=0)
    tool_call_count: StrictInt = Field(..., ge=0)
    trace: list[RunStep]
    stop_reason: StopReason | None = None

    class Config:
        extra = "forbid"
