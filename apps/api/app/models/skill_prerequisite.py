import uuid

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import UUIDPKMixin


class SkillPrerequisite(UUIDPKMixin, Base):
    """A directed "must learn first" edge in the skill taxonomy — docs/DATABASE.md §2.4, Phase
    10. `skill_id` requires `requires_skill_id`: the Learning Roadmap's deterministic topological
    sort (app/services/learning_roadmap.py) reads this as a real prerequisite graph, per
    docs/AI_ARCHITECTURE.md §8's Learning Planner guardrail ("must respect prerequisite ordering
    computed deterministically" — the LLM never decides sequencing, only this graph does).

    Curated reference content, like `CareerPathSkill` — shared across all users, not per-user
    data. Seeded by `app/scripts/seed_learning_resources.py` with a small, honest set of edges
    (Deep Learning<-Machine Learning, Kubernetes<-Docker, etc.) rather than padded coverage: most
    of the skill taxonomy has no curated prerequisite edge, and the sequencing algorithm falls
    back to priority-only ordering for those skills, which is expected, not a bug."""

    __tablename__ = "skill_prerequisites"
    __table_args__ = (
        UniqueConstraint(
            "skill_id", "requires_skill_id", name="uq_skill_prerequisites_skill_requires"
        ),
        CheckConstraint(
            "skill_id != requires_skill_id", name="ck_skill_prerequisites_no_self_reference"
        ),
    )

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requires_skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
