import json
import logging
import sys
import pytest

from core.observability.formatter import JSONFormatter


def _make_record(message="hello", level=logging.INFO, logger_name="test", exc_info=None, **extra):
    record = logging.LogRecord(
        name=logger_name,
        level=level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=exc_info,
    )
    for k, v in extra.items():
        setattr(record, k, v)
    return record


class TestJSONFormatter:
    def setup_method(self):
        self.fmt = JSONFormatter()

    def test_output_is_valid_json(self):
        record = _make_record()
        output = self.fmt.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_standard_fields_present(self):
        record = _make_record(message="hello", logger_name="mylogger")
        data = json.loads(self.fmt.format(record))
        assert data["message"] == "hello"
        assert data["logger"] == "mylogger"
        assert data["level"] == "INFO"
        assert "time" in data

    def test_extra_request_fields_included(self):
        record = _make_record(
            request_id="abc-123",
            app="quiz",
            method="GET",
            path="/api/v1/quiz/",
            status=200,
            duration_ms=42,
            user_id="user-uuid",
        )
        data = json.loads(self.fmt.format(record))
        assert data["request_id"] == "abc-123"
        assert data["app"] == "quiz"
        assert data["method"] == "GET"
        assert data["path"] == "/api/v1/quiz/"
        assert data["status"] == 200
        assert data["duration_ms"] == 42
        assert data["user_id"] == "user-uuid"

    def test_missing_extra_fields_omitted(self):
        record = _make_record()
        data = json.loads(self.fmt.format(record))
        for field in ("request_id", "app", "method", "path", "status", "duration_ms", "user_id"):
            assert field not in data

    def test_unauthenticated_user_id_omitted(self):
        # user_id=None must not appear in the output (field is omitted when None)
        record = _make_record(user_id=None)
        data = json.loads(self.fmt.format(record))
        assert "user_id" not in data

    def test_exception_info_included(self):
        try:
            raise ValueError("boom")
        except ValueError:
            exc_info = sys.exc_info()
        record = _make_record(exc_info=exc_info)
        data = json.loads(self.fmt.format(record))
        assert "exc" in data
        assert "ValueError" in data["exc"]
        assert "boom" in data["exc"]

    def test_no_exception_info_no_exc_field(self):
        record = _make_record()
        data = json.loads(self.fmt.format(record))
        assert "exc" not in data

    def test_special_characters_in_message_are_escaped(self):
        record = _make_record(message='has "quotes" and \nnewlines')
        output = self.fmt.format(record)
        data = json.loads(output)
        assert data["message"] == 'has "quotes" and \nnewlines'

    def test_numeric_level_maps_to_name(self):
        record = _make_record(level=logging.WARNING)
        data = json.loads(self.fmt.format(record))
        assert data["level"] == "WARNING"
