import uuid

from sqlalchemy import Select, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

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
    """
    limit = max(1, min(limit, MAX_PAGE_SIZE))

    if q:
        keyword_stmt = (
            select(Job)
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
        keyword_stmt = _apply_cursor(keyword_stmt, cursor)
        keyword_stmt = keyword_stmt.order_by(Job.posted_at.desc(), Job.id.desc()).limit(limit + 1)
        result = await db.execute(keyword_stmt)
        rows = list(result.scalars().all())
        if rows:
            return _paginate(rows, limit)

        query_vector = await embed_text(q)
        semantic_result = await db.execute(
            select(Job)
            .where(Job.is_active.is_(True), Job.embedding.is_not(None))
            .order_by(Job.embedding.cosine_distance(query_vector))
            .limit(_SEMANTIC_FALLBACK_LIMIT)
        )
        return list(semantic_result.scalars().all()), None

    stmt = select(Job).where(Job.is_active.is_(True))
    stmt = _apply_cursor(stmt, cursor)
    stmt = stmt.order_by(Job.posted_at.desc(), Job.id.desc()).limit(limit + 1)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    return _paginate(rows, limit)


def _apply_cursor(stmt: Select[tuple[Job]], cursor: str | None) -> Select[tuple[Job]]:
    if not cursor:
        return stmt
    posted_at, job_id = decode_cursor(cursor)
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
