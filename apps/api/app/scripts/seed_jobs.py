"""Seeds example companies and job postings for Phase 7 (docs/ROADMAP.md Phase 7). There's no
real job-board scraper or external job API integration in this project — this script is the
phase's "ingestion" path, standing in for one, same documented scope deviation as Phase 6
seeding the career-path catalog by hand instead of importing an external taxonomy.

Idempotent — upserts by company slug / (company, title) rather than inserting duplicates, safe
to re-run after editing the content below. Computes a real embedding per job (title +
description) via `embed_text`, so `Job.embedding`-based semantic search/matching works against
this seed data without any extra backfill step.

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.scripts.seed_jobs`):

    python -m app.scripts.seed_jobs
"""

import asyncio
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal, engine
from app.models.company import Company
from app.models.job import Job, JobSkill
from app.services.embeddings import embed_text
from app.services.skill_taxonomy import get_or_create_skill


@dataclass(frozen=True)
class SeedCompany:
    slug: str
    name: str
    industry: str
    description: str


@dataclass(frozen=True)
class SeedJobSkill:
    name: str
    weight: int  # 1-10, same scale as CareerPathSkill.weight
    is_required: bool = True


@dataclass(frozen=True)
class SeedJob:
    company_slug: str
    title: str
    description: str
    seniority_level: str
    employment_type: str
    location: str | None
    remote: bool
    salary_min: float | None
    salary_max: float | None
    currency: str | None
    skills: list[SeedJobSkill] = field(default_factory=list)


COMPANIES: list[SeedCompany] = [
    SeedCompany(
        slug="northwind-ai",
        name="Northwind AI",
        industry="Artificial Intelligence",
        description=(
            "Builds retrieval-augmented generation and agentic-workflow infrastructure for "
            "enterprise customers automating knowledge-heavy back-office work."
        ),
    ),
    SeedCompany(
        slug="riverstone-cloud",
        name="Riverstone Cloud",
        industry="Cloud Infrastructure",
        description=(
            "A infrastructure-as-a-service provider offering managed Kubernetes, observability, "
            "and CI/CD tooling for mid-market engineering teams."
        ),
    ),
    SeedCompany(
        slug="ledgerline-fintech",
        name="Ledgerline",
        industry="Financial Technology",
        description=(
            "Builds embedded payments and ledger infrastructure for marketplaces and vertical "
            "SaaS platforms."
        ),
    ),
    SeedCompany(
        slug="atlashealth",
        name="AtlasHealth",
        industry="Healthcare Technology",
        description=(
            "A patient-scheduling and clinical-workflow platform used by outpatient clinics "
            "across North America."
        ),
    ),
    SeedCompany(
        slug="fieldnote-labs",
        name="Fieldnote Labs",
        industry="Developer Tools",
        description=(
            "Makes collaborative data-science notebooks and experiment-tracking tools for "
            "applied ML teams."
        ),
    ),
]

