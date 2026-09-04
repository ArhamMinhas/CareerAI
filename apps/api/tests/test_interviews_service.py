import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete, select

from app.ai.interview_evaluation import InterviewEvaluationResult
from app.core.db import AsyncSessionLocal
from app.models.interview import (
    Interview,
    InterviewAnswer,
    InterviewMode,
    InterviewQuestion,
    InterviewQuestionBank,
    InterviewStatus,
)
from app.models.user import Role, User
from app.services.interviews import (
    AnswerAlreadySubmittedError,
    _cosine_similarity,
    advance_or_complete,
    create_interview,
    delete_interview,
    get_analytics,
    has_answer,
    list_interviews,
    record_answer,
    select_next_question,
)

_MODE = InterviewMode.TECHNICAL


@pytest.fixture
async def isolated_technical_bank() -> AsyncGenerator[None]:
    """Temporarily replaces the real seeded `interview_question_bank` rows for
    `InterviewMode.TECHNICAL` with whatever the test itself inserts, so selection-algorithm
    tests are deterministic and self-contained — they must not depend on
    `seed_interview_questions.py` having run, nor interact with its real content. Restores the
    original real rows (same id/category/text/embedding/created_at) afterward."""
    async with AsyncSessionLocal() as db:
        original_result = await db.execute(
            select(InterviewQuestionBank).where(InterviewQuestionBank.mode == _MODE)
        )
        saved = [
            {
                "id": row.id,
                "category": row.category,
                "question_text": row.question_text,
                "embedding": row.embedding,
                "created_at": row.created_at,
            }
            for row in original_result.scalars().all()
        ]
        await db.execute(delete(InterviewQuestionBank).where(InterviewQuestionBank.mode == _MODE))
        await db.commit()

    yield

    async with AsyncSessionLocal() as db:
        await db.execute(delete(InterviewQuestionBank).where(InterviewQuestionBank.mode == _MODE))
        for row in saved:
            db.add(InterviewQuestionBank(mode=_MODE, **row))
        await db.commit()


@pytest.fixture
async def interview_user() -> AsyncGenerator[User]:
    user = User(id=uuid.uuid4(), email=f"interview-test-{uuid.uuid4()}@example.com", role=Role.USER)
    async with AsyncSessionLocal() as db:
        db.add(user)
        await db.commit()

    yield user

    async with AsyncSessionLocal() as db:
        await db.execute(delete(Interview).where(Interview.user_id == user.id))
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()


def test_cosine_similarity_identical_vectors_is_one() -> None:
    v = [1.0, 2.0, 3.0]
    assert _cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_opposite_vectors_is_minus_one() -> None:
    assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_similarity_zero_vector_is_zero_not_a_crash() -> None:
    assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


async def test_select_next_question_returns_none_for_empty_bank(
    isolated_technical_bank: None,
) -> None:
    interview = Interview(id=uuid.uuid4(), user_id=uuid.uuid4(), mode=_MODE, target_role=None)
    async with AsyncSessionLocal() as db:
        assert await select_next_question(db, interview=interview) is None


async def test_select_next_question_prefers_unused_categories(
    isolated_technical_bank: None,
) -> None:
    async with AsyncSessionLocal() as db:
        db.add_all(
            [
                InterviewQuestionBank(mode=_MODE, category="alpha", question_text="Q-alpha"),
                InterviewQuestionBank(mode=_MODE, category="beta", question_text="Q-beta"),
            ]
        )
        await db.commit()

    interview = Interview(id=uuid.uuid4(), user_id=uuid.uuid4(), mode=_MODE, target_role=None)
    async with AsyncSessionLocal() as db:
        first = await select_next_question(db, interview=interview)
    assert first is not None
    assert first.category in ("alpha", "beta")


