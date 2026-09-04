"""Manual interview-evaluation harness (docs/AI_ARCHITECTURE.md §9, Phase 11) — a directional,
mechanically-checkable proxy for `app/ai/interview_evaluation.py::evaluate_answer`, not a claim
about rubric/feedback quality (which would need an LLM-as-judge — same scope boundary
`rag_cases.json`/`run_eval.py` already draw for their own class of check). Makes real LLM calls,
so it needs a real provider API key — not run in CI, same "real model runs stay manual" precedent
as `run_eval.py` and `ml/`'s training scripts (docs/ROADMAP.md Phase 8).

One metric: for each (mode, question) case, does `correctness_score` rank a strong answer above a
weak answer above an off-topic answer? This only checks that scoring is directional — it says
nothing about whether the *feedback text* is well-written or the exact scores are "correct" in any
absolute sense. A second, simpler check confirms `feedback` is always non-empty.

Run from apps/api with the venv active (or `docker exec careerai-api-1 python -m
app.ai.evaluation.run_interview_eval`):

    python -m app.ai.evaluation.run_interview_eval
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from app.ai.interview_evaluation import evaluate_answer
from app.models.interview import InterviewMode

_CASES_PATH = Path(__file__).parent / "interview_cases.json"


@dataclass(frozen=True)
class EvalCase:
    mode: InterviewMode
    question: str
    strong_answer: str
    weak_answer: str
    off_topic_answer: str


def _load_cases() -> list[EvalCase]:
    raw = json.loads(_CASES_PATH.read_text(encoding="utf-8"))
    return [
        EvalCase(
            mode=InterviewMode(c["mode"]),
            question=c["question"],
            strong_answer=c["answers"]["strong"],
            weak_answer=c["answers"]["weak"],
            off_topic_answer=c["answers"]["off_topic"],
        )
        for c in raw
    ]


async def _score(mode: InterviewMode, question: str, answer_text: str) -> tuple[float, str]:
    result, _ = await evaluate_answer(
        mode=mode, question_text=question, answer_text=answer_text, resume_context=None
    )
    return result.correctness_score, result.feedback


async def run() -> None:
    cases = _load_cases()
    ordering_hits = 0
    feedback_hits = 0

    for case in cases:
        strong_score, strong_feedback = await _score(case.mode, case.question, case.strong_answer)
        weak_score, weak_feedback = await _score(case.mode, case.question, case.weak_answer)
        off_topic_score, off_topic_feedback = await _score(
            case.mode, case.question, case.off_topic_answer
        )

        ordering_ok = strong_score > weak_score > off_topic_score
        feedback_ok = bool(strong_feedback and weak_feedback and off_topic_feedback)
        ordering_hits += ordering_ok
        feedback_hits += feedback_ok

        status = "PASS" if ordering_ok and feedback_ok else "FAIL"
        print(f"[{status}] {case.mode.value}: {case.question[:80]}")
        print(
            f"    strong={strong_score:.0f}  weak={weak_score:.0f}  off_topic={off_topic_score:.0f}"
        )
        if not ordering_ok:
            print("    ORDERING VIOLATION: expected strong > weak > off_topic")
        if not feedback_ok:
            print("    EMPTY FEEDBACK for at least one answer")

    total = len(cases)
    print(f"\nScoring ordering (strong > weak > off_topic): {ordering_hits}/{total}")
    print(f"Non-empty feedback: {feedback_hits}/{total}")


if __name__ == "__main__":
    asyncio.run(run())
