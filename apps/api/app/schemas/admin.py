import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Role


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: Role
    email_verified: bool
    created_at: datetime


class AdminUserUpdateRequest(BaseModel):
    role: Role


class AdminCompanyRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class AdminJobRead(BaseModel):
    """Admin list view — unlike the public `JobRead` (app/schemas/job.py), this includes
    `is_active` since the whole point of this listing is to also surface inactive postings."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    company: AdminCompanyRef
    is_active: bool
    remote: bool
    source: str | None
    search_category: str | None
    created_at: datetime


class AdminJobCreateRequest(BaseModel):
    company_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    seniority_level: str | None = None
    employment_type: str | None = None
    location: str | None = None
    remote: bool = False
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    currency: str | None = None
    apply_url: str | None = None
    search_category: str | None = None
    required_skill_names: list[str] = Field(default_factory=list)


class AdminSkillRead(BaseModel):
    """Never built via `model_validate` — `has_curated_content` is computed, not a column, so
    the route constructs this directly rather than claiming `from_attributes` support it can't
    actually provide."""

    id: uuid.UUID
    name: str
    slug: str
    category: str | None
    has_curated_content: bool
    created_at: datetime


class AdminSkillCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str | None = None


class AIUsageByFeature(BaseModel):
    feature: str
    call_count: int
    prompt_tokens: int
    completion_tokens: int
    avg_latency_ms: float


class AIUsageByModel(BaseModel):
    model: str
    call_count: int
    prompt_tokens: int
    completion_tokens: int
    avg_latency_ms: float


class AIUsageRead(BaseModel):
    """`GET /api/v1/admin/ai-usage` — real aggregates over `ai_conversations` (Phase 5). No
    dollar-cost figure: no real per-token pricing constants exist anywhere in this codebase, and
    fabricating one would misrepresent real spend."""

    by_feature: list[AIUsageByFeature] = Field(default_factory=list)
    by_model: list[AIUsageByModel] = Field(default_factory=list)


class ModelMetricsEntry(BaseModel):
    """One trained model's currently-pinned-version metadata (Phase 8) — real stored fields
    only, never a live-computed drift metric (drift monitoring is Phase 14 scope). `available`
    is `False` (every other field `None`) when `metadata.json` is missing or malformed for this
    model/version — never a 500 for the other 5 models over one bad file."""

    name: str
    version: str
    available: bool
    metric: str | None = None
    score: float | None = None
    training_window: str | None = None
    limitations: str | None = None
    retrained_at: str | None = None


class ModelMetricsRead(BaseModel):
    models: list[ModelMetricsEntry] = Field(default_factory=list)


class SystemHealthRead(BaseModel):
    """`GET /api/v1/admin/system-health` — real connectivity checks, not audit-log-based (Phase
    15 scope). `database_ok` has an inherent limitation worth naming honestly: reaching this
    route at all already required a working DB connection (auth resolves the user via a DB
    query), so this mostly catches a connection going bad *mid-session*, not a fully-down DB —
    a fully-down DB means an admin can't authenticate to see this page in the first place.
    `redis_ok` has no such limitation — auth never touches Redis, so this is genuinely
    independent signal."""

    database_ok: bool
    redis_ok: bool
    total_users: int
    total_jobs: int
    total_resumes: int
