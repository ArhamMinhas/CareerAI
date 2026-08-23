import base64
import json
import uuid
from datetime import datetime


class InvalidCursorError(Exception):
    pass


def encode_cursor(*, sort_value: datetime, id: uuid.UUID, rank: int | None = None) -> str:
    """Opaque keyset cursor (docs/API.md §1: `?limit=20&cursor=<opaque>` -> `next_cursor`), for
    genuinely unbounded lists — `jobs` is the first. Encodes `(sort_value, id)` rather than an
    offset so pagination stays stable while new rows are inserted between reads, at the cost of
    only supporting one fixed sort order per resource (here: newest first, id as a tiebreaker
    for rows with an identical timestamp).

    `rank` is an optional leading sort key ahead of `sort_value` — used by keyword search
    (app/services/jobs.py) to keep company-name/title matches ordered ahead of description-only
    matches across pages, not just within a single page."""

    payload = json.dumps([sort_value.isoformat(), str(id), rank])
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID, int | None]:
    try:
        decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        raw_sort_value, raw_id, raw_rank = decoded
        return datetime.fromisoformat(raw_sort_value), uuid.UUID(raw_id), raw_rank
    except Exception as exc:
        raise InvalidCursorError("Invalid pagination cursor.") from exc
