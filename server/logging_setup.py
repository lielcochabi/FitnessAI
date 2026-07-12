import json
import logging
import os
from contextvars import ContextVar
from datetime import datetime, timezone

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_username: ContextVar[str | None] = ContextVar("username", default=None)
_method: ContextVar[str | None] = ContextVar("method", default=None)
_path: ContextVar[str | None] = ContextVar("path", default=None)

_CONTEXT_KEYS = ("request_id", "username", "method", "path")
_STANDARD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())


def bind_request_context(request_id: str, method: str, path: str) -> None:
    _request_id.set(request_id)
    _method.set(method)
    _path.set(path)


def bind_username(username: str) -> None:
    _username.set(username)


def clear_context() -> None:
    _request_id.set(None)
    _username.set(None)
    _method.set(None)
    _path.set(None)


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        record.username = _username.get()
        record.method = _method.get()
        record.path = _path.get()
        return True


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _CONTEXT_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS or key in _CONTEXT_KEYS or key in payload:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(_JSONFormatter())
    handler.addFilter(_ContextFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # uvicorn's loggers ship with their own plain-text handlers and
    # propagate=False, so without this their lines would bypass the JSON
    # formatter and corrupt the machine-readable stream.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = []
        uv_logger.propagate = True
