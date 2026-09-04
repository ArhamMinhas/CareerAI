"""Seeds `skill_prerequisites` and `skill_learning_resources` — the curated reference content
the Learning Roadmap's deterministic sequencing algorithm reads (docs/ROADMAP.md Phase 10).
Covers the same 20 skills `seed_career_paths.py`'s `SKILL_CONTENT` dict already curates
`seo_summary` for — a deliberate, documented scope decision (docs/ROADMAP.md), not an oversight:
most of the ~100+ distinct skill names across the seeded career paths have no curated
prerequisite edge or resource, and the sequencing algorithm falls back to priority-only ordering
for those, which is expected.

Prerequisite edges are a small, honest set — only relationships genuinely confident to be real
learning-order dependencies, not padded to hit a round number. Resource URLs are all stable,
official-domain links (docs.python.org, react.dev, kubernetes.io, etc.) — never a course-platform
URL whose long-term stability can't be verified.

Idempotent — safe to re-run any time this content changes; upserts by (skill, requires_skill) for
prerequisites and replaces each skill's resource list wholesale (matching `kb_ingest.py`'s
"replace the whole set for one owner" idiom — this is small, single-process, manually-run
reference data, not a per-user table, so no SAVEPOINT race protection is needed here, same
simplicity as `seed_career_paths.py`).

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.scripts.seed_learning_resources`):

    python -m app.scripts.seed_learning_resources
"""

import asyncio
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal, engine
from app.models.skill import Skill
from app.models.skill_learning_resource import LearningResourceType, SkillLearningResource
from app.models.skill_prerequisite import SkillPrerequisite
from app.services.skill_taxonomy import get_or_create_skill


@dataclass(frozen=True)
class SeedLearningResource:
    title: str
    resource_type: LearningResourceType
    url: str | None = None
    estimated_hours: int | None = None


# (skill, requires_skill) — skill can only be sequenced after requires_skill, per
# app/services/learning_roadmap.py's topological sort. Only edges genuinely confident to be real
# learning-order dependencies, deliberately not padded for coverage.
PREREQUISITES: list[tuple[str, str]] = [
    ("Deep Learning", "Machine Learning"),
    ("Machine Learning", "Python"),
    ("Machine Learning", "Statistics"),
    ("MLOps", "Machine Learning"),
    ("Kubernetes", "Docker"),
    ("Next.js", "React"),
    ("A/B Testing", "Statistics"),
    ("Vector Databases", "SQL"),
]

