import math
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interview_evaluation import InterviewEvaluationResult
from app.core.pagination import decode_cursor, encode_cursor
from app.models.interview import (
    Interview,
    InterviewAnswer,
    InterviewEvaluation,
    InterviewMode,
    InterviewQuestion,
    InterviewQuestionBank,
    InterviewStatus,
)
from app.models.resume import Resume, ResumeStatus
from app.models.user import User
from app.schemas.resume import ResumeExtraction
from app.services.career_paths import CareerPathNotFoundError, resolve_career_path

_QUESTIONS_PER_INTERVIEW = 5


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def _resolve_target_role_embedding(
    db: AsyncSession, target_role: str | None
) -> list[float] | None:
    """Best-effort only — `Interview.target_role` is a plain, optional string, not required to
    resolve against the curated `CareerPath` catalog (see that model's docstring for why).
    Returns `None` on any resolution failure or a nullable, not-yet-embedded `CareerPath` —
    question selection just falls back to unranked, stable ordering, same as
    `find_related_career_paths`'s existing "no embedding -> no ranking" precedent."""
    if not target_role:
        return None
    try:
        career_path = await resolve_career_path(db, target_role)
    except CareerPathNotFoundError:
        return None
    return career_path.embedding


async def select_next_question(
    db: AsyncSession, *, interview: Interview
) -> InterviewQuestionBank | None:
    """Fully deterministic — no LLM call (docs/AI_ARCHITECTURE.md §8: sequencing/selection is
    never an LLM decision). Prefers a category not yet used this session — with ~5-6 categories
    per mode and a 5-question session, category repeats are the *common* path once a session is
    past its first few questions, not a rare edge case. Ranked by cosine similarity to the
    resolved target role's `CareerPath.embedding` when available; falls back to stable
    (`created_at`, `id`) ordering when no ranking signal exists. Returns `None` only when the
    bank has zero questions for this mode at all (never happens against the real seeded data,
    but must degrade gracefully rather than crash session creation)."""
    asked_result = await db.execute(
        select(InterviewQuestion.bank_question_id, InterviewQuestion.category).where(
            InterviewQuestion.interview_id == interview.id
        )
    )
    asked_rows = asked_result.all()
    asked_bank_ids = {
        row.bank_question_id for row in asked_rows if row.bank_question_id is not None
    }
    asked_categories = {row.category for row in asked_rows}

    bank_result = await db.execute(
        select(InterviewQuestionBank).where(InterviewQuestionBank.mode == interview.mode)
    )
    bank_questions = list(bank_result.scalars().all())
    if not bank_questions:
        return None

    candidates = [q for q in bank_questions if q.id not in asked_bank_ids]
    if not candidates:
        # Bank exhausted for this mode — degrade to full repeats rather than failing the session.
        candidates = bank_questions

    fresh_category_candidates = [q for q in candidates if q.category not in asked_categories]
    pool = fresh_category_candidates or candidates

    target_embedding = await _resolve_target_role_embedding(db, interview.target_role)
    scored = (
        [
            (q, _cosine_similarity(q.embedding, target_embedding))
            for q in pool
            if q.embedding is not None
        ]
        if target_embedding is not None
        else []
    )
    if scored:
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[0][0]

    return sorted(pool, key=lambda q: (q.created_at, q.id))[0]


async def _create_question_row(
    db: AsyncSession, *, interview: Interview, order_index: int
) -> InterviewQuestion | None:
    bank_question = await select_next_question(db, interview=interview)
    if bank_question is None:
        return None
    question = InterviewQuestion(
        interview_id=interview.id,
        bank_question_id=bank_question.id,
        question_text=bank_question.question_text,
        category=bank_question.category,
        order_index=order_index,
    )
    db.add(question)
    await db.flush()
    return question


async def create_interview(
    db: AsyncSession, *, user: User, mode: InterviewMode, target_role: str | None
) -> Interview:
    """Creates the session + its first question. No LLM call — pure retrieval — so this never
    needs Idempotency-Key/rate-limiting, matching `applications.py`'s plain resource-creation-POST
    precedent. Does not commit — caller owns the transaction."""
    interview = Interview(user_id=user.id, mode=mode, target_role=target_role)
    db.add(interview)
    await db.flush()
    await _create_question_row(db, interview=interview, order_index=0)
    return interview


