"""logger.py — In-memory operation audit log (deque, newest-first)."""
import uuid
from collections import deque
from datetime import datetime, timezone

_log: deque = deque(maxlen=200)


def record(operation: str, status: str, file_name=None, details=None) -> dict:
    entry = {"id": str(uuid.uuid4())[:8],
             "timestamp": datetime.now(timezone.utc).isoformat(),
             "operation": operation, "status": status,
             "file_name": file_name, "details": details or {}}
    _log.appendleft(entry)
    return entry


def get_all() -> list:
    return list(_log)


def clear():
    _log.clear()