JOBS: list[SeedJob] = [
    SeedJob(
        company_slug="northwind-ai",
        title="AI Engineer",
        description=(
            "Design and operate retrieval-augmented generation pipelines that power our "
            "customers' document-automation workflows. You'll own the full path from ingestion "
            "and chunking through embedding, retrieval, and structured-output validation, with a "
            "strong focus on latency and cost budgets in production. Day to day: build and "
            "maintain FastAPI services calling multiple LLM providers with fallback and "
            "caching, tune retrieval quality against real customer documents, and instrument "
            "everything so regressions in answer quality show up before customers notice."
        ),
        seniority_level="Mid-level",
        employment_type="full-time",
        location="Remote (US)",
        remote=True,
        salary_min=130000,
        salary_max=175000,
        currency="USD",
        skills=[
            SeedJobSkill("Python", 10, True),
            SeedJobSkill("Prompt Engineering", 9, True),
            SeedJobSkill("Vector Databases", 8, True),
            SeedJobSkill("REST APIs", 7, True),
            SeedJobSkill("Machine Learning", 7, False),
            SeedJobSkill("Docker", 5, False),
        ],
    ),
    SeedJob(
        company_slug="northwind-ai",
        title="Senior Machine Learning Engineer",
        description=(
            "Lead the design of our document-embedding and reranking pipeline, including "
            "evaluating and fine-tuning open-weight embedding models against domain-specific "
            "customer data. You'll partner closely with the AI Engineering team on retrieval "
            "quality and mentor two mid-level engineers."
        ),
        seniority_level="Senior",
        employment_type="full-time",
        location="New York, NY",
        remote=False,
        salary_min=170000,
        salary_max=220000,
        currency="USD",
        skills=[
            SeedJobSkill("Machine Learning", 10, True),
            SeedJobSkill("Python", 9, True),
            SeedJobSkill("Natural Language Processing", 8, True),
            SeedJobSkill("System Design", 7, False),
            SeedJobSkill("SQL", 5, False),
        ],
    ),
    SeedJob(
        company_slug="riverstone-cloud",
        title="DevOps Engineer",
        description=(
            "Operate the managed Kubernetes control plane our customers run their production "
            "workloads on. You'll build Terraform modules for customer-facing infrastructure, "
            "improve our CI/CD pipeline's reliability, and be part of the on-call rotation "
            "responding to platform incidents."
        ),
        seniority_level="Mid-level",
        employment_type="full-time",
        location="Austin, TX",
        remote=True,
        salary_min=125000,
        salary_max=160000,
        currency="USD",
        skills=[
            SeedJobSkill("Kubernetes", 10, True),
            SeedJobSkill("Docker", 9, True),
            SeedJobSkill("AWS", 8, True),
            SeedJobSkill("CI/CD", 8, True),
            SeedJobSkill("System Design", 6, False),
        ],
    ),
    SeedJob(
        company_slug="riverstone-cloud",
        title="Backend Engineer",
        description=(
            "Build the API layer and control-plane services behind our managed Kubernetes "
            "product. Most of the work is Go services talking to Postgres and our internal "
            "provisioning queue, with a strong emphasis on backward-compatible API design since "
            "customers script against these endpoints directly."
        ),
        seniority_level="Entry",
        employment_type="full-time",
        location="Austin, TX",
        remote=True,
        salary_min=95000,
        salary_max=125000,
        currency="USD",
        skills=[
            SeedJobSkill("REST APIs", 9, True),
            SeedJobSkill("SQL", 8, True),
            SeedJobSkill("System Design", 6, False),
            SeedJobSkill("Docker", 5, False),
            SeedJobSkill("Git", 4, False),
        ],
    ),
    SeedJob(
        company_slug="ledgerline-fintech",
        title="Full-Stack Engineer",
        description=(
            "Ship customer-facing features across our ledger dashboard: a React/TypeScript "
            "frontend backed by a Python API. You'll work closely with product on payments "
            "reconciliation and dispute-management workflows, where correctness and auditability "
            "matter as much as speed."
        ),
        seniority_level="Mid-level",
        employment_type="full-time",
        location="Chicago, IL",
        remote=False,
        salary_min=120000,
        salary_max=155000,
        currency="USD",
        skills=[
            SeedJobSkill("React", 9, True),
            SeedJobSkill("TypeScript", 8, True),
            SeedJobSkill("Python", 7, True),
            SeedJobSkill("SQL", 6, False),
            SeedJobSkill("REST APIs", 6, False),
        ],
    ),
    SeedJob(
        company_slug="ledgerline-fintech",
        title="Data Scientist",
        description=(
            "Build the fraud-risk scoring models behind our payments platform. You'll own "
            "feature engineering against transaction data, model evaluation against a shifting "
            "fraud landscape, and clear communication of tradeoffs (false-positive rate vs. "
            "recall) to a non-technical risk team."
        ),
        seniority_level="Senior",
        employment_type="full-time",
        location="Remote (US)",
        remote=True,
        salary_min=150000,
        salary_max=190000,
        currency="USD",
        skills=[
            SeedJobSkill("Machine Learning", 9, True),
            SeedJobSkill("Python", 9, True),
            SeedJobSkill("SQL", 8, True),
            SeedJobSkill("Statistics", 8, True),
            SeedJobSkill("Data Visualization", 5, False),
        ],
    ),
    SeedJob(
        company_slug="atlashealth",
        title="Frontend Engineer",
        description=(
            "Own the clinic-facing scheduling calendar — a dense, accessibility-critical React "
            "application used by front-desk staff hundreds of times a day. You'll work directly "
            "with clinic operations staff to understand real workflow friction and turn it into "
            "concrete UI improvements."
        ),
        seniority_level="Entry",
        employment_type="full-time",
        location="Remote (US)",
        remote=True,
        salary_min=90000,
        salary_max=115000,
        currency="USD",
        skills=[
            SeedJobSkill("React", 9, True),
            SeedJobSkill("TypeScript", 8, True),
            SeedJobSkill("Accessibility", 6, False),
            SeedJobSkill("CSS", 5, False),
        ],
    ),
    SeedJob(
        company_slug="atlashealth",
        title="Product Manager, Clinical Workflows",
        description=(
            "Own the roadmap for our clinical-intake and scheduling product line. You'll spend "
            "real time shadowing clinic staff, translate what you learn into prioritized specs, "
            "and partner with engineering and design to ship changes that measurably reduce "
            "front-desk workload."
        ),
        seniority_level="Mid-level",
        employment_type="full-time",
        location="Boston, MA",
        remote=False,
        salary_min=115000,
        salary_max=150000,
        currency="USD",
        skills=[
            SeedJobSkill("Product Sense", 9, True),
            SeedJobSkill("Stakeholder Management", 8, True),
            SeedJobSkill("Data Analysis", 6, False),
            SeedJobSkill("SQL", 4, False),
        ],
    ),
    SeedJob(
        company_slug="fieldnote-labs",
        title="Backend Engineer, Notebook Platform",
        description=(
            "Build the execution-kernel orchestration layer behind our collaborative notebook "
            "product — the service responsible for spinning up isolated, GPU-backed Python "
            "kernels per user session and keeping them synchronized across collaborators in "
            "real time."
        ),
        seniority_level="Mid-level",
        employment_type="full-time",
        location="Remote (US)",
        remote=True,
        salary_min=135000,
        salary_max=170000,
        currency="USD",
        skills=[
            SeedJobSkill("Python", 9, True),
            SeedJobSkill("Docker", 8, True),
            SeedJobSkill("Kubernetes", 7, True),
            SeedJobSkill("System Design", 7, False),
            SeedJobSkill("REST APIs", 6, False),
        ],
    ),
    SeedJob(
        company_slug="fieldnote-labs",
        title="Machine Learning Engineer",
        description=(
            "Build the experiment-tracking and model-comparison features data scientists use "
            "daily inside our notebook product — ingesting training metrics at scale, powering "
            "fast comparison queries across thousands of runs, and surfacing regressions "
            "automatically."
        ),
        seniority_level="Senior",
        employment_type="full-time",
        location="San Francisco, CA",
        remote=True,
        salary_min=160000,
        salary_max=205000,
        currency="USD",
        skills=[
            SeedJobSkill("Machine Learning", 8, True),
            SeedJobSkill("Python", 9, True),
            SeedJobSkill("SQL", 6, True),
            SeedJobSkill("System Design", 7, False),
            SeedJobSkill("Data Visualization", 5, False),
        ],
    ),
]


