import json
import logging

_EXTRA_FIELDS = (
    "request_id",
    "app",
    "method",
    "path",
    "status",
    "duration_ms",
    "user_id",
)


class JSONFormatter(logging.Formatter):
    """
    Emit one JSON object per log line.

    Standard fields (time, level, logger, message) are always present.
    Request-scoped fields (request_id, app, method, path, status,
    duration_ms, user_id) are included when available so every log line
    for a given request can be correlated and filtered by app in Railway,
    Sentry, or any structured-log tool.
    """

    def format(self, record):
        data = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                data[field] = value
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data)
