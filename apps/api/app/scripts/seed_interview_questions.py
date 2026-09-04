"""Seeds `interview_question_bank` — the curated reference content
`app/services/interviews.py::select_next_question` picks from (docs/ROADMAP.md Phase 11). Real,
authored questions: 5 per mode across all 6 modes, each with a real category tag so the
selection algorithm's category-rotation logic has real, distinct categories to rotate through.

Idempotent — safe to re-run any time this content changes; upserts by `(mode, question_text)`
rather than inserting duplicates. Each question gets a real embedding
(`app/services/embeddings.py::embed_text`) used to rank selection against a resolved target
role's `CareerPath.embedding`.

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.scripts.seed_interview_questions`):

    python -m app.scripts.seed_interview_questions
"""

import asyncio
from dataclasses import dataclass

from sqlalchemy import select

from app.core.db import AsyncSessionLocal, engine
from app.models.interview import InterviewMode, InterviewQuestionBank
from app.services.embeddings import embed_text


@dataclass(frozen=True)
class SeedQuestion:
    mode: InterviewMode
    category: str
    question_text: str


QUESTIONS: list[SeedQuestion] = [
    # --- technical ---------------------------------------------------------------------------
    SeedQuestion(
        InterviewMode.TECHNICAL,
        "algorithms",
        "Given an array of integers, how would you find two numbers that add up to a specific "
        "target? Walk through your approach and its time complexity.",
    ),
    SeedQuestion(
        InterviewMode.TECHNICAL,
        "data-structures",
        "When would you choose a hash map over a balanced binary search tree, and vice versa?",
    ),
    SeedQuestion(
        InterviewMode.TECHNICAL,
        "debugging",
        "Describe a time you tracked down a hard-to-reproduce bug. What was your process?",
    ),
    SeedQuestion(
        InterviewMode.TECHNICAL,
        "code-quality",
        "What makes code 'maintainable' to you? Give a concrete example of a change you made to "
        "improve it.",
    ),
    SeedQuestion(
        InterviewMode.TECHNICAL,
        "testing",
        "How do you decide what to unit test versus integration test in a typical feature you "
        "build?",
    ),
    # --- behavioral ---------------------------------------------------------------------------
    SeedQuestion(
        InterviewMode.BEHAVIORAL,
        "conflict",
        "Tell me about a time you disagreed with a teammate on a technical decision. How did you "
        "resolve it?",
    ),
    SeedQuestion(
        InterviewMode.BEHAVIORAL,
        "leadership",
        "Describe a situation where you had to lead a project or initiative without formal "
        "authority.",
    ),
    SeedQuestion(
        InterviewMode.BEHAVIORAL,
        "failure",
        "Tell me about a project that didn't go as planned. What did you learn?",
    ),
    SeedQuestion(
        InterviewMode.BEHAVIORAL,
        "teamwork",
        "Describe a time you had to rely heavily on someone else's work to succeed. How did you "
        "build that trust?",
    ),
    SeedQuestion(
        InterviewMode.BEHAVIORAL,
        "prioritization",
        "Tell me about a time you had to choose between two competing priorities with limited "
        "time. How did you decide?",
    ),
    # --- hr -------------------------------------------------------------------------------------
    SeedQuestion(
        InterviewMode.HR,
        "motivation",
        "Why are you interested in this role, specifically, and not just any similar role?",
    ),
    SeedQuestion(
        InterviewMode.HR,
        "career-goals",
        "Where do you want to be in your career three years from now, and how does this role fit "
        "into that?",
    ),
    SeedQuestion(
        InterviewMode.HR,
        "culture-fit",
        "Describe the kind of team environment where you do your best work.",
    ),
    SeedQuestion(
        InterviewMode.HR,
        "compensation",
        "How do you think about evaluating a job offer beyond just the salary number?",
    ),
    SeedQuestion(
        InterviewMode.HR,
        "self-improvement",
        "What's a skill you're actively working to improve right now, and what are you doing "
        "about it?",
    ),
    # --- system_design --------------------------------------------------------------------------
    SeedQuestion(
        InterviewMode.SYSTEM_DESIGN,
        "scalability",
        "How would you design a URL-shortening service that needs to handle 100 million requests "
        "a day?",
    ),
    SeedQuestion(
        InterviewMode.SYSTEM_DESIGN,
        "tradeoffs",
        "Walk me through the trade-offs between a monolithic and a microservices architecture for "
        "a mid-sized product.",
    ),
    SeedQuestion(
        InterviewMode.SYSTEM_DESIGN,
        "data-modeling",
        "How would you design the data model for a ride-sharing app's core matching feature?",
    ),
    SeedQuestion(
        InterviewMode.SYSTEM_DESIGN,
        "reliability",
        "How would you design a system so that a single failing dependency doesn't take down the "
        "whole product?",
    ),
    SeedQuestion(
        InterviewMode.SYSTEM_DESIGN,
        "caching",
        "When and where would you introduce caching into a typical web application, and what are "
        "the risks?",
    ),
    # --- ml -------------------------------------------------------------------------------------
    SeedQuestion(
        InterviewMode.ML,
        "problem-framing",
        "How would you frame 'predict which users will cancel their subscription' as a machine "
        "learning problem?",
    ),
    SeedQuestion(
        InterviewMode.ML,
        "model-evaluation",
        "A classifier has 95% accuracy on a fraud-detection dataset. Why might that number be "
        "misleading, and what would you look at instead?",
    ),
    SeedQuestion(
        InterviewMode.ML,
        "feature-engineering",
        "How do you decide which features to include when you have dozens of candidate features "
        "and limited training data?",
    ),
    SeedQuestion(
        InterviewMode.ML,
        "ml-ops",
        "How would you detect that a deployed model's performance is degrading in production?",
    ),
    SeedQuestion(
        InterviewMode.ML,
        "overfitting",
        "How do you recognize and address overfitting during model development?",
    ),
    # --- data_science --------------------------------------------------------------------------
    SeedQuestion(
        InterviewMode.DATA_SCIENCE,
        "experimentation",
        "How would you design an A/B test to measure whether a new checkout flow increases "
        "conversion?",
    ),
    SeedQuestion(
        InterviewMode.DATA_SCIENCE,
        "statistics",
        "Explain what a p-value actually means to someone without a statistics background.",
    ),
    SeedQuestion(
        InterviewMode.DATA_SCIENCE,
        "data-quality",
        "How do you handle a dataset where you suspect a meaningful chunk of the data is wrong or "
        "missing?",
    ),
    SeedQuestion(
        InterviewMode.DATA_SCIENCE,
        "communication",
        "Describe a time you had to explain a data-driven finding to a non-technical stakeholder "
        "who disagreed with it.",
    ),
    SeedQuestion(
        InterviewMode.DATA_SCIENCE,
        "causality",
        "What's the difference between correlation and causation, and how would you try to "
        "establish causality with observational data?",
    ),
]


async def seed() -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as db:
        count = 0
        for seed_question in QUESTIONS:
            result = await db.execute(
                select(InterviewQuestionBank).where(
                    InterviewQuestionBank.mode == seed_question.mode,
                    InterviewQuestionBank.question_text == seed_question.question_text,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = InterviewQuestionBank(
                    mode=seed_question.mode, question_text=seed_question.question_text
                )
                db.add(row)
            row.category = seed_question.category
            row.embedding = await embed_text(
                f"{seed_question.category}: {seed_question.question_text}"
            )
            await db.flush()
            count += 1
        await db.commit()
        print(
            f"seeded {count} interview question(s) across {len({q.mode for q in QUESTIONS})} modes"
        )


if __name__ == "__main__":
    asyncio.run(seed())
