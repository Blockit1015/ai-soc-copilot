from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse

from app.contracts.alert import StandardAlert
from app.services.idempotency import (
    IDEMPOTENCY_CONFLICT_MESSAGE,
    IdempotencyConflictError,
    idempotency_store,
)


router = APIRouter()


@router.post("/api/v1/investigations")
def receive_investigation(
    alert: StandardAlert,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1),
    correlation_id: str | None = Header(
        default=None,
        alias="X-Correlation-ID",
        min_length=1,
    ),
) -> JSONResponse:
    def create_first_response() -> dict[str, object]:
        return {
            "investigation_id": f"inv_{uuid4().hex}",
            "alert_id": alert.alert_id,
            "status": "received",
            "correlation_id": correlation_id or f"corr_{uuid4().hex}",
            "duplicate": False,
        }

    try:
        result = idempotency_store.get_or_create(
            idempotency_key=idempotency_key,
            payload=alert,
            create_response=create_first_response,
        )
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IDEMPOTENCY_CONFLICT",
                "message": IDEMPOTENCY_CONFLICT_MESSAGE,
            },
        ) from error

    response = result.response
    response["duplicate"] = result.duplicate
    response_status = status.HTTP_200_OK if result.duplicate else status.HTTP_201_CREATED
    return JSONResponse(status_code=response_status, content=response)
