#定义端口层，是Agent与外部世界交互的标准，规定外部必须长什么样
from typing import Protocol

#定义超时的契约
class ToolTimeoutError(TimeoutError):
    """Raised when the read-only teaching tool does not respond in time."""

#端口，定义Agent 与外部工具交互的绝对边界
class ToolGateway(Protocol):
    """The single read-only tool boundary used by the agent runtime."""

    def query_asset_context(
        self,
        *,
        case_id: str,
        evidence_refs: list[str],
        correlation_id: str,
    ) -> object:
        """Read asset context without allowing the runtime to access a real system."""
        ...
