#告警接收部门（接上路由（Router））

from uuid import uuid4
from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse
from app.contracts.alert import StandardAlert
from app.services.idempotency import (
    IDEMPOTENCY_CONFLICT_MESSAGE,
    IdempotencyConflictError,
    idempotency_store,
)

#定义接口：在系统里开了一个“收件窗口”，地址叫 /api/v1/investigations，只接收POST请求（也就是别人来提交数据）
#当有人往这个地址发数据时，就会触发下面的receive_investigation函数。

router = APIRouter()
@router.post("/api/v1/investigations")

# 接收参数：当别人发来请求时，我们要求他必须带三样东西：
# 一是alert (JSON数据)：必须长得很像我们昨天定义的 StandardAlert（在app/contracts/alert.py中）。如果长得不像，系统会自动拦截并返回422错误。
# 二是idempotency_key (请求头)：相当于“快递单号”，用来防止重复提交。
# 三是correlation_id (请求头)：相当于“追踪手环”，用来串联整个请求链路。

def receive_investigation(                      
    alert: StandardAlert,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1),
    correlation_id: str | None = Header(
        default=None,
        alias="X-Correlation-ID",
        min_length=1,
    ),
) -> JSONResponse:
    def create_first_response() -> dict[str, object]:    ###这就是调查任务返回的数据格式
        return {
            "investigation_id": f"inv_{uuid4().hex}",  #调查任务ID，系统自己生成的
            "alert_id": alert.alert_id,   #告警本身的 ID
            "status": "received",    
            "correlation_id": correlation_id or f"corr_{uuid4().hex}",    #追踪标识，系统自己生成的
            "duplicate": False,  #固定值，表示不是重复请求
        }
    
#防重放检查：系统会拿着idempotency_key去记事本里查。
#如果这个告警没查过：就执行 create_first_response 生成一条新记录，存进记事本，并返回 201（创建成功）。
#如果查过了，且内容一样：直接返回之前存的结果，并标记为 200（重复请求）。
#如果查过了，但内容不一样：就会触发下面的 except，返回 409（冲突）。

#最终保存形式：idempotency_key➕指纹字符串payload_fingerprint➕上面的response的格式
    try:
        result = idempotency_store.get_or_create(
            idempotency_key=idempotency_key,   #快递单号
            payload=alert,          #payload_fingerprint
            create_response=create_first_response,  #和上面的调查任务格式
        )
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IDEMPOTENCY_CONFLICT",
                "message": IDEMPOTENCY_CONFLICT_MESSAGE,
            },
        ) from error

#返回结果：把记事本返回的结果包装成JSON格式，根据是不是重复请求，贴上200或201的标签，然后返回给调用方。（409和422都是有问题的，压根不会被保存）

    response = result.response
    response["duplicate"] = result.duplicate
    response_status = status.HTTP_200_OK if result.duplicate else status.HTTP_201_CREATED
    return JSONResponse(status_code=response_status, content=response)

