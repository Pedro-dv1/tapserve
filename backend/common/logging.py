"""Structured diagnostics without request paths, bodies, cookies or exception data."""

import json
import logging
from datetime import UTC, datetime


class SuppressRequestDetails(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {"level": record.levelname, "logger": record.name, "event": record.getMessage()}
        entry["timestamp"] = datetime.fromtimestamp(record.created, UTC).isoformat()
        for key in (
            "request_id",
            "status",
            "method",
            "error_type",
            "endpoint",
            "close_code",
            "environment",
        ):
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        # Do not format exception arguments: DB/HTTP errors may contain credentials.
        return json.dumps(entry, ensure_ascii=False)