async def _get_or_create_company(db: AsyncSession, seed: SeedCompany) -> Company:
    result = await db.execute(select(Company).where(Company.slug == seed.slug))
    company = result.scalar_one_or_none()
    if company is None:
        company = Company(slug=seed.slug)
        db.add(company)

    company.name = seed.name
    company.industry = seed.industry
    company.description = seed.description
    await db.flush()
    return company


async def _get_or_create_job(db: AsyncSession, company: Company, seed: SeedJob) -> Job:
    result = await db.execute(
        select(Job).where(Job.company_id == company.id, Job.title == seed.title)
    )
    job = result.scalar_one_or_none()
    if job is None:
        job = Job(company_id=company.id, title=seed.title)
        db.add(job)

    job.description = seed.description
    job.seniority_level = seed.seniority_level
    job.employment_type = seed.employment_type
    job.location = seed.location
    job.remote = seed.remote
    job.salary_min = seed.salary_min
    job.salary_max = seed.salary_max
    job.currency = seed.currency
    job.is_active = True
    job.embedding = await embed_text(f"{seed.title} at {company.name}\n\n{seed.description}")
    await db.flush()
    return job


async def _upsert_job_skill(db: AsyncSession, job: Job, seed_skill: SeedJobSkill) -> None:
    skill = await get_or_create_skill(db, seed_skill.name)
    result = await db.execute(
        select(JobSkill).where(JobSkill.job_id == job.id, JobSkill.skill_id == skill.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = JobSkill(job_id=job.id, skill_id=skill.id)
        db.add(row)
    row.is_required = seed_skill.is_required
    row.weight = seed_skill.weight


async def seed() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        companies_by_slug: dict[str, Company] = {}
        for seed_company in COMPANIES:
            company = await _get_or_create_company(db, seed_company)
            companies_by_slug[seed_company.slug] = company
            await db.commit()
            print(f"seeded company: {seed_company.slug}")

        for seed_job in JOBS:
            company = companies_by_slug[seed_job.company_slug]
            job = await _get_or_create_job(db, company, seed_job)
            for seed_skill in seed_job.skills:
                await _upsert_job_skill(db, job, seed_skill)
            await db.commit()
            print(f"seeded job: {seed_job.title} @ {seed_job.company_slug}")


if __name__ == "__main__":
    asyncio.run(seed())
