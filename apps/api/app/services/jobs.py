import uuid

from sqlalchemy import Select, case, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.pagination import decode_cursor, encode_cursor
from app.models.company import Company
from app.models.job import Job
from app.services.embeddings import embed_text

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50
_SEMANTIC_FALLBACK_LIMIT = 20


async def list_jobs(
    db: AsyncSession, *, q: str | None, limit: int, cursor: str | None
) -> tuple[list[Job], str | None]:
    """`GET /api/v1/jobs` (docs/API.md §1's cursor-pagination convention, first real use of it
    — the curated catalogs (careers, skills) are small enough to return unpaginated, but job
    postings are the genuinely unbounded list that convention was written for).

    `q` is a hybrid keyword-then-semantic search: an `ILIKE` match against title/description/
    company name first (cheap, precise for exact terms), falling back to nearest-neighbor
    search over `Job.embedding` only when the keyword pass finds nothing — catching queries
    phrased differently than any posting's own words (e.g. "ML engineer" vs. a posting titled
    "Machine Learning Engineer"). The semantic fallback returns an unpaginated single page
    (`_SEMANTIC_FALLBACK_LIMIT` results, no `next_cursor`): it's a bounded top-K similarity
    ranking, not a stable keyset order, so it doesn't compose with cursor pagination the way the
    keyword/default listing does.

    Keyword matches are ranked company-name-first, then title, then description-only (see
    `_match_rank`) — without this, a query like "google" surfaces any job that merely *mentions*
    Google in its description (e.g. "familiar with Google Cloud") ahead of postings actually at
    Google, which is backwards for what a company-name search is for.
    """
    limit = max(1, min(limit, MAX_PAGE_SIZE))

    if q:
        return await _list_jobs_by_keyword(db, q=q, limit=limit, cursor=cursor)

    stmt = select(Job).where(Job.is_active.is_(True))
    stmt = _apply_cursor(stmt, cursor)
    stmt = stmt.order_by(Job.posted_at.desc(), Job.id.desc()).limit(limit + 1)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    return _paginate(rows, limit)


def _match_rank(q: str) -> ColumnElement[int]:
    """0 = company name match, 1 = title match, 2 = description-only match — the ORDER BY key
    that keeps "google" surfacing jobs *at* Google ahead of jobs that merely mention it."""
    return case(
        (Company.name.ilike(f"%{q}%"), 0),
        (Job.title.ilike(f"%{q}%"), 1),
        else_=2,
    )


async def _list_jobs_by_keyword(
    db: AsyncSession, *, q: str, limit: int, cursor: str | None
) -> tuple[list[Job], str | None]:
    rank = _match_rank(q).label("match_rank")
    stmt = (
        select(Job, rank)
        .join(Company)
        .where(
            Job.is_active.is_(True),
            or_(
                Job.title.ilike(f"%{q}%"),
                Job.description.ilike(f"%{q}%"),
                Company.name.ilike(f"%{q}%"),
            ),
        )
    )
    if cursor:
        cursor_posted_at, cursor_job_id, cursor_rank = decode_cursor(cursor)
        if cursor_rank is None:
            cursor_rank = 2
        stmt = stmt.where(
            tuple_(rank, Job.posted_at, Job.id) < (cursor_rank, cursor_posted_at, cursor_job_id)
        )
    stmt = stmt.order_by(rank, Job.posted_at.desc(), Job.id.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    rows = result.all()
    if not rows:
        query_vector = await embed_text(q)
        semantic_result = await db.execute(
            select(Job)
            .where(Job.is_active.is_(True), Job.embedding.is_not(None))
            .order_by(Job.embedding.cosine_distance(query_vector))
            .limit(_SEMANTIC_FALLBACK_LIMIT)
        )
        return list(semantic_result.scalars().all()), None

    page_rows = rows[:limit]
    jobs = [row[0] for row in page_rows]
    next_cursor = None
    if len(rows) > limit:
        last_job, last_rank = page_rows[-1]
        next_cursor = encode_cursor(sort_value=last_job.posted_at, id=last_job.id, rank=last_rank)
    return jobs, next_cursor


def _apply_cursor(stmt: Select[tuple[Job]], cursor: str | None) -> Select[tuple[Job]]:
    if not cursor:
        return stmt
    posted_at, job_id, _rank = decode_cursor(cursor)
    return stmt.where(tuple_(Job.posted_at, Job.id) < (posted_at, job_id))


def _paginate(rows: list[Job], limit: int) -> tuple[list[Job], str | None]:
    if len(rows) > limit:
        page = rows[:limit]
        last = page[-1]
        return page, encode_cursor(sort_value=last.posted_at, id=last.id)
    return rows, None


async def get_active_job(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id, Job.is_active.is_(True)))
    return result.scalar_one_or_none()


async def list_active_jobs_for_company(
    db: AsyncSession, company_id: uuid.UUID, *, limit: int, cursor: str | None
) -> tuple[list[Job], str | None]:
    stmt = select(Job).where(Job.company_id == company_id, Job.is_active.is_(True))
    stmt = _apply_cursor(stmt, cursor)
    stmt = stmt.order_by(Job.posted_at.desc(), Job.id.desc()).limit(limit + 1)
    result = await db.execute(stmt)
    return _paginate(list(result.scalars().all()), limit)
