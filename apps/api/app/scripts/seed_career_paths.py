"""Seeds the curated career-path catalog the Skill Gap Engine diffs against and the public
`/careers`/`/careers/[slug]` pages render (docs/ROADMAP.md Phase 6). Idempotent — safe to
re-run any time the content below changes; upserts by slug/name rather than inserting
duplicates. Also backfills `seo_summary`/`synonyms`/`embedding` for the subset of skills common
enough across these paths to warrant curated `/skills/[slug]` content.

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.scripts.seed_career_paths`):

    python -m app.scripts.seed_career_paths
"""

import asyncio
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal, engine
from app.models.career_path import CareerPath, CareerPathSkill
from app.models.skill import Skill
from app.services.embeddings import embed_text
from app.services.skill_taxonomy import get_or_create_skill


@dataclass(frozen=True)
class SeedSkill:
    name: str
    weight: int  # 1-10, how heavily this skill counts toward gap priority for this path
    is_core: bool = False  # non-negotiable for the role — see app/services/skill_gap.py


@dataclass(frozen=True)
class SeedCareerPath:
    slug: str
    title: str
    summary: str
    description_md: str
    related_job_titles: list[str]
    skills: list[SeedSkill] = field(default_factory=list)


CAREER_PATHS: list[SeedCareerPath] = [
    SeedCareerPath(
        slug="ai-engineer",
        title="AI Engineer",
        summary=(
            "Builds production systems powered by large language models and other generative "
            "AI — retrieval pipelines, agentic workflows, and the infrastructure that makes "
            "them reliable, observable, and cost-controlled."
        ),
        description_md=(
            "An AI Engineer sits between traditional software engineering and machine "
            "learning: most of the day-to-day work is building and operating systems that call "
            "LLM APIs, not training models from scratch. That means strong fundamentals in "
            "backend engineering — APIs, databases, async programming — combined with the "
            "newer discipline of prompt engineering, retrieval-augmented generation, and vector "
            "search.\n\n"
            'The hardest problems in this role are rarely "can the model do this" and almost '
            'always "how do we make it reliable, fast, and affordable at scale": structured-'
            "output validation, caching, fallback providers, and cost/latency budgets matter as "
            "much as prompt quality. A strong AI Engineer treats the LLM as one component in a "
            "larger deterministic system, not the whole system."
        ),
        related_job_titles=[
            "AI Engineer",
            "Applied AI Engineer",
            "Generative AI Engineer",
            "LLM Engineer",
        ],
        skills=[
            SeedSkill("Python", 10, is_core=True),
            SeedSkill("Machine Learning", 8, is_core=True),
            SeedSkill("Prompt Engineering", 9, is_core=True),
            SeedSkill("Vector Databases", 8, is_core=True),
            SeedSkill("REST APIs", 7),
            SeedSkill("SQL", 6),
            SeedSkill("Docker", 6),
            SeedSkill("System Design", 7),
            SeedSkill("Natural Language Processing", 7),
            SeedSkill("MLOps", 5),
            SeedSkill("AWS", 5),
            SeedSkill("Git", 4),
        ],
    ),
    SeedCareerPath(
        slug="machine-learning-engineer",
        title="Machine Learning Engineer",
        summary=(
            "Designs, trains, and deploys machine learning models — the discipline that turns "
            "a promising notebook experiment into a reliable, monitored production system."
        ),
        description_md=(
            "Machine Learning Engineers own the full model lifecycle: framing a business "
            "problem as a learning task, building the training pipeline, evaluating against a "
            "real baseline, and shipping it behind an API that the rest of the product can "
            "call. Strong Python and statistics fundamentals are table stakes; what separates "
            "a good ML Engineer is comfort with the *engineering* half of the job — "
            "reproducible training runs, feature stores, model versioning, and monitoring for "
            "drift once a model is live.\n\n"
            "Unlike a pure Data Scientist role, the emphasis here is on production reliability "
            "over exploratory analysis: a model that's 2% less accurate but reproducible, "
            "fast, and monitorable usually beats a marginally better one nobody can safely "
            "retrain or debug."
        ),
        related_job_titles=[
            "Machine Learning Engineer",
            "ML Engineer",
            "Applied Scientist",
        ],
        skills=[
            SeedSkill("Python", 10, is_core=True),
            SeedSkill("Machine Learning", 10, is_core=True),
            SeedSkill("Deep Learning", 8, is_core=True),
            SeedSkill("PyTorch", 7),
            SeedSkill("Statistics", 8, is_core=True),
            SeedSkill("Pandas", 7),
            SeedSkill("Scikit-learn", 6),
            SeedSkill("MLOps", 7),
            SeedSkill("SQL", 6),
            SeedSkill("Docker", 5),
            SeedSkill("AWS", 5),
            SeedSkill("Data Visualization", 4),
        ],
    ),
    SeedCareerPath(
        slug="data-scientist",
        title="Data Scientist",
        summary=(
            "Turns raw data into decisions — statistical analysis, experimentation, and "
            "predictive modeling in service of a specific business question, not modeling for "
            "its own sake."
        ),
        description_md=(
            "A Data Scientist's core loop is: get a question from the business, find or build "
            "the data to answer it, choose the right statistical or ML method (often a simple "
            "one), and communicate the result clearly enough that someone acts on it. The "
            "communication half is not optional — an analysis nobody understands or trusts "
            "changes nothing.\n\n"
            "Day to day this looks like SQL against a warehouse, exploratory analysis in "
            "Python/pandas, running and interpreting A/B tests, and building the occasional "
            "predictive model. Deep production-engineering skills matter less here than for an "
            "ML Engineer; rigor about causality, sample size, and honest uncertainty matters "
            "more."
        ),
        related_job_titles=[
            "Data Scientist",
            "Data Analyst",
            "Quantitative Analyst",
        ],
        skills=[
            SeedSkill("SQL", 10, is_core=True),
            SeedSkill("Python", 9, is_core=True),
            SeedSkill("Statistics", 10, is_core=True),
            SeedSkill("Pandas", 7),
            SeedSkill("A/B Testing", 8, is_core=True),
            SeedSkill("Data Visualization", 7),
            SeedSkill("Machine Learning", 6),
            SeedSkill("Tableau", 5),
            SeedSkill("Communication", 6),
            SeedSkill("NumPy", 4),
        ],
    ),
    SeedCareerPath(
        slug="backend-engineer",
        title="Backend Engineer",
        summary=(
            "Designs and builds the server-side systems, APIs, and data layer that power an "
            "application — correctness, performance, and reliability under real traffic."
        ),
        description_md=(
            "Backend engineering is fundamentally about managing state correctly under "
            "concurrency: databases, caches, queues, and the APIs that sit in front of them. "
            "The job spans designing a data model that won't need a painful migration in six "
            "months, writing APIs that fail predictably, and understanding exactly what "
            "happens when two requests hit the same row at once.\n\n"
            "Strong backend engineers are comfortable reading a query plan, reasoning about "
            "transaction isolation, and designing for horizontal scale before it's strictly "
            "necessary — not by over-engineering everything, but by knowing which decisions "
            "are cheap to defer and which aren't."
        ),
        related_job_titles=[
            "Backend Engineer",
            "Backend Developer",
            "Software Engineer, Backend",
        ],
        skills=[
            SeedSkill("Python", 8, is_core=True),
            SeedSkill("SQL", 9, is_core=True),
            SeedSkill("PostgreSQL", 8, is_core=True),
            SeedSkill("REST APIs", 9, is_core=True),
            SeedSkill("System Design", 9, is_core=True),
            SeedSkill("Docker", 7),
            SeedSkill("Git", 5),
            SeedSkill("Data Structures & Algorithms", 7),
            SeedSkill("Testing (Unit/E2E)", 6),
            SeedSkill("CI/CD", 5),
            SeedSkill("AWS", 5),
            SeedSkill("Kubernetes", 4),
        ],
    ),
    SeedCareerPath(
        slug="frontend-engineer",
        title="Frontend Engineer",
        summary=(
            "Builds the interfaces users actually touch — fast, accessible, visually polished "
            "web applications, and the component architecture that keeps them maintainable."
        ),
        description_md=(
            "Frontend engineering has grown far beyond markup and styling: modern frontend "
            "work means component architecture, client/server state management, rendering "
            "strategy (static vs. server vs. client), and performance budgets measured in "
            'Core Web Vitals, not just "feels fast."\n\n'
            "A strong Frontend Engineer thinks about the user first — accessibility, "
            "responsive layout, perceived performance — while also owning the engineering "
            "concerns that make a codebase survive past its first few features: typed "
            "component contracts, test coverage on interaction logic, and a build pipeline "
            "that doesn't regress silently."
        ),
        related_job_titles=[
            "Frontend Engineer",
            "Frontend Developer",
            "UI Engineer",
        ],
        skills=[
            SeedSkill("JavaScript", 9, is_core=True),
            SeedSkill("TypeScript", 8, is_core=True),
            SeedSkill("React", 9, is_core=True),
            SeedSkill("Next.js", 7),
            SeedSkill("HTML/CSS", 8, is_core=True),
            SeedSkill("Accessibility (a11y)", 6),
            SeedSkill("Performance Optimization", 6),
            SeedSkill("Testing (Unit/E2E)", 5),
            SeedSkill("REST APIs", 5),
            SeedSkill("Git", 4),
            SeedSkill("GraphQL", 4),
        ],
    ),
    SeedCareerPath(
        slug="full-stack-engineer",
        title="Full-Stack Engineer",
        summary=(
            "Owns a feature end to end — database schema, API, and the UI on top of it — and "
            "moves fluidly across the whole stack rather than specializing in one layer."
        ),
        description_md=(
            "Full-stack engineers are generalists by design: the value isn't being the best at "
            "any one layer, it's being able to take a feature from a database migration "
            "through an API to a polished UI without needing three separate handoffs. That "
            "makes the role especially common at smaller teams and startups, where the "
            "overhead of specialist silos isn't worth it yet.\n\n"
            "The skill profile below blends backend and frontend fundamentals rather than "
            "going deep on either — real full-stack roles vary a lot in exactly where the line "
            'sits, so treat "core" here as the non-negotiable minimum on both sides, not an '
            "exhaustive list."
        ),
        related_job_titles=[
            "Full-Stack Engineer",
            "Full-Stack Developer",
            "Software Engineer",
        ],
        skills=[
            SeedSkill("JavaScript", 8, is_core=True),
            SeedSkill("TypeScript", 7),
            SeedSkill("React", 7, is_core=True),
            SeedSkill("Node.js", 7),
            SeedSkill("Python", 6),
            SeedSkill("SQL", 7, is_core=True),
            SeedSkill("PostgreSQL", 6),
            SeedSkill("REST APIs", 8, is_core=True),
            SeedSkill("Docker", 5),
            SeedSkill("Git", 5),
            SeedSkill("System Design", 6),
        ],
    ),
    SeedCareerPath(
        slug="devops-engineer",
        title="DevOps Engineer",
        summary=(
            "Builds and operates the infrastructure, CI/CD pipelines, and observability "
            "systems that let every other engineer ship safely and often."
        ),
        description_md=(
            "DevOps work is infrastructure as a product: the pipelines, environments, and "
            "monitoring dashboards other engineers depend on daily. The job blends software "
            "engineering (most modern infrastructure is defined in code) with systems "
            "knowledge — networking, Linux internals, container orchestration — and a strong "
            "incident-response mindset.\n\n"
            "The best DevOps engineers optimize for reducing the *cost of change* everywhere "
            "else in the org: a deploy that takes one click and rolls back automatically on a "
            "bad health check removes an entire category of fear from every other team's "
            "release process."
        ),
        related_job_titles=[
            "DevOps Engineer",
            "Site Reliability Engineer",
            "Platform Engineer",
        ],
        skills=[
            SeedSkill("Linux", 9, is_core=True),
            SeedSkill("Docker", 9, is_core=True),
            SeedSkill("Kubernetes", 8, is_core=True),
            SeedSkill("Terraform", 7),
            SeedSkill("CI/CD", 9, is_core=True),
            SeedSkill("AWS", 8, is_core=True),
            SeedSkill("Networking", 6),
            SeedSkill("System Design", 6),
            SeedSkill("Python", 5),
            SeedSkill("Git", 4),
        ],
    ),
    SeedCareerPath(
        slug="product-manager",
        title="Product Manager",
        summary=(
            "Decides what gets built and why — translating user needs and business goals into "
            "a prioritized roadmap the engineering and design teams can execute against."
        ),
        description_md=(
            "Product Management is the least technical-skills-heavy path in this catalog and "
            "the most people-and-judgment-heavy: the job is making good prioritization calls "
            "with incomplete information, then getting a cross-functional team genuinely "
            "aligned behind them. Technical fluency still matters — enough to have a real "
            "conversation with engineering about tradeoffs — but depth of coding skill is "
            "not the bar.\n\n"
            "Strong PMs are distinguished by product sense (a calibrated intuition for what's "
            "actually worth building), rigorous user research, and comfort making a defensible "
            "call under ambiguity rather than waiting for perfect data that will never arrive."
        ),
        related_job_titles=[
            "Product Manager",
            "Senior Product Manager",
            "Technical Product Manager",
        ],
        skills=[
            SeedSkill("Product Sense", 9, is_core=True),
            SeedSkill("Roadmapping", 8, is_core=True),
            SeedSkill("User Research", 8, is_core=True),
            SeedSkill("Stakeholder Management", 8, is_core=True),
            SeedSkill("Communication", 9, is_core=True),
            SeedSkill("A/B Testing", 6),
            SeedSkill("Data Visualization", 5),
            SeedSkill("Agile/Scrum", 6),
            SeedSkill("SQL", 4),
        ],
    ),
]

