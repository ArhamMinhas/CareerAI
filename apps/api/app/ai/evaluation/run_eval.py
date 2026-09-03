"""Manual RAG evaluation harness (docs/AI_ARCHITECTURE.md §9, Phase 9) — reports citation
accuracy and citation-marker groundedness against the seeded `resources` knowledge base
(app/scripts/seed_resources.py must have been run first). Makes real embedding + LLM calls, so
it needs a real provider API key and real seeded data — not run in CI, same "real model runs
stay manual" precedent as `ml/`'s training scripts (docs/ROADMAP.md Phase 8).

Two metrics, both honest proxies rather than a full factual-consistency check (which would need
an LLM-as-judge — out of scope for this harness):
- **Citation accuracy**: for a case with expected resources, did at least one expected slug
  appear in the returned citations? For a case expecting no confident answer (the knowledge base
  genuinely doesn't cover it), did the model correctly cite nothing / say so?
- **Citation-marker groundedness**: for a case with expected resources, did the answer actually
  contain a `[N]` citation marker — i.e. did the model follow the grounding instruction in
  `app/ai/prompts/rag_answer/v1.md`, not just happen to retrieve the right chunk?

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.ai.evaluation.run_eval`):

    python -m app.ai.evaluation.run_eval
"""

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag_answer import answer_question
from app.core.db import AsyncSessionLocal, engine

_CASES_PATH = Path(__file__).parent / "rag_cases.json"
_INSUFFICIENT_CONTEXT_MARKERS = ("doesn't cover", "does not cover", "no relevant", "not covered")
_CITATION_MARKER_RE = re.compile(r"\[\d+\]")


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_resource_slugs: list[str]  # empty means "expect no confident citation"


@dataclass(frozen=True)
class EvalResult:
    case: EvalCase
    answer: str
    cited_slugs: set[str]
    citation_correct: bool
    groundedness_ok: bool


def _load_cases() -> list[EvalCase]:
    raw = json.loads(_CASES_PATH.read_text(encoding="utf-8"))
    return [
        EvalCase(question=c["question"], expected_resource_slugs=c["expected_resource_slugs"])
        for c in raw
    ]


def _says_insufficient_context(answer: str) -> bool:
    lowered = answer.lower()
    return any(marker in lowered for marker in _INSUFFICIENT_CONTEXT_MARKERS)


async def _run_case(db: AsyncSession, case: EvalCase) -> EvalResult:
    answer, citations, _ = await answer_question(db, case.question)
    cited_slugs = {c.resource_slug for c in citations}

    if case.expected_resource_slugs:
        citation_correct = bool(cited_slugs & set(case.expected_resource_slugs))
        groundedness_ok = bool(_CITATION_MARKER_RE.search(answer))
    else:
        citation_correct = not cited_slugs or _says_insufficient_context(answer)
        groundedness_ok = _says_insufficient_context(answer)

    return EvalResult(
        case=case,
        answer=answer,
        cited_slugs=cited_slugs,
        citation_correct=citation_correct,
        groundedness_ok=groundedness_ok,
    )


async def run() -> None:
    await engine.dispose()
    cases = _load_cases()
    results: list[EvalResult] = []

    async with AsyncSessionLocal() as db:
        for case in cases:
            result = await _run_case(db, case)
            results.append(result)
            status = "PASS" if result.citation_correct and result.groundedness_ok else "FAIL"
            expected = case.expected_resource_slugs or "(none — insufficient context expected)"
            print(f"[{status}] {case.question}")
            print(f"    expected: {expected}")
            print(f"    cited: {sorted(result.cited_slugs) or '(none)'}")
            print(f"    answer: {result.answer[:200]}")

    total = len(results)
    citation_hits = sum(r.citation_correct for r in results)
    groundedness_hits = sum(r.groundedness_ok for r in results)
    print(f"\nCitation accuracy: {citation_hits}/{total}")
    print(f"Citation-marker groundedness: {groundedness_hits}/{total}")


if __name__ == "__main__":
    asyncio.run(run())
