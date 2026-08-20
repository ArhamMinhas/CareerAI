import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.resume_extraction import ResumeExtractionError, extract_resume_fields
from app.core.db import AsyncSessionLocal, engine
from app.core.storage import StorageError, download_object
from app.models.profile import Profile
from app.models.resume import Resume, ResumeStatus, ResumeVersion
from app.models.skill import SkillSource, UserSkill
from app.schemas.resume import ResumeExtraction
from app.services.ai_conversations import AIFeature, log_conversation
from app.services.embeddings import store_embedding
from app.services.resume_parsing import (
    TextExtractionError,
    UnsupportedFileError,
    detect_sections,
    extract_text,
)
from app.services.resume_scoring import compute_overall_score, compute_score_breakdown
from app.services.skill_taxonomy import get_or_create_skill
from app.workers.celery_app import celery_app

# Conservative char cap for the embedding call — well under every embedding model's token
# limit (e.g. OpenAI's ~8191 tokens) without needing a tokenizer dependency just for this.
_EMBEDDING_MAX_CHARS = 8_000


@celery_app.task(name="resumes.process")
def process_resume_task(resume_id: str) -> None:
    asyncio.run(_process_resume(uuid.UUID(resume_id)))


async def _process_resume(resume_id: uuid.UUID) -> None:
    # Fresh connections for this task's own event loop. `asyncio.run()` above hands every task
    # invocation a brand-new event loop, but `engine` (app/core/db.py) is a process-level
    # singleton — without this, a worker's second task inherits a connection pool bound to the
    # first task's already-closed loop. Same fix, same reasoning, as
    # apps/api/tests/conftest.py's `_fresh_engine_per_test`.
    await engine.dispose()

    async with AsyncSessionLocal() as db:
        resume = await db.get(Resume, resume_id)
        if resume is None:
            return

        resume.status = ResumeStatus.PROCESSING
        await db.commit()

        # Everything through the final commit is one try block — a resume must never be left
        # stuck in "processing" forever no matter *where* it fails, extraction or persistence.
        # (This used to end after `compute_overall_score`, leaving the skill-sync step
        # unprotected — a duplicate-skill collision there raised uncaught and left real
        # resumes stuck at "processing" indefinitely, since `status=PROCESSING` had already
        # been committed separately above and nothing after it ever committed again.)
        try:
            content = await download_object(resume.file_url)
            raw_text = extract_text(content, resume.file_type)
            sections = detect_sections(raw_text)
            extraction, llm_result = await extract_resume_fields(raw_text)
            await log_conversation(
                db,
                user_id=resume.user_id,
                feature=AIFeature.RESUME_ANALYSIS,
                result=llm_result,
                prompt_name="resume_extraction",
                prompt_version="v1",
            )
            await store_embedding(
                db, owner_type="resume", owner_id=resume.id, text=raw_text[:_EMBEDDING_MAX_CHARS]
            )
            breakdown = compute_score_breakdown(extraction, raw_text, sections)
            overall = compute_overall_score(breakdown)

            structured = extraction.model_dump(mode="json")
            breakdown_data = breakdown.model_dump(mode="json")

            resume.structured_data = structured
            resume.score_breakdown = breakdown_data
            resume.overall_score = overall
            resume.status = ResumeStatus.COMPLETED
            resume.failure_reason = None

            existing_versions = await db.execute(
                select(ResumeVersion).where(ResumeVersion.resume_id == resume.id)
            )
            version_number = len(existing_versions.scalars().all()) + 1
            db.add(
                ResumeVersion(
                    resume_id=resume.id,
                    version_number=version_number,
                    structured_data=structured,
                    overall_score=overall,
                    score_breakdown=breakdown_data,
                )
            )

            await _sync_skills_from_resume(db, resume, extraction)
            await db.commit()
        except (
            StorageError,
            UnsupportedFileError,
            TextExtractionError,
            ResumeExtractionError,
        ) as exc:
            # A failed flush/commit above leaves the session unusable until rolled back —
            # required before `resume` (still attached to this session) can be touched again.
            await db.rollback()
            resume.status = ResumeStatus.FAILED
            resume.failure_reason = str(exc)[:1024]
            await db.commit()
        except Exception:
            # Never leave a resume stuck in "processing" on an unexpected error — record a
            # generic failure (no internals leaked, same policy as app/core/errors.py) and
            # re-raise so Celery still logs/retries per its own policy.
            await db.rollback()
            resume.status = ResumeStatus.FAILED
            resume.failure_reason = "An unexpected error occurred while processing this resume."
            await db.commit()
            raise


async def _sync_skills_from_resume(
    db: AsyncSession, resume: Resume, extraction: ResumeExtraction
) -> None:
    """Adds resume-extracted skills to the user's profile with `source=resume` — the
    integration point `app/models/skill.py`'s `UserSkill.resume_id` docstring anticipated back
    in Phase 3. Only additive: never removes or overwrites a skill the user already has
    (manually added or from an earlier resume), just fills in ones that are missing."""
    if not extraction.skills:
        return

    result = await db.execute(select(Profile).where(Profile.user_id == resume.user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=resume.user_id)
        db.add(profile)
        await db.flush()

    existing = await db.execute(select(UserSkill).where(UserSkill.profile_id == profile.id))
    # Keyed by resolved skill id, not the raw extracted string — `get_or_create_skill`
    # dedupes by *slug*, so two different-looking extracted strings ("Node.js", "NodeJS")
    # can resolve to the *same* skill row even though their lowercased text differs. Tracking
    # by raw string let two such strings both pass the "not seen yet" check and both try to
    # insert a UserSkill for the same (profile_id, skill_id) pair — a real duplicate-key
    # crash observed in production, left the resume stuck in "processing" forever (see
    # `_process_resume`'s try/except comment).
    claimed_skill_ids = {row.skill_id for row in existing.scalars().all()}

    for skill_name in extraction.skills:
        clean = skill_name.strip()
        if not clean:
            continue
        skill = await get_or_create_skill(db, clean)
        if skill.id in claimed_skill_ids:
            continue
        db.add(
            UserSkill(
                profile_id=profile.id,
                skill_id=skill.id,
                resume_id=resume.id,
                source=SkillSource.RESUME,
            )
        )
        claimed_skill_ids.add(skill.id)
