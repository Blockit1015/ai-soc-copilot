from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from app.contracts.case_evidence import DependencyError
from app.services.context_preparation import (
    InvestigationNotFoundError,
    context_preparation_service,
)
##从业务服务层到HTTP接口层的转换

#创建一个独立的路由对象
#FastAPI将不同的业务模块拆分到不同的文件中，最后再统一注册到 main.py
router = APIRouter()

# 定义了POST接口路径
# FastAPI 会自动将URL中的 {investigation_id} 提取出来，作为参数传给函数
@router.post("/api/v1/investigations/{investigation_id}/context")
def prepare_investigation_context(investigation_id: str) -> JSONResponse:
  # 场景二处理：未知 ID 返回 404
    try:   #捕获业务层抛出的 InvestigationNotFoundError
        result = context_preparation_service.prepare_context(investigation_id)
    except InvestigationNotFoundError as error: #将其转换为HTTP标准的404 Not Found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
  # 场景三处理：依赖不可用返回 503
    if isinstance(result, DependencyError): # 如果业务层返回的是DependencyError，说明Stub挂了
        return JSONResponse(   # 返回 503 Service Unavailable
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=result.model_dump(),
        )
  # 场景一处理：成功返回 200
    return JSONResponse(
        status_code=status.HTTP_200_OK, # 返回 200 OK
        content=result.model_dump(), # 将包含 status='CONTEXT_READY'、case_id、evidence_refs 和 correlation_id 的冻结契约原样输出
    )
