import copy
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum
from typing import Any
from pydantic import BaseModel

#用一个字典存数据

IDEMPOTENCY_CONFLICT_MESSAGE = (
    "Idempotency-Key was already used with a different payload"
)

#class定义了：冲突时抛出的错误
class IdempotencyConflictError(Exception):
    def __init__(self) -> None:
        super().__init__(IDEMPOTENCY_CONFLICT_MESSAGE)

#这个class定义了：返回给路由的结果
@dataclass(frozen=True)
class IdempotencyResult:
    response: dict[str, Any]
    duplicate: bool

#这个class定义了：字典里存的单条记录（包含指纹和响应数据）
@dataclass(frozen=True)
class _IdempotencyRecord:
    payload_fingerprint: str
    response: dict[str, Any]

#负责把复杂的Python 对象，翻译成标准的、可以用来算指纹的字符串
def _json_default(value: object) -> object:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Unsupported value in idempotency payload: {type(value)!r}")
def _payload_for_serialization(
    payload: Mapping[str, Any] | BaseModel,
) -> Mapping[str, Any]:
    if isinstance(payload, BaseModel):
        if hasattr(payload, "model_dump"):
            return payload.model_dump(mode="json")
        return payload.dict()
    return payload

#把发来的JSON数据变成一串固定的字符串（哈希值）。这样下次再来一个请求，只要算一下哈希值，就能知道内容有没有变过
def fingerprint_payload(payload: Mapping[str, Any] | BaseModel) -> str:
    normalized_payload = _payload_for_serialization(payload)
    serialized_payload = json.dumps(
        normalized_payload,
        default=_json_default,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()

#定义记事本——调查任务保存位置！！！
class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[str, _IdempotencyRecord] = {}     #_records是一个普通的字典，用来存所有的调查任务

    def get_or_create(
        self,
        idempotency_key: str,
        payload: Mapping[str, Any] | BaseModel,
        create_response: Callable[[], Mapping[str, Any]],
    ) -> IdempotencyResult:
        payload_fingerprint = fingerprint_payload(payload)  ## 1. 算指纹

      ## 2.拿Key去记事本字典里查，字典的Key是调用方传过来的idempotency_key（防重放键/快递单号）
        record = self._records.get(idempotency_key)  

      ## 3. 如果没查到（第一次来）
        if record is None:
            first_response = dict(create_response())     ## 执行创建逻辑，这是在app/api/investigations.py（告警接收接口）里定义的
            # 存进字典
            self._records[idempotency_key] = _IdempotencyRecord(
                payload_fingerprint=payload_fingerprint,
                response=copy.deepcopy(first_response),
            )
            # 返回201
            return IdempotencyResult(
                response=copy.deepcopy(first_response),
                duplicate=False,
            )

      ## 4. 如果查到了，且指纹一样（原样重放）
        if record.payload_fingerprint == payload_fingerprint:
            return IdempotencyResult(
                response=copy.deepcopy(record.response),
                duplicate=True,
            )     # 返回 200
        
      ## 5. 如果查到了，但指纹不一样（冲突）
        raise IdempotencyConflictError()      # 抛出 409 错误

    def get_by_investigation_id(
        self,
        investigation_id: str,
    ) -> dict[str, Any] | None:
        for record in self._records.values():
            if record.response.get("investigation_id") == investigation_id:
                return copy.deepcopy(record.response)
        return None

    def clear(self) -> None:
        self._records.clear()


idempotency_store = InMemoryIdempotencyStore()
