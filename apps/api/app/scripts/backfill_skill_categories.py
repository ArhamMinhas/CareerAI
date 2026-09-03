"""Backfills `skills.category` (docs/ROADMAP.md Phase 8) — this column has existed since Phase 3
for manual-entry browsing/filtering, but no seed script or UI flow ever actually populated it, so
it was NULL for all 66 skills in the taxonomy. Needed as model 3's baseline (docs/ML_PIPELINE.md
§3: "manually curated category labels") — without it, there's nothing to evaluate skill
clustering against. `CATEGORIES` below is real, hand-curated domain knowledge (not derived from
clustering output itself — that would make the "baseline" circular), covering every skill
currently in the taxonomy.

Idempotent: re-running just re-applies the same mapping.

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.scripts.backfill_skill_categories`):

    python -m app.scripts.backfill_skill_categories
"""

import asyncio

from sqlalchemy import select

from app.core.db import AsyncSessionLocal, engine
from app.models.skill import Skill

CATEGORIES: dict[str, str] = {
    # Languages
    "Python": "Languages",
    "Javascript": "Languages",
    "TypeScript": "Languages",
    "Java": "Languages",
    "C++": "Languages",
    "PHP": "Languages",
    "SQL": "Languages",
    ".NET": "Languages",
    # Frontend
    "React": "Frontend",
    "React Native": "Frontend",
    "Angular": "Frontend",
    "Next.js": "Frontend",
    "HTML": "Frontend",
    "CSS": "Frontend",
    "HTML/CSS": "Frontend",
    "Accessibility": "Frontend",
    "Accessibility (a11y)": "Frontend",
    "Mobile Development": "Frontend",
    "Mobile/Responsive Development": "Frontend",
    "Responsive Development": "Frontend",
    # Backend
    "Node.js": "Backend",
    "FastAPI": "Backend",
    "Laravel": "Backend",
    "REST APIs": "Backend",
    "GraphQL": "Backend",
    "System Design": "Backend",
    # Data & ML
    "Machine Learning": "Data & ML",
    "Deep Learning": "Data & ML",
    "Natural Language Processing": "Data & ML",
    "PyTorch": "Data & ML",
    "Scikit-learn": "Data & ML",
    "Pandas": "Data & ML",
    "NumPy": "Data & ML",
    "Statistics": "Data & ML",
    "Data Analysis": "Data & ML",
    "Data Visualization": "Data & ML",
    "Tableau": "Data & ML",
    "Vector Databases": "Data & ML",
    "Prompt Engineering": "Data & ML",
    "MLOps": "Data & ML",
    "Data Structures & Algorithms": "Data & ML",
    # Databases
    "PostgreSQL": "Databases",
    "MySQL": "Databases",
    "Redis": "Databases",
    "Firebase": "Databases",
    # Cloud & DevOps
    "AWS": "Cloud & DevOps",
    "Docker": "Cloud & DevOps",
    "Kubernetes": "Cloud & DevOps",
    "Terraform": "Cloud & DevOps",
    "CI/CD": "Cloud & DevOps",
    "Linux": "Cloud & DevOps",
    "Networking": "Cloud & DevOps",
    "Performance Optimization": "Cloud & DevOps",
    "Git": "Cloud & DevOps",
    "GitHub": "Cloud & DevOps",
    "Testing (Unit/E2E)": "Cloud & DevOps",
    # Product & Design
    "Product Sense": "Product & Design",
    "User Research": "Product & Design",
    "Roadmapping": "Product & Design",
    "Stakeholder Management": "Product & Design",
    "A/B Testing": "Product & Design",
    # Soft Skills
    "Communication": "Soft Skills",
    "Collaboration": "Soft Skills",
    "Teamwork": "Soft Skills",
    "Remote pair-programming": "Soft Skills",
    "Agile/Scrum": "Soft Skills",
}


async def run() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        skills = list((await db.execute(select(Skill))).scalars().all())
        updated = 0
        unmapped: list[str] = []
        for skill in skills:
            category = CATEGORIES.get(skill.name)
            if category is not None:
                skill.category = category
                updated += 1
            else:
                unmapped.append(skill.name)
        await db.commit()
        print(f"updated {updated}/{len(skills)} skills")
        if unmapped:
            print(f"no curated category for: {unmapped}")


if __name__ == "__main__":
    asyncio.run(run())
