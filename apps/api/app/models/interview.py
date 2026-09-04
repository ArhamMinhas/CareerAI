import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.embedding import EMBEDDING_DIMENSIONS
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class InterviewMode(enum.StrEnum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    HR = "hr"
    SYSTEM_DESIGN = "system_design"
    ML = "ml"
    DATA_SCIENCE = "data_science"


class InterviewStatus(enum.StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class InterviewQuestionBank(UUIDPKMixin, Base):
    """Curated, real interview questions — docs/DATABASE.md §2.4, Phase 11. Shared reference
    content, like `CareerPathSkill`/`SkillLearningResource` — authored once, never duplicated per
    session; `app/services/interviews.py`'s selection algorithm reads this table and copies the
    text it picks onto a new `InterviewQuestion` row.

    `embedding` lives here, not on the per-session `InterviewQuestion` row the original ERD
    sketch put it on — a deliberate deviation (docs/DATABASE.md records the full reasoning):
    this is curated reference data selection ranks against (like `resources.embedding`), not a
    per-session artifact that would need its own embedding call on every question asked."""

    __tablename__ = "interview_question_bank"

    mode: Mapped[InterviewMode] = mapped_column(
        Enum(InterviewMode, name="interview_mode"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    question_text: Mapped[str] = mapped_column(Text(), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Interview(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A user's mock-interview session — docs/DATABASE.md §2.4, Phase 11. Soft-deleted like
    `Application`/`LearningPath`: "history" is explicit Phase 11 scope, so this is durable
    user-authored content, not cached/computed output like `SkillGap`/`JobMatch`. Unlike those
    two, there's no partial unique index — a user legitimately runs many practice sessions for
    the same `mode`+`target_role`, so there's no natural key re-creation-after-delete needs to
    protect.

    `target_role` is a genuinely optional, plain free-text string — a deliberate deviation from
    `SkillGap`/`LearningPath.target_role`'s "must resolve to a real `CareerPath` via
    `resolve_career_path`" convention. Those two features literally cannot compute without a
    curated match; interview practice has real value even for a role with no curated catalog
    entry, so forcing a 404 here would block practice sessions for niche titles for no benefit.
    `app/services/interviews.py` makes a best-effort resolution attempt against `CareerPath`
    only to feed question-selection ranking when it happens to succeed — resolution failure
    never blocks session creation.

    `overall_score` is NULL until the session completes — computed deterministically as the
    mean of every answered question's (correctness+depth+communication)/3, never an LLM
    judgment call on the aggregate. `ABANDONED` is reserved, no transition path yet — same
    treatment `LearningPathStatus` got in Phase 10, for the same reason (a future explicit
    "abandon" action, not used by anything this phase ships)."""

    __tablename__ = "interviews"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mode: Mapped[InterviewMode] = mapped_column(
        Enum(InterviewMode, name="interview_mode"), nullable=False
    )
    target_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status"),
        default=InterviewStatus.IN_PROGRESS,
        nullable=False,
    )
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)


class InterviewQuestion(UUIDPKMixin, Base):
    """One question actually asked in a session — docs/DATABASE.md §2.4, Phase 11.
    `question_text`/`category` are denormalized copies of the bank row at selection time (not a
    live join) so a session's historical record stays stable even if the bank's curated content
    is later edited. `bank_question_id` is nullable purely for traceability back to the source
    row; nothing in this phase ever creates a question that isn't bank-sourced, but the FK isn't
    load-bearing for that invariant."""

    __tablename__ = "interview_questions"
    __table_args__ = (
        UniqueConstraint(
            "interview_id", "order_index", name="uq_interview_questions_interview_order"
        ),
    )

    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bank_question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_question_bank.id", ondelete="SET NULL"),
        nullable=True,
    )
    question_text: Mapped[str] = mapped_column(Text(), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InterviewAnswer(UUIDPKMixin, Base):
    """A user's submitted answer to one question — docs/DATABASE.md §2.4, Phase 11.
    `question_id` is UNIQUE (one answer per question, matching the ERD's `o|` 1:1 relationship)
    — this is also the concurrency guard's DB-level backstop: two racing submissions for the same
    question can't both insert (see `app/services/interviews.py::record_answer`'s pre-check +
    caught `IntegrityError` -> 409, which turns this constraint violation into a clean response
    instead of an unhandled 500)."""

    __tablename__ = "interview_answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    answer_text: Mapped[str] = mapped_column(Text(), nullable=False)
    response_time_seconds: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InterviewEvaluation(UUIDPKMixin, Base):
    """The LLM's structured evaluation of one answer — docs/DATABASE.md §2.4, Phase 11. Every
    score is `0-100` (enforced at the schema layer, `app/ai/interview_evaluation.py`'s
    `Field(ge=0, le=100)`, same bounded-numeric convention as `ResumeExtraction.SubScore`).
    `answer_id` UNIQUE, same 1:1-relationship/concurrency-backstop reasoning as
    `InterviewAnswer.question_id`."""

    __tablename__ = "interview_evaluations"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_answers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    correctness_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    depth_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    communication_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    feedback: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