async def _complete_interview(db: AsyncSession, *, interview: Interview) -> None:
    result = await db.execute(
        select(
            InterviewEvaluation.correctness_score,
            InterviewEvaluation.depth_score,
            InterviewEvaluation.communication_score,
        )
        .select_from(InterviewQuestion)
        .join(InterviewAnswer, InterviewAnswer.question_id == InterviewQuestion.id)
        .join(InterviewEvaluation, InterviewEvaluation.answer_id == InterviewAnswer.id)
        .where(InterviewQuestion.interview_id == interview.id)
    )
    rows = result.all()
    if rows:
        per_question_means = [
            (float(row.correctness_score) + float(row.depth_score) + float(row.communication_score))
            / 3
            for row in rows
        ]
        interview.overall_score = round(sum(per_question_means) / len(per_question_means), 2)
    interview.status = InterviewStatus.COMPLETED
    await db.flush()


async def advance_or_complete(
    db: AsyncSession, *, interview: Interview
) -> InterviewQuestion | None:
    """Called after an answer is recorded. Returns the newly-created next question, or `None` if
    the session just completed (in which case `interview.status`/`overall_score` are already
    updated on the passed-in object)."""
    answered_count_result = await db.execute(
        select(func.count(InterviewAnswer.id))
        .select_from(InterviewQuestion)
        .join(InterviewAnswer, InterviewAnswer.question_id == InterviewQuestion.id)
        .where(InterviewQuestion.interview_id == interview.id)
    )
    answered_count = answered_count_result.scalar_one()

    if answered_count >= _QUESTIONS_PER_INTERVIEW:
        await _complete_interview(db, interview=interview)
        return None

    return await _create_question_row(db, interview=interview, order_index=answered_count)


class AnswerAlreadySubmittedError(Exception):
    """Raised when a question already has an answer — the route maps this to 409. Concurrency
    guard against two racing submissions for the same question (duplicate tabs, not just a
    client retry sharing an Idempotency-Key), same shape as `resumes.py`'s `PROCESSING`-status
    409 guard."""


async def has_answer(db: AsyncSession, *, question_id: uuid.UUID) -> bool:
    """Cheap pre-check the route calls *before* running the expensive LLM evaluation, so a
    losing racer doesn't pay for a call whose result will just be discarded. `record_answer`
    still re-checks and catches the DB-level conflict as the final, authoritative guard."""
    result = await db.execute(
        select(InterviewAnswer.id).where(InterviewAnswer.question_id == question_id)
    )
    return result.scalar_one_or_none() is not None


async def record_answer(
    db: AsyncSession,
    *,
    question: InterviewQuestion,
    answer_text: str,
    response_time_seconds: int,
    evaluation: InterviewEvaluationResult,
) -> InterviewAnswer:
    try:
        async with db.begin_nested():
            existing = await db.execute(
                select(InterviewAnswer.id).where(InterviewAnswer.question_id == question.id)
            )
            if existing.scalar_one_or_none() is not None:
                raise AnswerAlreadySubmittedError(f"Question {question.id} already has an answer.")

            answer = InterviewAnswer(
                question_id=question.id,
                answer_text=answer_text,
                response_time_seconds=response_time_seconds,
            )
            db.add(answer)
            await db.flush()
            db.add(
                InterviewEvaluation(
                    answer_id=answer.id,
                    correctness_score=evaluation.correctness_score,
                    depth_score=evaluation.depth_score,
                    communication_score=evaluation.communication_score,
                    feedback=evaluation.feedback,
                )
            )
            await db.flush()
    except IntegrityError as exc:
        raise AnswerAlreadySubmittedError(f"Question {question.id} already has an answer.") from exc
    return answer


