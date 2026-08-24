#这个文件职责是在测试中模拟外部工具query_asset_context 的行为
# 提供确定、可控制的响应，不用真正调用外部系统
from copy import deepcopy
from typing import Literal
from app.ports.tool_gateway import ToolTimeoutError

#这是query_asset_context 方法的固定返回值
ASSET_CONTEXT_FIXTURE = {
    "asset_id": "asset-fixture-001", #被查询对象的唯一标识
    "context": "training asset context", #被查询对象的上下文描述信息
}

#实现 ToolGateway Port 接口的 query_asset_context 方法
class ReadOnlyToolStub:
    """Deterministic, local-only implementation of the single tool Port."""

    def __init__(self, mode: Literal["available", "timeout"] = "available") -> None:
        self._mode = mode
        self.call_count = 0 #记录自己被调用了多少次
        self.called_tool_names: list[str] = [] #记录被调用的工具名称

#query_asset_context 方法
    def query_asset_context(
        self,
        *,
        case_id: str,
        evidence_refs: list[str],
        correlation_id: str,
    ) -> object:
        del case_id, evidence_refs, correlation_id
        self.call_count += 1
        self.called_tool_names.append("query_asset_context")

        if self._mode == "timeout":
            raise ToolTimeoutError("teaching tool timed out")
        return deepcopy(ASSET_CONTEXT_FIXTURE)
