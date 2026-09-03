"""Seeds the curated knowledge-base articles that back the public `/resources`/`/resources/[slug]`
pages and the RAG pipeline's retrieval corpus (docs/ROADMAP.md Phase 9). Idempotent — safe to
re-run any time the content below changes; upserts by slug rather than inserting duplicates, and
re-ingests each resource's `kb_chunks` on every run so an edited article's chunks/embeddings stay
in sync with `body_md`.

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.scripts.seed_resources`):

    python -m app.scripts.seed_resources
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.kb_ingest import ingest_resource
from app.core.db import AsyncSessionLocal, engine
from app.models.resource import Resource
from app.services.embeddings import embed_text


@dataclass(frozen=True)
class SeedResource:
    slug: str
    title: str
    summary: str
    body_md: str
    category: str
    tags: list[str] = field(default_factory=list)


RESOURCES: list[SeedResource] = [
    SeedResource(
        slug="ats-resume-tips",
        title="How to Write a Resume That Passes an ATS",
        summary=(
            "Most resumes are screened by an applicant tracking system before a human ever "
            "sees them. Here's what actually matters for getting through — and what's a myth."
        ),
        category="resume",
        tags=["resume", "ats", "job-search"],
        body_md=(
            "An applicant tracking system (ATS) is software that employers use to collect, "
            "parse, and filter resumes before a recruiter ever looks at one. If your resume is "
            "hard for that software to parse correctly, a human may never see it at all — "
            "regardless of how qualified you actually are. Understanding what an ATS does, and "
            "doesn't do, is the difference between a resume that gets read and one that gets "
            "silently dropped.\n\n"
            "## What an ATS actually does\n\n"
            "Contrary to the popular myth, most modern ATS platforms don't use a hidden "
            "keyword-matching score that auto-rejects resumes below a threshold. What they "
            "actually do is parse your resume into structured fields — name, contact info, work "
            "history, education, skills — and make that structured data searchable and "
            "filterable for a recruiter. If the parser misreads your resume (for example, "
            "pulling your job title into the company field, or missing your most recent role "
            "entirely), a recruiter searching for your exact qualifications may never find you, "
            "even though the words are technically on the page.\n\n"
            "## Formatting that parses cleanly\n\n"
            "Use a single-column layout. Multi-column resumes and resumes built with text boxes "
            "or tables often parse out of order — an ATS reading left-to-right, top-to-bottom "
            "can interleave your left column's skills section with your right column's work "
            'history, scrambling both. Stick to standard section headings ("Work Experience," '
            '"Education," "Skills") rather than creative alternatives ("My Journey") — '
            "parsers are tuned to recognize the standard ones. Save as a .docx or a text-based "
            "PDF, never a PDF that's actually a scanned image, which most parsers can't read at "
            "all.\n\n"
            "## Keywords still matter, but not the way people think\n\n"
            "Recruiters search their ATS by keyword to shortlist candidates for a specific role "
            '— so if the job description says "SQL" and your resume only says "databases," '
            "you may not surface in that search even though you're qualified. The fix isn't to "
            "stuff your resume with every keyword from the posting; it's to mirror the specific "
            "terms the posting uses for skills you genuinely have. If a posting says "
            '"Kubernetes" and you have that exact experience, write "Kubernetes," not just '
            '"container orchestration."\n\n'
            "## What doesn't matter\n\n"
            "Font choice, as long as it's a standard, readable one, has no effect on parsing. "
            "Objective statements are optional and rarely help. A resume doesn't need to be "
            "exactly one page — what matters is that every line earns its place, not the page "
            "count itself. Spend your effort on clean structure and honest keyword alignment, "
            "not on chasing rumored ATS tricks that have little real effect."
        ),
    ),
    SeedResource(
        slug="quantify-resume-bullets",
        title="How to Quantify Your Resume Bullet Points",
        summary=(
            '"Responsible for improving performance" tells a recruiter nothing. Here\'s a '
            "repeatable method for turning vague resume bullets into specific, credible ones."
        ),
        category="resume",
        tags=["resume", "writing"],
        body_md=(
            "A resume bullet's job is to convince a stranger, in under five seconds, that you "
            'did something that mattered. "Responsible for X" or "helped with Y" doesn\'t do '
            "that — it describes a duty, not an outcome, and it reads identically whether you "
            "did the bare minimum or transformed the team. Quantifying your bullets is the "
            "single highest-leverage edit most resumes need.\n\n"
            "## The problem with duty-based bullets\n\n"
            '"Responsible for managing the deployment pipeline" could describe someone who '
            "kept a stable system running quietly for years, or someone who inherited a broken "
            "pipeline and fixed nothing. A reader can't tell the difference, so duty-based "
            "language gets discounted by default — recruiters have learned that most resumes "
            "overstate vague responsibilities, so vague language reads as weaker evidence, not "
            "neutral.\n\n"
            "## A simple structure: action, object, result\n\n"
            "A strong bullet names the action you took, what you took it on, and the measurable "
            'result. "Rebuilt the deployment pipeline, cutting release time from 45 minutes to '
            "6\" tells a complete story in one line: what changed, and by how much. If you can't "
            "find a number, look for a proxy — team size affected, frequency, scope, or a "
            "before/after comparison — rather than defaulting back to duty language.\n\n"
            "## Where to actually find the numbers\n\n"
            "Most people underestimate how much quantifiable detail they already have access "
            "to. Check ticket/issue trackers for counts of what you shipped or resolved. Check "
            "analytics or monitoring dashboards for before/after metrics on anything you "
            "changed. Ask a manager or teammate for team size, budget, or user-count context you "
            "may not have tracked yourself. When a precise number genuinely isn't available, an "
            'honest, clearly-scoped estimate ("an estimated 30% reduction") is far better than '
            "no number at all — but never fabricate a figure you can't stand behind if asked "
            "about it in an interview.\n\n"
            "## Common mistakes\n\n"
            'Don\'t quantify effort instead of outcome — "wrote 500 lines of code" says nothing '
            "about whether that code mattered. Don't stack unrelated numbers into one bullet "
            "just to look busy; one clear result beats three vague ones. And don't force a "
            "number where there genuinely isn't a meaningful one — an honest qualitative result, "
            "written specifically, still beats a padded, meaningless statistic."
        ),
    ),
    SeedResource(
        slug="closing-skill-gaps",
        title="Closing a Skill Gap: A Practical Framework",
        summary=(
            "Identifying that you're missing a skill is the easy part. Here's a practical, "
            "prioritized way to actually close the gap without wasting months on the wrong one."
        ),
        category="skills",
        tags=["skills", "career-growth"],
        body_md=(
            "Once you know which skills separate you from a target role — CareerAI's skill-gap "
            "engine will show you that breakdown directly — the harder question is what to "
            "actually do about it. Not every gap deserves equal attention, and not every gap "
            "closes the same way.\n\n"
            "## Prioritize core skills over broad coverage\n\n"
            "A required-skill profile usually marks a handful of skills as non-negotiable "
            '"core" requirements for the role, with the rest weighted by how much they matter. '
            "Closing a missing core skill is almost always higher-leverage than adding "
            "incremental depth to skills you're already adequate in — a hiring manager will "
            "notice one glaring gap in a must-have skill far more than they'll notice you're at "
            "70% instead of 90% on a nice-to-have. Start there.\n\n"
            "## Match the learning method to the skill type\n\n"
            "Not every skill closes the same way. A conceptual skill (statistics, system design "
            "fundamentals) often closes fastest through structured study — a course or a book, "
            "followed by deliberately applying the concept somewhere real. A tool-based skill "
            "(a specific framework, a cloud platform) closes fastest through direct, hands-on "
            "use — build something small but real with it, rather than only reading "
            "documentation. A soft skill (stakeholder communication, leading a project) rarely "
            "closes through reading at all; it closes through repeated, reflected-on practice in "
            "real situations, ideally with feedback from someone more experienced.\n\n"
            "## Build proof, not just familiarity\n\n"
            '"I took a course on X" is weak evidence to a future interviewer; "I used X to '
            'build/ship/fix Y" is strong evidence. Wherever possible, turn a learning plan into '
            "a small real project or a real contribution at your current job — something you can "
            "concretely describe and quantify later (see CareerAI's guide on quantifying resume "
            "bullets), not just a certificate. Proof of applied skill is what actually moves a "
            "hiring decision, not proof of exposure.\n\n"
            "## Re-check the gap, don't assume it's closed\n\n"
            "Skill growth is easy to overestimate from the inside — a few weeks of study can "
            "feel like mastery long before it actually is. Re-run a skill-gap comparison "
            "periodically rather than assuming a gap is closed once you've put in effort; it's "
            "a cheap, honest check against a real target-role profile, and it tells you whether "
            "to keep going deeper or move on to the next-highest-priority gap."
        ),
    ),
    SeedResource(
        slug="behavioral-interview-prep",
        title="How to Prepare for a Behavioral Interview",
        summary=(
            '"Tell me about a time when..." questions reward preparation more than almost any '
            "other interview format. Here's a structure that holds up under follow-up questions."
        ),
        category="interviewing",
        tags=["interviewing", "behavioral"],
        body_md=(
            'Behavioral interviews ask about specific past situations — "tell me about a time '
            'you disagreed with a teammate" — on the theory that past behavior predicts future '
            "behavior better than a hypothetical answer would. They reward real preparation more "
            "than almost any other interview format, because the difference between a vague "
            "answer and a specific, credible one is entirely about how well you've prepared your "
            "stories in advance.\n\n"
            "## Use a consistent structure: STAR\n\n"
            "Situation, Task, Action, Result. State the real context briefly (Situation), what "
            "you were specifically responsible for (Task), what you actually did — in enough "
            'detail that your individual contribution is clear, not just "we" (Action), and '
            "what happened as a result, ideally quantified (Result). Most weak answers fail at "
            "the Action step: they describe the team's actions in general rather than the "
            "candidate's specific decisions and behavior. An interviewer is evaluating you, not "
            "your team, so make your own role unambiguous.\n\n"
            "## Prepare a small story bank, not one story per question\n\n"
            "Rather than trying to guess every possible question, prepare 5-7 real stories that "
            "each cover a distinct theme — a conflict you navigated, a failure you recovered "
            "from, a time you influenced someone without authority, a project you led end to "
            "end, a time you changed your mind based on new information. Most behavioral "
            "questions map onto one of a small set of themes, so a well-chosen story bank covers "
            "far more questions than it looks like it should, and you won't be improvising a "
            "brand-new story under pressure.\n\n"
            "## Choose stories with a real, specific result\n\n"
            "A story where nothing was really at stake, or where the outcome is vague, is hard "
            "to tell convincingly no matter how well-structured the delivery is. Favor real "
            "situations with a concrete before/after, even if the result wasn't a total success "
            "— a well-told story about a real failure and what you learned from it is far more "
            "convincing than a manufactured success story that sounds rehearsed and generic.\n\n"
            "## Expect and welcome follow-up questions\n\n"
            'A strong interviewer will probe a vague part of your answer — "what exactly did '
            'you say to them?", "how did you know it worked?" A prepared, specific story '
            "survives this easily; a padded or exaggerated one usually falls apart under a "
            "second or third follow-up. Preparing real stories in specific detail, not just a "
            "rehearsed opening line, is what actually protects you here."
        ),
    ),
    SeedResource(
        slug="negotiating-job-offers",
        title="Negotiating a Job Offer: A Step-by-Step Guide",
        summary=(
            "Most candidates leave real money and better terms on the table simply by not "
            "asking. Here's a straightforward, low-risk process for negotiating an offer well."
        ),
        category="negotiation",
        tags=["negotiation", "compensation", "job-search"],
        body_md=(
            "Negotiating a job offer is one of the highest-leverage conversations in your entire "
            "career — a single conversation, typically twenty minutes long, that can meaningfully "
            "change your compensation for years. Most candidates under-negotiate not because "
            "they lack leverage, but because the process feels unfamiliar and uncomfortable. It "
            "doesn't have to be either.\n\n"
            "## Never negotiate against yourself\n\n"
            "Once you receive a written offer, respond with genuine enthusiasm for the role, "
            "then ask for a short amount of time to review it in full before responding with "
            "numbers. Don't counter on the spot in the same conversation the offer is delivered "
            "— you lose the chance to think clearly, and you signal that you'll accept whatever "
            "comes first. A simple \"Thank you — I'm excited about this. Can I take a couple of "
            'days to review the full offer?" is a completely normal, expected response, not an '
            "aggressive one.\n\n"
            "## Negotiate the whole package, not just base salary\n\n"
            "Base salary is the most visible number, but it's rarely the only lever available. "
            "Signing bonus, equity, start date, remote/hybrid flexibility, title, and reporting "
            "level can all be negotiated, and a company that has limited room on base salary "
            "(often due to internal pay bands) may have real flexibility elsewhere. Decide in "
            "advance which of these actually matter to you, rather than fixating on base salary "
            "alone.\n\n"
            "## Anchor with a real number, not a vague range\n\n"
            "When asked for a counter, give a specific number slightly above your real target, "
            "grounded in real market data for the role, level, and location — not an arbitrary "
            'aspirational figure. A vague range ("somewhere in the 120s to 150s") often gets '
            'anchored to its lower end; a specific number backed by a clear rationale ("based '
            'on market data for this role and level, I was targeting $X") is taken more '
            "seriously and is harder to lowball.\n\n"
            "## Get everything in writing before you resign your current role\n\n"
            "A verbal agreement over the phone is not a finalized offer. Wait for the updated, "
            "written offer letter reflecting every negotiated term before giving notice at a "
            "current job, and read it carefully against what was verbally agreed — details are "
            "sometimes lost or misremembered between a negotiation call and the final paperwork, "
            "and it's far easier to catch a discrepancy before you've already resigned than "
            "after."
        ),
    ),
]


async def _get_or_create_resource(db: AsyncSession, seed: SeedResource) -> Resource:
    result = await db.execute(select(Resource).where(Resource.slug == seed.slug))
    resource = result.scalar_one_or_none()
    is_new = resource is None
    if resource is None:
        resource = Resource(slug=seed.slug)
        db.add(resource)

    resource.title = seed.title
    resource.summary = seed.summary
    resource.body_md = seed.body_md
    resource.category = seed.category
    resource.tags = seed.tags or None
    resource.published = True
    if is_new:
        resource.published_at = datetime.now(UTC)
    resource.embedding = await embed_text(f"{seed.title}\n\n{seed.summary}")
    await db.flush()
    return resource


async def seed() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        for seed_resource in RESOURCES:
            resource = await _get_or_create_resource(db, seed_resource)
            chunks = await ingest_resource(db, resource)
            await db.commit()
            print(f"seeded resource: {seed_resource.slug} ({len(chunks)} chunks)")


if __name__ == "__main__":
    asyncio.run(seed())
