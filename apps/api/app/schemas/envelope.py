from fastapi import Request
from pydantic import BaseModel


class Meta(BaseModel):
    request_id: str | None = None
    next_cursor: str | None = None


class Envelope[T](BaseModel):
    """Standard success response shape — docs/API.md §2. Every endpoint returns
    `{"data": ..., "meta": {...}}` rather than a bare object, so the frontend has one
    consistent unwrap path regardless of endpoint."""

    data: T
    meta: Meta


def meta_from_request(request: Request, *, next_cursor: str | None = None) -> Meta:
    return Meta(request_id=getattr(request.state, "request_id", None), next_cursor=next_cursor)
