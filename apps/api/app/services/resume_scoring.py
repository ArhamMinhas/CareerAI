"""Deterministic resume scoring — docs/ML_PIPELINE.md §2.1. No model, no LLM call: every
sub-score is a named rule over the structured extraction, so it's reproducible and auditable
(spec §54's "baseline first" principle). Weights live here as named constants, not admin-
editable yet (ML_PIPELINE.md notes that as a later, Phase-13 upgrade)."""

from app.schemas.resume import ResumeExtraction, ScoreBreakdown, SubScore
from app.services.resume_parsing import quantification_ratio

WEIGHTS = {
    "ats_compatibility": 0.15,
    "skills": 0.20,
    "experience": 0.15,
    "projects": 0.15,
    "education": 0.10,
    "achievements": 0.10,
    "keywords": 0.10,
    "structure": 0.05,
}

_CORE_SECTIONS = ("experience", "education", "skills")
_ALL_SECTIONS = ("summary", "experience", "education", "skills", "projects")


def _score_ats_compatibility(text: str, sections: set[str]) -> SubScore:
    length_score = min(len(text) / 1500, 1.0) * 40
    found_core = [s for s in _CORE_SECTIONS if s in sections]
    section_score = (len(found_core) / len(_CORE_SECTIONS)) * 60
    score = round(length_score + section_score, 1)
    missing = [s for s in _CORE_SECTIONS if s not in sections]
    evidence = [f"Detected sections: {', '.join(found_core) or 'none'}"]
    if missing:
        evidence.append(f"Missing standard headers: {', '.join(missing)}")
    return SubScore(
        score=score,
        explanation="Based on extracted text length and presence of standard section headers "
        "an ATS parser would look for.",
        evidence=evidence,
    )


def _score_skills(extraction: ResumeExtraction) -> SubScore:
    count = len(extraction.skills)
    if count == 0:
        score = 0.0
    elif count <= 3:
        score = 40.0
    elif count <= 7:
        score = 70.0
    elif count <= 14:
        score = 90.0
    else:
        score = 100.0
    return SubScore(
        score=score,
        explanation=f"{count} distinct skill{'s' if count != 1 else ''} identified in the resume.",
        evidence=extraction.skills[:15],
    )


def _score_experience(extraction: ResumeExtraction) -> SubScore:
    count = len(extraction.experience)
    base = {0: 0.0, 1: 50.0, 2: 75.0}.get(count, 90.0)
    all_bullets = [b for entry in extraction.experience for b in entry.bullets]
    quant = quantification_ratio(all_bullets)
    score = round(min(base + quant * 10, 100.0), 1)
    evidence = [f"{count} role{'s' if count != 1 else ''} listed"]
    if all_bullets:
        evidence.append(f"{round(quant * 100)}% of bullet points include a quantified metric")
    return SubScore(
        score=score,
        explanation="Based on the number of roles listed and how many achievement bullets "
        "include a measurable result.",
        evidence=evidence,
    )


def _score_projects(extraction: ResumeExtraction) -> SubScore:
    count = len(extraction.projects)
    base = {0: 30.0, 1: 60.0, 2: 80.0}.get(count, 100.0)
    with_links = sum(1 for p in extraction.projects if p.url)
    evidence = [f"{count} project{'s' if count != 1 else ''} listed"]
    if with_links:
        evidence.append(f"{with_links} include a live/repo link")
    return SubScore(
        score=base,
        explanation="Based on the number of projects listed and whether they link to a "
        "live demo or repository.",
        evidence=evidence,
    )


def _score_education(extraction: ResumeExtraction) -> SubScore:
    if not extraction.education:
        return SubScore(
            score=30.0,
            explanation="No education entries found — not disqualifying, but most ATS "
            "parsers expect at least one.",
            evidence=[],
        )
    complete = [e for e in extraction.education if e.institution and e.degree]
    score = 100.0 if len(complete) >= 2 else 80.0 if complete else 60.0
    count = len(extraction.education)
    evidence = [f"{count} entr{'y' if count == 1 else 'ies'} found"]
    return SubScore(
        score=score,
        explanation="Based on whether education entries include both an institution and a degree.",
        evidence=evidence,
    )


def _score_achievements(extraction: ResumeExtraction) -> SubScore:
    all_bullets = [b for entry in extraction.experience for b in entry.bullets]
    ratio = quantification_ratio(all_bullets)
    score = round(ratio * 100, 1)
    return SubScore(
        score=score,
        explanation="Percentage of experience bullet points that include a quantified "
        "result (a number, percentage, or measurable outcome).",
        evidence=[f"{round(ratio * 100)}% of {len(all_bullets)} bullet points are quantified"]
        if all_bullets
        else ["No bullet points found to evaluate"],
    )


def _score_keywords(extraction: ResumeExtraction) -> SubScore:
    skill_score = min(len(extraction.skills) / 12, 1.0) * 80
    cert_bonus = min(len(extraction.certifications), 2) * 10
    score = round(min(skill_score + cert_bonus, 100.0), 1)
    evidence = [f"{len(extraction.skills)} recognized skill keywords"]
    if extraction.certifications:
        evidence.append(f"{len(extraction.certifications)} certification(s) listed")
    return SubScore(
        score=score,
        explanation="Based on the breadth of recognized skill and certification keywords found.",
        evidence=evidence,
    )


def _score_structure(sections: set[str]) -> SubScore:
    found = [s for s in _ALL_SECTIONS if s in sections]
    score = round((len(found) / len(_ALL_SECTIONS)) * 100, 1)
    missing = [s for s in _ALL_SECTIONS if s not in sections]
    evidence = [f"Sections found: {', '.join(found) or 'none'}"]
    if missing:
        evidence.append(f"Sections not detected: {', '.join(missing)}")
    return SubScore(
        score=score,
        explanation="Based on how many of the standard resume sections have a recognizable header.",
        evidence=evidence,
    )


def compute_score_breakdown(
    extraction: ResumeExtraction, raw_text: str, sections: set[str]
) -> ScoreBreakdown:
    return ScoreBreakdown(
        ats_compatibility=_score_ats_compatibility(raw_text, sections),
        skills=_score_skills(extraction),
        experience=_score_experience(extraction),
        projects=_score_projects(extraction),
        education=_score_education(extraction),
        achievements=_score_achievements(extraction),
        keywords=_score_keywords(extraction),
        structure=_score_structure(sections),
    )


def compute_overall_score(breakdown: ScoreBreakdown) -> float:
    total = sum(getattr(breakdown, field).score * weight for field, weight in WEIGHTS.items())
    return round(total, 2)