async def get_owned_interview(
    db: AsyncSession, *, interview_id: uuid.UUID, user_id: uuid.UUID
) -> Interview | None:
    result = await db.execute(
        select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id,
            Interview.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_question_in_interview(
    db: AsyncSession, *, question_id: uuid.UUID, interview_id: uuid.UUID
) -> InterviewQuestion | None:
    result = await db.execute(
        select(InterviewQuestion).where(
            InterviewQuestion.id == question_id, InterviewQuestion.interview_id == interview_id
        )
    )
    return result.scalar_one_or_none()


QuestionWithDetails = tuple[InterviewQuestion, InterviewAnswer | None, InterviewEvaluation | None]


async def get_questions_with_details(
    db: AsyncSession, *, interview_id: uuid.UUID
) -> list[QuestionWithDetails]:
    result = await db.execute(
        select(InterviewQuestion, InterviewAnswer, InterviewEvaluation)
        .outerjoin(InterviewAnswer, InterviewAnswer.question_id == InterviewQuestion.id)
        .outerjoin(InterviewEvaluation, InterviewEvaluation.answer_id == InterviewAnswer.id)
        .where(InterviewQuestion.interview_id == interview_id)
        .order_by(InterviewQuestion.order_index)
    )
    return [(row[0], row[1], row[2]) for row in result.all()]


async def delete_interview(
    db: AsyncSession, *, user_id: uuid.UUID, interview_id: uuid.UUID
) -> bool:
    interview = await get_owned_interview(db, interview_id=interview_id, user_id=user_id)
    if interview is None:
        return False
    interview.soft_delete()
    await db.flush()
    return True


async def list_interviews(
    db: AsyncSession, *, user_id: uuid.UUID, limit: int, cursor: str | None
) -> tuple[list[Interview], str | None]:
    """Cursor-paginated (docs/API.md §1) — deliberately not left unpaginated like `resumes.py`'s
    list: a user can start unboundedly many practice sessions, including abandoned/dangling
    `in_progress` ones from a flaky client or a duplicate tab, unlike a resume upload list."""
    stmt = select(Interview).where(Interview.user_id == user_id, Interview.deleted_at.is_(None))
    if cursor:
        created_at, interview_id, _rank = decode_cursor(cursor)
        stmt = stmt.where(tuple_(Interview.created_at, Interview.id) < (created_at, interview_id))
    stmt = stmt.order_by(Interview.created_at.desc(), Interview.id.desc()).limit(limit + 1)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    if len(rows) > limit:
        page = rows[:limit]
        last = page[-1]
        return page, encode_cursor(sort_value=last.created_at, id=last.id)
    return rows, None


@dataclass(frozen=True)
class InterviewAnalyticsData:
    total_completed: int
    average_overall_score: float | None
    average_correctness_score: float | None
    average_depth_score: float | None
    average_communication_score: float | None
    recent: list[Interview]


async def get_analytics(db: AsyncSession, *, user_id: uuid.UUID) -> InterviewAnalyticsData:
    """Real SQL aggregates over the current user's own completed sessions only — never another
    user's data, never a fabricated placeholder."""
    completed_result = await db.execute(
        select(func.count(Interview.id), func.avg(Interview.overall_score)).where(
            Interview.user_id == user_id,
            Interview.status == InterviewStatus.COMPLETED,
            Interview.deleted_at.is_(None),
        )
    )
    total_completed, average_overall = completed_result.one()

    dims_result = await db.execute(
        select(
            func.avg(InterviewEvaluation.correctness_score),
            func.avg(InterviewEvaluation.depth_score),
            func.avg(InterviewEvaluation.communication_score),
        )
        .select_from(InterviewEvaluation)
        .join(InterviewAnswer, InterviewAnswer.id == InterviewEvaluation.answer_id)
        .join(InterviewQuestion, InterviewQuestion.id == InterviewAnswer.question_id)
        .join(Interview, Interview.id == InterviewQuestion.interview_id)
        .where(
            Interview.user_id == user_id,
            Interview.status == InterviewStatus.COMPLETED,
            Interview.deleted_at.is_(None),
        )
    )
    avg_correctness, avg_depth, avg_communication = dims_result.one()

    recent_result = await db.execute(
        select(Interview)
        .where(
            Interview.user_id == user_id,
            Interview.status == InterviewStatus.COMPLETED,
            Interview.deleted_at.is_(None),
        )
        .order_by(Interview.updated_at.desc())
        .limit(5)
    )
    recent = list(recent_result.scalars().all())

    return InterviewAnalyticsData(
        total_completed=total_completed,
        average_overall_score=float(average_overall) if average_overall is not None else None,
        average_correctness_score=float(avg_correctness) if avg_correctness is not None else None,
        average_depth_score=float(avg_depth) if avg_depth is not None else None,
        average_communication_score=(
            float(avg_communication) if avg_communication is not None else None
        ),
        recent=recent,
    )


async def build_resume_context(db: AsyncSession, *, user_id: uuid.UUID) -> str | None:
    """A short, pre-formatted grounding string for `app/ai/interview_evaluation.py` — never the
    raw `structured_data` blob. `None` when the user has no analyzed resume (most users, at
    least initially) — evaluation must work well without this, not depend on it."""
    result = await db.execute(
        select(Resume)
        .where(
            Resume.user_id == user_id,
            Resume.status == ResumeStatus.COMPLETED,
            Resume.deleted_at.is_(None),
        )
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    resume = result.scalar_one_or_none()
    if resume is None or resume.structured_data is None:
        return None

    try:
        extraction = ResumeExtraction.model_validate(resume.structured_data)
    except Exception:
        return None

    parts: list[str] = []
    if extraction.skills:
        parts.append(f"Skills: {', '.join(extraction.skills[:10])}")
    if extraction.experience:
        most_recent = extraction.experience[0]
        role = " at ".join(part for part in (most_recent.title, most_recent.company) if part)
        if role:
            parts.append(f"Most recent role: {role}")
    return ". ".join(parts) if parts else None
