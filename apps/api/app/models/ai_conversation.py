import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import UUIDPKMixin


class AIConversation(UUIDPKMixin, Base):
    """docs/DATABASE.md §2.4, safe-logging policy in docs/AI_ARCHITECTURE.md §10. `feature` is
    plain text (not a DB enum) since new AI features land every phase and a Postgres enum would
    need a migration for each one — validity is enforced at the application layer instead
    (see `app.services.ai_conversations.AIFeature`). `request_meta` holds prompt name/version
    and other non-sensitive parameters only — never full prompt/response text or raw PII, per
    §10; that's retained separately only when a case is explicitly flagged for eval review."""

    __tablename__ = "ai_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    request_meta: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