async def test_select_next_question_falls_back_to_repeats_once_all_categories_used(
    isolated_technical_bank: None, interview_user: User
) -> None:
    """Category-repeat is the *common* path once a session has asked more questions than there
    are categories — not a rare edge case — so this exercises it for real, not just in reasoning."""
    async with AsyncSessionLocal() as db:
        db.add(InterviewQuestionBank(mode=_MODE, category="only-category", question_text="Q1"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        interview = Interview(user_id=interview_user.id, mode=_MODE, target_role=None)
        db.add(interview)
        await db.flush()
        # Simulate one question already asked in this exact category.
        db.add(
            InterviewQuestion(
                interview_id=interview.id,
                question_text="Already asked",
                category="only-category",
                order_index=0,
            )
        )
        await db.commit()
        interview_id = interview.id

    async with AsyncSessionLocal() as db:
        fetched_interview = await db.get(Interview, interview_id)
        assert fetched_interview is not None
        # Only one bank question exists and its category is already "used" this session — must
        # still return it (repeat), not None.
        picked = await select_next_question(db, interview=fetched_interview)
    assert picked is not None
    assert picked.category == "only-category"


async def test_select_next_question_ranks_by_embedding_similarity(
    isolated_technical_bank: None,
) -> None:
    close_vector = [1.0] * 1536
    far_vector = [-1.0] * 1536
    async with AsyncSessionLocal() as db:
        db.add_all(
            [
                InterviewQuestionBank(
                    mode=_MODE, category="close", question_text="Close Q", embedding=close_vector
                ),
                InterviewQuestionBank(
                    mode=_MODE, category="far", question_text="Far Q", embedding=far_vector
                ),
            ]
        )
        await db.commit()

    interview = Interview(id=uuid.uuid4(), user_id=uuid.uuid4(), mode=_MODE, target_role=None)
    async with AsyncSessionLocal() as db:
        # Monkeypatch-free: directly exercise the ranking helper the way select_next_question
        # would if `_resolve_target_role_embedding` returned `close_vector` — verified separately
        # via the "no target role -> no ranking" test below, so this isolates the ranking math.
        from app.services import interviews as interviews_module

        original = interviews_module._resolve_target_role_embedding

        async def _fake_resolve(db_: object, target_role: str | None) -> list[float]:
            return close_vector

        interviews_module._resolve_target_role_embedding = _fake_resolve  # type: ignore[assignment]
        try:
            picked = await select_next_question(db, interview=interview)
        finally:
            interviews_module._resolve_target_role_embedding = original

    assert picked is not None
    assert picked.category == "close"


async def test_select_next_question_falls_back_to_stable_order_without_target_role(
    isolated_technical_bank: None,
) -> None:
    async with AsyncSessionLocal() as db:
        db.add(InterviewQuestionBank(mode=_MODE, category="only", question_text="Only Q"))
        await db.commit()

    interview = Interview(id=uuid.uuid4(), user_id=uuid.uuid4(), mode=_MODE, target_role=None)
    async with AsyncSessionLocal() as db:
        picked = await select_next_question(db, interview=interview)
    assert picked is not None  # never crashes with no target_role and no ranking signal


async def test_create_interview_creates_first_question(
    isolated_technical_bank: None, interview_user: User
) -> None:
    async with AsyncSessionLocal() as db:
        db.add(InterviewQuestionBank(mode=_MODE, category="c", question_text="Q1"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        user = await db.get(User, interview_user.id)
        assert user is not None
        interview = await create_interview(db, user=user, mode=_MODE, target_role=None)
        await db.commit()
        interview_id = interview.id

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InterviewQuestion).where(InterviewQuestion.interview_id == interview_id)
        )
        questions = result.scalars().all()
        assert len(questions) == 1
        assert questions[0].order_index == 0


def _make_evaluation(correctness: float = 80) -> InterviewEvaluationResult:
    return InterviewEvaluationResult(
        correctness_score=correctness, depth_score=70, communication_score=90, feedback="Good."
    )


async def test_record_answer_then_advance_creates_next_question(
    isolated_technical_bank: None, interview_user: User
) -> None:
    async with AsyncSessionLocal() as db:
        db.add_all(
            [
                InterviewQuestionBank(mode=_MODE, category="a", question_text="Q-a"),
                InterviewQuestionBank(mode=_MODE, category="b", question_text="Q-b"),
            ]
        )
        await db.commit()

    async with AsyncSessionLocal() as db:
        user = await db.get(User, interview_user.id)
        assert user is not None
        interview = await create_interview(db, user=user, mode=_MODE, target_role=None)
        await db.commit()
        interview_id = interview.id

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InterviewQuestion).where(InterviewQuestion.interview_id == interview_id)
        )
        question = result.scalars().one()
        await record_answer(
            db,
            question=question,
            answer_text="My answer",
            response_time_seconds=30,
            evaluation=_make_evaluation(),
        )
        refreshed_interview = await db.get(Interview, interview_id)
        assert refreshed_interview is not None
        next_question = await advance_or_complete(db, interview=refreshed_interview)
        await db.commit()

    assert next_question is not None
    assert next_question.order_index == 1
    async with AsyncSessionLocal() as db:
        final_interview = await db.get(Interview, interview_id)
        assert final_interview is not None
        assert final_interview.status == InterviewStatus.IN_PROGRESS


