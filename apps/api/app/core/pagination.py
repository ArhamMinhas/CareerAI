import base64
import json
import uuid
from datetime import datetime


class InvalidCursorError(Exception):
    pass


def encode_cursor(*, sort_value: datetime, id: uuid.UUID) -> str:
    """Opaque keyset cursor (docs/API.md §1: `?limit=20&cursor=<opaque>` -> `next_cursor`), for
    genuinely unbounded lists — `jobs` is the first. Encodes `(sort_value, id)` rather than an
    offset so pagination stays stable while new rows are inserted between reads, at the cost of
    only supporting one fixed sort order per resource (here: newest first, id as a tiebreaker
    for rows with an identical timestamp)."""

    payload = json.dumps([sort_value.isoformat(), str(id)])
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw_sort_value, raw_id = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return datetime.fromisoformat(raw_sort_value), uuid.UUID(raw_id)
    except Exception as exc:
        raise InvalidCursorError("Invalid pagination cursor.") from exc
