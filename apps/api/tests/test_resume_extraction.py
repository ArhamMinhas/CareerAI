import httpx2
from openai import APIError

from app.ai.resume_extraction import _clean_error_detail

_DUMMY_REQUEST = httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")


def _make_openai_error(body: object) -> APIError:
    return APIError(f"Error code: 429 - {body}", _DUMMY_REQUEST, body=body)


def test_clean_error_detail_extracts_message_from_body() -> None:
    body = {"error": {"message": "You have no credits remaining.", "code": "insufficient_quota"}}
    exc = _make_openai_error(body)
    assert _clean_error_detail(exc) == "You have no credits remaining."


def test_clean_error_detail_falls_back_to_str_when_no_body_message() -> None:
    exc = _make_openai_error(None)
    assert "429" in _clean_error_detail(exc)
