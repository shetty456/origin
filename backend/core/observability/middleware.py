import logging
import time
import uuid

logger = logging.getLogger("origin.request")

# URL segments that belong to the platform, not a product app.
_CORE_SEGMENTS = {"auth", "token", "schema", "docs", "redoc"}


def _resolve_app(path: str) -> str:
    """
    Derive the app name from the request path.

    /api/v1/{app}/...  →  app name  (or "core" for platform segments)
    /admin/...         →  "admin"
    anything else      →  "platform"
    """
    parts = path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "api" and parts[1].startswith("v"):
        segment = parts[2]
        return "core" if segment in _CORE_SEGMENTS else segment
    if parts[0] == "admin":
        return "admin"
    return "platform"


class RequestLoggingMiddleware:
    """
    Attach a UUID request ID to every request and emit one structured log
    line per response.

    Every log line includes the app name derived from the URL, so logs from
    quiz, tutor, and any future product are independently filterable without
    any per-product configuration.

    The request ID is also returned in the X-Request-Id response header so
    client errors can be correlated with server logs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())
        request.request_id = request_id
        start = time.monotonic()

        try:
            response = self.get_response(request)
        except Exception:
            duration_ms = round((time.monotonic() - start) * 1000)
            logger.exception(
                "Unhandled exception",
                extra=self._fields(request, request_id, 500, duration_ms),
            )
            raise

        duration_ms = round((time.monotonic() - start) * 1000)
        logger.info(
            "",
            extra=self._fields(request, request_id, response.status_code, duration_ms),
        )
        response["X-Request-Id"] = request_id
        return response

    @staticmethod
    def _fields(request, request_id, status, duration_ms):
        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = str(request.user.pk)
        return {
            "request_id": request_id,
            "app": _resolve_app(request.path),
            "method": request.method,
            "path": request.path,
            "status": status,
            "duration_ms": duration_ms,
            "user_id": user_id,
        }
