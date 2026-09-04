import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.interview import InterviewMode, InterviewStatus


class InterviewCreateRequest(BaseModel):
    mode: InterviewMode
    target_role: str | None = Field(default=None, max_length=255)


class InterviewAnswerRequest(BaseModel):
    question_id: uuid.UUID
    answer_text: str = Field(min_length=1, max_length=10_000)
    response_time_seconds: int = Field(ge=0, le=3_600)


class InterviewEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    correctness_score: float
    depth_score: float
    communication_score: float
    feedback: str


class InterviewAnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    answer_text: str
    response_time_seconds: int
    created_at: datetime
    evaluation: InterviewEvaluationRead | None = None


class InterviewQuestionRead(BaseModel):
    """One question in a session, with its answer/evaluation if already submitted. The
    frontend/route derive "the current question" as the first item with `answer is None` —
    there's no separate `current_question` field, matching the "one response has everything"
    pattern RAG/roadmap already use rather than a second, potentially-inconsistent field."""

    id: uuid.UUID
    question_text: str
    category: str
    order_index: int
    answer: InterviewAnswerRead | None = None


class InterviewRead(BaseModel):
    """List-view projection — `GET /api/v1/interviews` (history)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mode: InterviewMode
    target_role: str | None
    status: InterviewStatus
    overall_score: float | None
    created_at: datetime


class InterviewDetailRead(InterviewRead):
    """`POST /api/v1/interviews`, `GET /api/v1/interviews/{id}`,
    `POST /api/v1/interviews/{id}/answer` — every route that returns a full session. `questions`
    isn't an ORM relationship — populated by the route from a fresh, ordered query joining
    answers/evaluations (app/services/interviews.py), same reasoning as `LearningRoadmapRead`."""

    questions: list[InterviewQuestionRead] = Field(default_factory=list)


class InterviewAnalyticsRecent(BaseModel):
    interview_id: uuid.UUID
    mode: InterviewMode
    overall_score: float
    completed_at: datetime


class InterviewAnalyticsRead(BaseModel):
    """`GET /api/v1/interviews/analytics` — real SQL aggregates over the current user's own
    completed sessions only. All fields `None`/empty when the user has no completed interviews
    yet, never a fabricated zero that could be misread as "you scored 0"."""

    total_completed: int
    average_overall_score: float | None
    average_correctness_score: float | None
    average_depth_score: float | None
    average_communication_score: float | None
    recent: list[InterviewAnalyticsRecent] = Field(default_factory=list)
