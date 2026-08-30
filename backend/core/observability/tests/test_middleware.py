import json
import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from core.observability.middleware import RequestLoggingMiddleware, _resolve_app


factory = RequestFactory()


def _middleware(get_response=None):
    if get_response is None:
        get_response = lambda req: HttpResponse(status=200)
    return RequestLoggingMiddleware(get_response)


# ---------------------------------------------------------------------------
# _resolve_app — URL-to-app-name mapping
# ---------------------------------------------------------------------------

class TestResolveApp:
    # Platform / core endpoints
    def test_auth_email_otp(self):
        assert _resolve_app("/api/v1/auth/otp/email/request/") == "core"

    def test_auth_phone_otp(self):
        assert _resolve_app("/api/v1/auth/otp/phone/verify/") == "core"

    def test_auth_token_refresh(self):
        assert _resolve_app("/api/v1/auth/token/refresh/") == "core"

    def test_auth_link_identity(self):
        assert _resolve_app("/api/v1/auth/identity/link/email/request/") == "core"

    def test_me_endpoint(self):
        # Future user self-service endpoint — must be tagged as core.
        assert _resolve_app("/api/v1/me/") == "core"

    # Product app endpoints
    def test_quiz_app(self):
        assert _resolve_app("/api/v1/quiz/attempts/") == "quiz"

    def test_tutor_app(self):
        assert _resolve_app("/api/v1/tutor/sessions/") == "tutor"

    def test_notes_app(self):
        assert _resolve_app("/api/v1/notes/") == "notes"

    def test_unknown_product_app(self):
        assert _resolve_app("/api/v1/someproduct/resources/1/") == "someproduct"

    # Future API version still works
    def test_v2_prefix(self):
        assert _resolve_app("/api/v2/quiz/") == "quiz"

    # Admin
    def test_admin_root(self):
        assert _resolve_app("/admin/") == "admin"

    def test_admin_nested(self):
        assert _resolve_app("/admin/users/user/1/") == "admin"

    # Non-versioned API paths (docs live at /api/schema/, not /api/v1/schema/)
    def test_api_schema(self):
        assert _resolve_app("/api/schema/") == "platform"

    def test_api_docs(self):
        assert _resolve_app("/api/docs/") == "platform"

    def test_api_redoc(self):
        assert _resolve_app("/api/redoc/") == "platform"

    # Edge cases
    def test_root(self):
        assert _resolve_app("/") == "platform"

    def test_bare_api(self):
        assert _resolve_app("/api/") == "platform"

    def test_api_v1_no_app(self):
        assert _resolve_app("/api/v1/") == "platform"

    def test_healthcheck(self):
        assert _resolve_app("/healthcheck/") == "platform"


# ---------------------------------------------------------------------------
# RequestLoggingMiddleware
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRequestLoggingMiddleware:
    def test_adds_x_request_id_header(self):
        request = factory.get("/api/v1/auth/otp/email/request/")
        response = _middleware()(request)
        assert "X-Request-Id" in response

    def test_x_request_id_is_uuid_shaped(self):
        import uuid
        request = factory.get("/api/v1/quiz/")
        response = _middleware()(request)
        header = response["X-Request-Id"]
        # Should not raise
        uuid.UUID(header)

    def test_sets_request_request_id(self):
        captured = {}

        def get_response(req):
            captured["request_id"] = getattr(req, "request_id", None)
            return HttpResponse()

        request = factory.get("/api/v1/quiz/")
        _middleware(get_response)(request)
        assert captured["request_id"] is not None

    def test_request_id_matches_header(self):
        captured = {}

        def get_response(req):
            captured["request_id"] = req.request_id
            return HttpResponse()

        request = factory.get("/api/v1/quiz/")
        response = _middleware(get_response)(request)
        assert response["X-Request-Id"] == captured["request_id"]

    def test_logs_one_line_per_request(self, caplog):
        import logging
        request = factory.get("/api/v1/quiz/")
        with caplog.at_level(logging.INFO, logger="origin.request"):
            _middleware()(request)
        assert len(caplog.records) == 1

    def test_log_contains_correct_fields(self, caplog):
        import logging
        request = factory.post("/api/v1/quiz/attempts/")
        with caplog.at_level(logging.INFO, logger="origin.request"):
            response = _middleware()(request)
        record = caplog.records[0]
        assert record.method == "POST"
        assert record.path == "/api/v1/quiz/attempts/"
        assert record.status == 200
        assert record.app == "quiz"
        assert isinstance(record.duration_ms, int)
        assert record.duration_ms >= 0
        assert record.request_id == response["X-Request-Id"]

    def test_log_app_is_core_for_auth_path(self, caplog):
        import logging
        request = factory.post("/api/v1/auth/otp/email/request/")
        with caplog.at_level(logging.INFO, logger="origin.request"):
            _middleware()(request)
        assert caplog.records[0].app == "core"

    def test_log_user_id_is_none_for_unauthenticated(self, caplog):
        import logging
        request = factory.get("/api/v1/quiz/")
        with caplog.at_level(logging.INFO, logger="origin.request"):
            _middleware()(request)
        assert caplog.records[0].user_id is None

    def test_log_user_id_set_for_authenticated_user(self, caplog, make_user):
        import logging
        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.tokens import RefreshToken

        user = make_user(email="obs@example.com")
        refresh = RefreshToken.for_user(user)
        token = str(refresh.access_token)

        api_factory = APIRequestFactory()
        request = api_factory.get(
            "/api/v1/quiz/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        # Manually force authentication the way DRF does it, to simulate
        # what happens after AuthenticationMiddleware + JWTAuthentication.
        request.user = user

        with caplog.at_level(logging.INFO, logger="origin.request"):
            _middleware()(request)
        assert caplog.records[0].user_id == str(user.pk)

    def test_passes_through_response_status(self, caplog):
        import logging
        request = factory.delete("/api/v1/quiz/1/")
        with caplog.at_level(logging.INFO, logger="origin.request"):
            _middleware(lambda req: HttpResponse(status=204))(request)
        assert caplog.records[0].status == 204

    def test_logs_and_reraises_on_exception(self, caplog):
        import logging

        def exploding_view(req):
            raise RuntimeError("kaboom")

        request = factory.get("/api/v1/quiz/")
        with caplog.at_level(logging.ERROR, logger="origin.request"):
            with pytest.raises(RuntimeError, match="kaboom"):
                _middleware(exploding_view)(request)
        assert len(caplog.records) == 1
        assert caplog.records[0].status == 500