# Curated `/skills/[slug]` content for the subset of skills common/central enough to warrant
# it — most skills in the taxonomy (long-tail resume-extracted/manually-added ones) stay
# without a `seo_summary`, which the model/schemas already treat as a normal, expected state.
SKILL_CONTENT: dict[str, tuple[str, list[str]]] = {
    "Python": (
        "A general-purpose, dynamically-typed language that dominates backend engineering, "
        "data science, and machine learning thanks to its readable syntax and enormous "
        "ecosystem (Django/FastAPI for web APIs, pandas/NumPy for data, PyTorch/TensorFlow "
        "for deep learning). Its combination of a low learning curve and production-grade "
        "libraries makes it the most commonly required skill across AI, ML, and backend "
        "roles.",
        ["Python3", "Py"],
    ),
    "Machine Learning": (
        "The discipline of building systems that learn patterns from data rather than "
        "following explicitly programmed rules — spanning classical algorithms (regression, "
        "decision trees, clustering) through deep learning. Distinct from generic 'AI' "
        "buzzword usage: ML specifically means a trained model whose behavior comes from "
        "data, evaluated against a measurable metric.",
        ["ML"],
    ),
    "Deep Learning": (
        "A subfield of machine learning using multi-layer neural networks, responsible for "
        "most recent breakthroughs in computer vision, NLP, and generative AI. Requires "
        "comfort with linear algebra, gradient-based optimization, and a framework like "
        "PyTorch or TensorFlow to define and train models at scale.",
        ["Neural Networks", "DL"],
    ),
    "SQL": (
        "The standard language for querying and manipulating relational databases — "
        "essential for nearly every data-adjacent and backend role. Strong SQL means more "
        "than basic SELECTs: window functions, query optimization, and understanding how "
        "indexes and execution plans affect performance at scale.",
        ["Structured Query Language"],
    ),
    "REST APIs": (
        "The dominant architectural style for web APIs, built on HTTP verbs and resource-"
        "oriented URLs. Designing a good REST API means predictable status codes, "
        "consistent pagination/error shapes, and versioning that doesn't break existing "
        "clients — the interface contract every frontend and integration depends on.",
        ["RESTful APIs", "REST"],
    ),
    "System Design": (
        "The practice of architecting software systems that meet real-world requirements for "
        "scale, reliability, and maintainability — choosing between a monolith and "
        "microservices, designing for horizontal scale, and reasoning about consistency "
        "tradeoffs (per the CAP theorem) under real traffic and failure conditions.",
        ["Systems Design", "Software Architecture"],
    ),
    "Docker": (
        "A containerization platform that packages an application with its dependencies into "
        "a single portable unit — the standard way modern teams ship consistent environments "
        "from a developer's laptop through CI to production, and the foundation Kubernetes "
        "orchestrates on top of.",
        ["Containers", "Containerization"],
    ),
    "Kubernetes": (
        "An open-source system for automating deployment, scaling, and management of "
        "containerized applications across a cluster of machines — the industry-standard way "
        "to run Docker containers reliably in production at scale, handling failover, "
        "rolling updates, and resource scheduling.",
        ["K8s"],
    ),
    "AWS": (
        "Amazon Web Services, the largest cloud infrastructure provider — compute (EC2/"
        "Lambda), storage (S3), managed databases (RDS), and hundreds of other services that "
        "let teams run production systems without owning physical hardware. The most widely "
        "required cloud platform skill across backend, DevOps, and ML roles.",
        ["Amazon Web Services"],
    ),
    "TypeScript": (
        "A statically-typed superset of JavaScript that catches a large class of bugs at "
        "compile time rather than in production. Now the default choice for serious frontend "
        "and Node.js codebases, since types make large component/API surfaces far safer to "
        "refactor.",
        ["TS"],
    ),
    "React": (
        "A component-based JavaScript library for building user interfaces, and the most "
        "widely used frontend framework in the industry. Its declarative model — describing "
        "what the UI should look like for a given state, not how to mutate the DOM — "
        "underlies most modern frontend architecture, including Next.js.",
        ["React.js", "ReactJS"],
    ),
    "Next.js": (
        "A React framework that adds server-side rendering, static generation, file-based "
        "routing, and API routes on top of React — the standard choice for production React "
        "applications that need real SEO, fast initial loads, and a full-stack story without "
        "a separate backend framework.",
        ["NextJS"],
    ),
    "PostgreSQL": (
        "An open-source relational database known for standards compliance, extensibility "
        "(including native vector search via pgvector), and reliability under real production "
        "load. The default relational database choice for new backend systems that need "
        "correctness guarantees a NoSQL store won't provide.",
        ["Postgres"],
    ),
    "Statistics": (
        "The mathematical foundation behind sound data analysis and machine learning — "
        "hypothesis testing, confidence intervals, distributions, and regression. Without it, "
        "it's easy to mistake noise for a real effect, which is exactly what separates a "
        "trustworthy analysis from a misleading one.",
        ["Statistical Analysis"],
    ),
    "A/B Testing": (
        "A controlled-experiment method for comparing two versions of a product to determine "
        "which performs better on a defined metric, using randomization to isolate causal "
        "effect from confounding factors. The primary tool product and data teams use to "
        "validate a change actually works before rolling it out fully.",
        ["Split Testing", "Experimentation"],
    ),
    "Prompt Engineering": (
        "The practice of designing inputs to large language models to reliably produce a "
        "desired output — system instructions, few-shot examples, structured-output schemas, "
        "and iterative refinement based on observed failure modes. A core skill for anyone "
        "building on top of LLM APIs rather than training models from scratch.",
        ["Prompt Design"],
    ),
    "Vector Databases": (
        "Specialized databases (or database extensions like pgvector) optimized for storing "
        "and searching high-dimensional embedding vectors by similarity — the retrieval layer "
        "behind semantic search and retrieval-augmented generation (RAG) systems.",
        ["Vector Search", "Vector Store"],
    ),
    "MLOps": (
        "The set of practices for reliably deploying, monitoring, and retraining machine "
        "learning models in production — versioning datasets and models, detecting drift, "
        "and automating retraining pipelines so a model stays accurate as real-world data "
        "shifts away from its training distribution.",
        ["ML Operations"],
    ),
    "Product Sense": (
        "A calibrated intuition for what's worth building — grounded in user needs, business "
        "constraints, and market context rather than just feature requests. The hardest "
        "product-management skill to teach directly, usually built through repeated exposure "
        "to real user feedback and outcomes.",
        [],
    ),
    "Git": (
        "The distributed version control system used by nearly all modern software teams to "
        "track changes, collaborate without overwriting each other's work, and review code "
        "before it merges. Baseline fluency (branching, merging, resolving conflicts) is "
        "assumed in essentially every engineering role.",
        ["Version Control"],
    ),
}