SKILL_RESOURCES: dict[str, list[SeedLearningResource]] = {
    "Python": [
        SeedLearningResource(
            "The Official Python Tutorial",
            LearningResourceType.DOCS,
            "https://docs.python.org/3/tutorial/",
            8,
        ),
        SeedLearningResource(
            "Build a CLI tool that fetches and summarizes real job postings from a public API",
            LearningResourceType.PROJECT,
            estimated_hours=6,
        ),
    ],
    "Machine Learning": [
        SeedLearningResource(
            "scikit-learn: Getting Started",
            LearningResourceType.DOCS,
            "https://scikit-learn.org/stable/getting_started.html",
            10,
        ),
        SeedLearningResource(
            "Train and evaluate a classifier on a public dataset against a real baseline",
            LearningResourceType.PROJECT,
            estimated_hours=8,
        ),
    ],
    "Deep Learning": [
        SeedLearningResource(
            "PyTorch: Learn the Basics",
            LearningResourceType.DOCS,
            "https://pytorch.org/tutorials/beginner/basics/intro.html",
            10,
        ),
        SeedLearningResource(
            "Train a small image classifier and report accuracy against a simple baseline",
            LearningResourceType.PROJECT,
            estimated_hours=8,
        ),
    ],
    "SQL": [
        SeedLearningResource(
            "PostgreSQL Tutorial",
            LearningResourceType.DOCS,
            "https://www.postgresql.org/docs/current/tutorial.html",
            6,
        ),
        SeedLearningResource(
            "Write a set of analytical window-function queries against a public dataset",
            LearningResourceType.PROJECT,
            estimated_hours=5,
        ),
    ],
    "REST APIs": [
        SeedLearningResource(
            "MDN: An Overview of HTTP",
            LearningResourceType.DOCS,
            "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview",
            4,
        ),
        SeedLearningResource(
            "Design and document a small REST API with OpenAPI",
            LearningResourceType.PROJECT,
            estimated_hours=6,
        ),
    ],
    "System Design": [
        SeedLearningResource(
            "The System Design Primer",
            LearningResourceType.ARTICLE,
            "https://github.com/donnemartin/system-design-primer",
            12,
        ),
        SeedLearningResource(
            "Write a one-page design doc for a URL shortener, covering scale and failure modes",
            LearningResourceType.PROJECT,
            estimated_hours=4,
        ),
    ],
    "Docker": [
        SeedLearningResource(
            "Docker: Get Started Guide",
            LearningResourceType.DOCS,
            "https://docs.docker.com/get-started/",
            6,
        ),
        SeedLearningResource(
            "Containerize an existing app you've built and document the Dockerfile decisions",
            LearningResourceType.PROJECT,
            estimated_hours=4,
        ),
    ],
    "Kubernetes": [
        SeedLearningResource(
            "Kubernetes Basics Tutorial",
            LearningResourceType.DOCS,
            "https://kubernetes.io/docs/tutorials/kubernetes-basics/",
            10,
        ),
    ],
    "AWS": [
        SeedLearningResource(
            "AWS Getting Started Resource Center",
            LearningResourceType.DOCS,
            "https://aws.amazon.com/getting-started/",
            8,
        ),
    ],
    "TypeScript": [
        SeedLearningResource(
            "The TypeScript Handbook",
            LearningResourceType.DOCS,
            "https://www.typescriptlang.org/docs/handbook/intro.html",
            6,
        ),
    ],
    "React": [
        SeedLearningResource(
            "React: Learn",
            LearningResourceType.DOCS,
            "https://react.dev/learn",
            10,
        ),
    ],
    "Next.js": [
        SeedLearningResource(
            "Next.js Documentation",
            LearningResourceType.DOCS,
            "https://nextjs.org/docs",
            8,
        ),
        SeedLearningResource(
            "Rebuild a small existing project as a Next.js app with real data fetching",
            LearningResourceType.PROJECT,
            estimated_hours=8,
        ),
    ],
    "PostgreSQL": [
        SeedLearningResource(
            "PostgreSQL Documentation",
            LearningResourceType.DOCS,
            "https://www.postgresql.org/docs/current/",
            6,
        ),
    ],
    "Statistics": [
        SeedLearningResource(
            "Khan Academy: Statistics and Probability",
            LearningResourceType.COURSE,
            "https://www.khanacademy.org/math/statistics-probability",
            15,
        ),
    ],
    "A/B Testing": [
        SeedLearningResource(
            "A/B Testing Glossary and Fundamentals",
            LearningResourceType.ARTICLE,
            "https://www.optimizely.com/optimization-glossary/ab-testing/",
            3,
        ),
        SeedLearningResource(
            "Design a real A/B test for an existing feature, including sample-size reasoning",
            LearningResourceType.PROJECT,
            estimated_hours=4,
        ),
    ],
    "Prompt Engineering": [
        SeedLearningResource(
            "OpenAI: Prompt Engineering Guide",
            LearningResourceType.DOCS,
            "https://platform.openai.com/docs/guides/prompt-engineering",
            4,
        ),
    ],
    "Vector Databases": [
        SeedLearningResource(
            "What is a Vector Database?",
            LearningResourceType.ARTICLE,
            "https://www.pinecone.io/learn/vector-database/",
            3,
        ),
    ],
    "MLOps": [
        SeedLearningResource(
            "ml-ops.org: MLOps Principles",
            LearningResourceType.ARTICLE,
            "https://ml-ops.org/",
            5,
        ),
    ],
    "Product Sense": [
        SeedLearningResource(
            "SVPG: Articles on Product Management",
            LearningResourceType.ARTICLE,
            "https://www.svpg.com/articles/",
            4,
        ),
    ],
    "Git": [
        SeedLearningResource(
            "Git Documentation",
            LearningResourceType.DOCS,
            "https://git-scm.com/doc",
            4,
        ),
    ],
}


async def _seed_prerequisites(db: AsyncSession) -> int:
    count = 0
    for skill_name, requires_name in PREREQUISITES:
        skill = await get_or_create_skill(db, skill_name)
        requires_skill = await get_or_create_skill(db, requires_name)
        result = await db.execute(
            select(SkillPrerequisite).where(
                SkillPrerequisite.skill_id == skill.id,
                SkillPrerequisite.requires_skill_id == requires_skill.id,
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(SkillPrerequisite(skill_id=skill.id, requires_skill_id=requires_skill.id))
            count += 1
    await db.flush()
    return count


async def _seed_resources_for_skill(
    db: AsyncSession, skill: Skill, resources: list[SeedLearningResource]
) -> None:
    await db.execute(
        delete(SkillLearningResource).where(SkillLearningResource.skill_id == skill.id)
    )
    for index, resource in enumerate(resources):
        db.add(
            SkillLearningResource(
                skill_id=skill.id,
                title=resource.title,
                url=resource.url,
                resource_type=resource.resource_type,
                estimated_hours=resource.estimated_hours,
                order_index=index,
            )
        )
    await db.flush()


async def seed() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        edge_count = await _seed_prerequisites(db)
        await db.commit()
        print(f"seeded {edge_count} new prerequisite edge(s)")

        for skill_name, resources in SKILL_RESOURCES.items():
            skill = await get_or_create_skill(db, skill_name)
            await _seed_resources_for_skill(db, skill, resources)
            await db.commit()
            print(f"seeded {len(resources)} resource(s) for skill: {skill_name}")


if __name__ == "__main__":
    asyncio.run(seed())
