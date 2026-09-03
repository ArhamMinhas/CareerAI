from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)


class RagCitation(BaseModel):
    """Page-level, not per-chunk — a `#chunk-N` deep link would require the frontend's flowing
    `body_md` render and the chunker's boundaries (app/ai/kb_ingest.py) to stay in sync, two
    independent code paths with no mechanism enforcing that. Page-level still satisfies
    docs/AI_ARCHITECTURE.md §6's citation requirement."""

    resource_slug: str
    resource_title: str


class RagQueryResponse(BaseModel):
    answer: str
    citations: list[RagCitation]
