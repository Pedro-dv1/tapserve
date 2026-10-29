"""Persist critical operation results under the resource's transaction lock."""

import hashlib
import json

from rest_framework.exceptions import APIException

from apps.identity.models import IdempotencyRecord


class Conflict(APIException):
    status_code = 409
    default_detail = "O registro mudou. Atualize e tente novamente."
    default_code = "conflict"


def request_digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def replay(actor: str, action: str, resource: str, key, data: dict):
    record = IdempotencyRecord.objects.filter(
        actor=actor, action=action, resource=resource, key=key
    ).first()
    if record is not None and record.request_digest != request_digest(data):
        raise Conflict()
    return record


def remember(
    unit, actor: str, action: str, resource: str, key, data: dict, response: dict, status: int
):
    return IdempotencyRecord.objects.create(
        unit=unit,
        actor=actor,
        action=action,
        resource=resource,
        key=key,
        request_digest=request_digest(data),
        response=response,
        status=status,
    )
