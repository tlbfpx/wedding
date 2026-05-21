from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.log import OperationLog
import json


WRITE_METHODS = {"POST", "PUT", "DELETE"}
MODULE_MAP = {
    "customers": "customer",
    "customer-pool": "customer",
    "events": "event",
    "venues": "venue",
    "staff-schedule": "event",
    "orders": "order",
    "approvals": "approval",
    "suppliers": "supplier",
    "users": "system",
    "roles": "system",
    "operation-logs": "system",
}


def get_module_from_path(path: str) -> str:
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "api" and parts[1] == "v1":
        resource = parts[2] if len(parts) > 2 else ""
        return MODULE_MAP.get(resource, resource)
    return "unknown"


def get_action_from_method(method: str) -> str:
    return {"POST": "create", "PUT": "update", "DELETE": "delete"}.get(method, "unknown")


async def log_operation(
    db: AsyncSession,
    user_id: int,
    request: Request,
    detail: dict | None = None,
):
    if request.method not in WRITE_METHODS:
        return
    log = OperationLog(
        user_id=user_id,
        module=get_module_from_path(request.url.path),
        action=get_action_from_method(request.method),
        target=request.url.path,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        ip=request.client.host if request.client else None,
    )
    db.add(log)
    await db.commit()
