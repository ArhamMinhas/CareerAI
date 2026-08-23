import base64
import json
import uuid
from datetime import UTC, datetime

import pytest

from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor


def test_cursor_round_trips() -> None:
    sort_value = datetime(2026, 1, 1, tzinfo=UTC)
    job_id = uuid.uuid4()

    cursor = encode_cursor(sort_value=sort_value, id=job_id)
    decoded_sort_value, decoded_id = decode_cursor(cursor)

    assert decoded_sort_value == sort_value
    assert decoded_id == job_id


def test_decode_rejects_garbage_cursor() -> None:
    with pytest.raises(InvalidCursorError):
        decode_cursor("not-a-real-cursor")


def test_decode_rejects_well_formed_but_wrong_shape_cursor() -> None:
    payload = json.dumps(["not-a-datetime", "not-a-uuid"])
    cursor = base64.urlsafe_b64encode(payload.encode()).decode()

    with pytest.raises(InvalidCursorError):
        decode_cursor(cursor)