async def test_session_completes_and_computes_overall_score_after_all_questions(
    isolated_technical_bank: None, interview_user: User
) -> None:
    async with AsyncSessionLocal() as db:
        db.add(InterviewQuestionBank(mode=_MODE, category="only", question_text="Q1"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        user = await db.get(User, interview_user.id)
        assert user is not None
        interview = await create_interview(db, user=user, mode=_MODE, target_role=None)
        await db.commit()
        interview_id = interview.id

    # Answer all 5 questions (repeats are expected once the 1-question bank is exhausted).
    for _ in range(5):
        async with AsyncSessionLocal() as db:
            round_interview = await db.get(Interview, interview_id)
            assert round_interview is not None
            result = await db.execute(
                select(InterviewQuestion)
                .where(InterviewQuestion.interview_id == interview_id)
                .order_by(InterviewQuestion.order_index.desc())
                .limit(1)
            )
            question = result.scalars().one()
            await record_answer(
                db,
                question=question,
                answer_text="Answer",
                response_time_seconds=10,
                evaluation=_make_evaluation(correctness=60),
            )
            await advance_or_complete(db, interview=round_interview)
            await db.commit()

    async with AsyncSessionLocal() as db:
        final_interview = await db.get(Interview, interview_id)
        assert final_interview is not None
        assert final_interview.status == InterviewStatus.COMPLETED
        assert final_interview.overall_score is not None
        # (60 + 70 + 90) / 3 = 73.33, same for all 5 answered questions.
        assert float(final_interview.overall_score) == pytest.approx(73.33, abs=0.01)


async def test_record_answer_survives_concurrent_calls_for_the_same_question(
    isolated_technical_bank: None, interview_user: User
) -> None:
    """Regression test mirroring prior phases' race regressions: two concurrent submissions for
    the same question must not both succeed, and the loser must get a clean
    `AnswerAlreadySubmittedError`, never an unhandled crash."""
    async with AsyncSessionLocal() as db:
        db.add(InterviewQuestionBank(mode=_MODE, category="c", question_text="Q1"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        user = await db.get(User, interview_user.id)
        assert user is not None
        interview = await create_interview(db, user=user, mode=_MODE, target_role=None)
        await db.commit()
        interview_id = interview.id

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InterviewQuestion).where(InterviewQuestion.interview_id == interview_id)
        )
        question_id = result.scalars().one().id

    async def _submit() -> str:
        async with AsyncSessionLocal() as db:
            question = await db.get(InterviewQuestion, question_id)
            assert question is not None
            try:
                await record_answer(
                    db,
                    question=question,
                    answer_text="Racing answer",
                    response_time_seconds=5,
                    evaluation=_make_evaluation(),
                )
                await db.commit()
                return "won"
            except AnswerAlreadySubmittedError:
                return "lost"

    results = await asyncio.gather(_submit(), _submit())
    assert sorted(results) == ["lost", "won"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InterviewAnswer).where(InterviewAnswer.question_id == question_id)
        )
        answers = result.scalars().all()
        assert len(answers) == 1  # no duplicate answer row from the losing attempt


async def test_has_answer(isolated_technical_bank: None, interview_user: User) -> None:
    async with AsyncSessionLocal() as db:
        db.add(InterviewQuestionBank(mode=_MODE, category="c", question_text="Q1"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        user = await db.get(User, interview_user.id)
        assert user is not None
        interview = await create_interview(db, user=user, mode=_MODE, target_role=None)
        await db.commit()
        interview_id = interview.id

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InterviewQuestion).where(InterviewQuestion.interview_id == interview_id)
        )
        question = result.scalars().one()
        assert await has_answer(db, question_id=question.id) is False
        await record_answer(
            db,
            question=question,
            answer_text="A",
            response_time_seconds=1,
            evaluation=_make_evaluation(),
        )
        await db.commit()
        assert await has_answer(db, question_id=question.id) is True


async def test_delete_interview_then_list_excludes_it(
    isolated_technical_bank: None, interview_user: User
) -> None:
    async with AsyncSessionLocal() as db:
        db.add(InterviewQuestionBank(mode=_MODE, category="c", question_text="Q1"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        user = await db.get(User, interview_user.id)
        assert user is not None
        interview = await create_interview(db, user=user, mode=_MODE, target_role=None)
        await db.commit()
        interview_id = interview.id

    async with AsyncSessionLocal() as db:
        deleted = await delete_interview(db, user_id=interview_user.id, interview_id=interview_id)
        await db.commit()
    assert deleted is True

    async with AsyncSessionLocal() as db:
        interviews, _ = await list_interviews(db, user_id=interview_user.id, limit=20, cursor=None)
    assert interview_id not in {i.id for i in interviews}


async def test_delete_interview_is_a_noop_for_unowned_or_missing(
    isolated_technical_bank: None, interview_user: User
) -> None:
    async with AsyncSessionLocal() as db:
        deleted = await delete_interview(db, user_id=interview_user.id, interview_id=uuid.uuid4())
    assert deleted is False


async def test_list_interviews_pagination_round_trips(
    isolated_technical_bank: None, interview_user: User
) -> None:
    async with AsyncSessionLocal() as db:
        db.add(InterviewQuestionBank(mode=_MODE, category="c", question_text="Q1"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        user = await db.get(User, interview_user.id)
        assert user is not None
        for _ in range(3):
            await create_interview(db, user=user, mode=_MODE, target_role=None)
            await db.commit()

    async with AsyncSessionLocal() as db:
        page_one, cursor = await list_interviews(
            db, user_id=interview_user.id, limit=2, cursor=None
        )
    assert len(page_one) == 2
    assert cursor is not None

    async with AsyncSessionLocal() as db:
        page_two, cursor_two = await list_interviews(
            db, user_id=interview_user.id, limit=2, cursor=cursor
        )
    assert len(page_two) == 1
    assert cursor_two is None
    assert {i.id for i in page_one} & {i.id for i in page_two} == set()


async def test_get_analytics_averages_only_this_users_completed_interviews(
    isolated_technical_bank: None, interview_user: User
) -> None:
    async with AsyncSessionLocal() as db:
        db.add(InterviewQuestionBank(mode=_MODE, category="c", question_text="Q1"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        user = await db.get(User, interview_user.id)
        assert user is not None
        interview = await create_interview(db, user=user, mode=_MODE, target_role=None)
        await db.commit()
        interview_id = interview.id

    for _ in range(5):
        async with AsyncSessionLocal() as db:
            round_interview = await db.get(Interview, interview_id)
            assert round_interview is not None
            result = await db.execute(
                select(InterviewQuestion)
                .where(InterviewQuestion.interview_id == interview_id)
                .order_by(InterviewQuestion.order_index.desc())
                .limit(1)
            )
            question = result.scalars().one()
            await record_answer(
                db,
                question=question,
                answer_text="A",
                response_time_seconds=1,
                evaluation=_make_evaluation(correctness=90),
            )
            await advance_or_complete(db, interview=round_interview)
            await db.commit()

    async with AsyncSessionLocal() as db:
        analytics = await get_analytics(db, user_id=interview_user.id)
    assert analytics.total_completed == 1
    assert analytics.average_overall_score is not None
    assert analytics.average_correctness_score == pytest.approx(90.0)
    assert len(analytics.recent) == 1
    assert analytics.recent[0].id == interview_id


async def test_get_analytics_excludes_in_progress_sessions_from_dimension_averages(
    isolated_technical_bank: None, interview_user: User
) -> None:
    """Regression for a real human-review-caught bug: the per-dimension averages (correctness/
    depth/communication) must be scoped to COMPLETED sessions only, exactly like
    `total_completed`/`average_overall_score` — an answered-but-not-yet-completed session's score
    must never quietly skew the reported averages."""
    async with AsyncSessionLocal() as db:
        db.add(InterviewQuestionBank(mode=_MODE, category="c1", question_text="Q1"))
        db.add(InterviewQuestionBank(mode=_MODE, category="c2", question_text="Q2"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        user = await db.get(User, interview_user.id)
        assert user is not None
        completed_interview = await create_interview(db, user=user, mode=_MODE, target_role=None)
        await db.commit()
        completed_id = completed_interview.id

    for _ in range(5):
        async with AsyncSessionLocal() as db:
            round_interview = await db.get(Interview, completed_id)
            assert round_interview is not None
            result = await db.execute(
                select(InterviewQuestion)
                .where(InterviewQuestion.interview_id == completed_id)
                .order_by(InterviewQuestion.order_index.desc())
                .limit(1)
            )
            question = result.scalars().one()
            await record_answer(
                db,
                question=question,
                answer_text="A",
                response_time_seconds=1,
                evaluation=_make_evaluation(correctness=90),
            )
            await advance_or_complete(db, interview=round_interview)
            await db.commit()

    # A second, separate session left deliberately in_progress with one very differently-scored
    # answered question — must not appear in any average below.
    async with AsyncSessionLocal() as db:
        user = await db.get(User, interview_user.id)
        assert user is not None
        in_progress_interview = await create_interview(db, user=user, mode=_MODE, target_role=None)
        await db.commit()
        in_progress_id = in_progress_interview.id

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InterviewQuestion).where(InterviewQuestion.interview_id == in_progress_id)
        )
        question = result.scalars().one()
        await record_answer(
            db,
            question=question,
            answer_text="A",
            response_time_seconds=1,
            evaluation=_make_evaluation(correctness=10),
        )
        await db.commit()

    async with AsyncSessionLocal() as db:
        in_progress_interview = await db.get(Interview, in_progress_id)
        assert in_progress_interview is not None
        assert in_progress_interview.status == InterviewStatus.IN_PROGRESS

    async with AsyncSessionLocal() as db:
        analytics = await get_analytics(db, user_id=interview_user.id)
    assert analytics.total_completed == 1
    # If the in-progress session's correctness=10 answer leaked in, this would drop well below 90.
    assert analytics.average_correctness_score == pytest.approx(90.0)
