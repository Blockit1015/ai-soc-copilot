import copy
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum
from typing import Any

from pydantic import BaseModel


IDEMPOTENCY_CONFLICT_MESSAGE = (
    "Idempotency-Key was already used with a different payload"
)


class IdempotencyConflictError(Exception):
    def __init__(self) -> None:
        super().__init__(IDEMPOTENCY_CONFLICT_MESSAGE)


@dataclass(frozen=True)
class IdempotencyResult:
    response: dict[str, Any]
    duplicate: bool


@dataclass(frozen=True)
class _IdempotencyRecord:
    payload_fingerprint: str
    response: dict[str, Any]


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


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[str, _IdempotencyRecord] = {}

    def get_or_create(
        self,
        idempotency_key: str,
        payload: Mapping[str, Any] | BaseModel,
        create_response: Callable[[], Mapping[str, Any]],
    ) -> IdempotencyResult:
        payload_fingerprint = fingerprint_payload(payload)
        record = self._records.get(idempotency_key)

        if record is None:
            first_response = dict(create_response())
            self._records[idempotency_key] = _IdempotencyRecord(
                payload_fingerprint=payload_fingerprint,
                response=copy.deepcopy(first_response),
            )
            return IdempotencyResult(
                response=copy.deepcopy(first_response),
                duplicate=False,
            )

        if record.payload_fingerprint == payload_fingerprint:
            return IdempotencyResult(
                response=copy.deepcopy(record.response),
                duplicate=True,
            )

        raise IdempotencyConflictError()

    def clear(self) -> None:
        self._records.clear()


idempotency_store = InMemoryIdempotencyStore()
