from app.schemas.resume import (
    ExtractedEducation,
    ExtractedExperience,
    ExtractedProject,
    ResumeExtraction,
)
from app.services.resume_scoring import WEIGHTS, compute_overall_score, compute_score_breakdown


def test_weights_sum_to_one() -> None:
    assert round(sum(WEIGHTS.values()), 6) == 1.0


def test_empty_extraction_scores_low() -> None:
    extraction = ResumeExtraction()
    breakdown = compute_score_breakdown(extraction, raw_text="", sections=set())
    overall = compute_overall_score(breakdown)

    assert breakdown.skills.score == 0
    assert breakdown.experience.score == 0
    assert overall < 30


def test_rich_extraction_scores_high() -> None:
    extraction = ResumeExtraction(
        full_name="Ada Lovelace",
        email="ada@example.com",
        skills=[
            "Python",
            "SQL",
            "React",
            "TypeScript",
            "Machine Learning",
            "Docker",
            "Kubernetes",
            "AWS",
            "FastAPI",
            "PostgreSQL",
            "RAG",
            "PyTorch",
            "Next.js",
            "NLP",
            "System Design",
        ],
        experience=[
            ExtractedExperience(
                company="Acme Corp",
                title="Senior Engineer",
                start_date="2021-01",
                end_date=None,
                bullets=[
                    "Reduced API latency by 40% through query optimization",
                    "Led a team of 5 engineers to ship a new billing platform",
                    "Increased test coverage from 60% to 95%",
                ],
            ),
            ExtractedExperience(company="Beta Inc", title="Engineer", start_date="2018-01"),
        ],
        education=[
            ExtractedEducation(institution="MIT", degree="BSc Computer Science"),
        ],
        projects=[
            ExtractedProject(title="CareerAI", url="https://example.com"),
            ExtractedProject(title="Side Project", url="https://github.com/x/y"),
        ],
        certifications=["AWS Certified Solutions Architect"],
    )
    sections = {"summary", "experience", "education", "skills", "projects"}
    breakdown = compute_score_breakdown(extraction, raw_text="x" * 2000, sections=sections)
    overall = compute_overall_score(breakdown)

    assert breakdown.skills.score == 100
    assert breakdown.structure.score == 100
    assert overall > 70


def test_every_sub_score_has_an_explanation() -> None:
    breakdown = compute_score_breakdown(ResumeExtraction(), raw_text="", sections=set())
    for field in WEIGHTS:
        sub_score = getattr(breakdown, field)
        assert sub_score.explanation
        assert 0 <= sub_score.score <= 100
