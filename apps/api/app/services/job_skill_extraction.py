import re

from app.models.skill import Skill

_MAX_WEIGHT = 10
# Treats a match as a whole term only when neither neighboring character is alphanumeric —
# `\b` alone doesn't behave predictably around skill names with symbols ("C++", "C#", ".NET"),
# so this is a deliberately simpler, more permissive boundary check instead. Known limitation:
# a bare "C" mention can still match inside "C++" (the char after "C" is "+", not alphanumeric,
# so the lookahead is satisfied) — accepted as a minor false-positive rate rather than building
# a real tokenizer for a first, deterministic pass.
_LEFT_BOUNDARY = r"(?<![A-Za-z0-9])"
_RIGHT_BOUNDARY = r"(?![A-Za-z0-9])"


def _term_pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"{_LEFT_BOUNDARY}{re.escape(term)}{_RIGHT_BOUNDARY}", re.IGNORECASE)


def extract_job_skills(*, title: str, description: str, skills: list[Skill]) -> dict[str, int]:
    """Deterministic keyword/synonym matcher against the shared skill taxonomy — no LLM call,
    same "LLMs reason, code decides" precedent as `app/services/job_matching.py`/`skill_gap.py`.
    Scans `title`+`description` for each skill's `name` and `synonyms`, case-insensitively,
    matching whole terms only (see `_BOUNDARY`). Returns `{skill_id: weight}` for skills found at
    least once, `weight` capped at `_MAX_WEIGHT` and based on how many times any of the skill's
    terms appear — a title mention counts the same as a description mention; this doesn't try to
    distinguish "required" from "nice to have" text, so every match backs `JobSkill(is_required=
    True)` (the caller's job, not this function's).
    """
    haystack = f"{title}\n{description}"
    matches: dict[str, int] = {}
    for skill in skills:
        terms = [skill.name, *(skill.synonyms or [])]
        count = sum(len(_term_pattern(term).findall(haystack)) for term in terms if term)
        if count > 0:
            matches[str(skill.id)] = min(_MAX_WEIGHT, count)
    return matches