async def _get_or_create_career_path(db: AsyncSession, seed: SeedCareerPath) -> CareerPath:
    result = await db.execute(select(CareerPath).where(CareerPath.slug == seed.slug))
    career_path = result.scalar_one_or_none()
    if career_path is None:
        career_path = CareerPath(slug=seed.slug)
        db.add(career_path)

    career_path.title = seed.title
    career_path.summary = seed.summary
    career_path.description_md = seed.description_md
    career_path.related_job_titles = seed.related_job_titles
    career_path.published = True
    career_path.embedding = await embed_text(f"{seed.title}\n\n{seed.summary}")
    await db.flush()
    return career_path


async def _upsert_career_path_skill(
    db: AsyncSession, career_path: CareerPath, skill: Skill, seed_skill: SeedSkill
) -> None:
    result = await db.execute(
        select(CareerPathSkill).where(
            CareerPathSkill.career_path_id == career_path.id,
            CareerPathSkill.skill_id == skill.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = CareerPathSkill(career_path_id=career_path.id, skill_id=skill.id)
        db.add(row)
    row.weight = seed_skill.weight
    row.is_core = seed_skill.is_core


async def _backfill_skill_content(db: AsyncSession) -> None:
    for name, (seo_summary, synonyms) in SKILL_CONTENT.items():
        skill = await get_or_create_skill(db, name)
        skill.seo_summary = seo_summary
        skill.synonyms = synonyms or None
        skill.embedding = await embed_text(f"{skill.name}: {seo_summary}")
        await db.flush()


async def seed() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        for seed_path in CAREER_PATHS:
            career_path = await _get_or_create_career_path(db, seed_path)
            for seed_skill in seed_path.skills:
                skill = await get_or_create_skill(db, seed_skill.name)
                await _upsert_career_path_skill(db, career_path, skill, seed_skill)
            await db.commit()
            print(f"seeded career path: {seed_path.slug}")

        await _backfill_skill_content(db)
        await db.commit()
        print(f"backfilled seo content for {len(SKILL_CONTENT)} skills")


if __name__ == "__main__":
    asyncio.run(seed())
