from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent
_BODY_SEPARATOR = "\n---\n"


@dataclass(frozen=True)
class Prompt:
    """A loaded, versioned prompt (docs/AI_ARCHITECTURE.md §4). `system` is the exact text sent
    as the model's system instructions — everything above the `---` separator in the source
    `.md` file is human-readable metadata (output schema, variables) and is not sent."""

    name: str
    version: str
    system: str


class PromptNotFoundError(Exception):
    pass


@lru_cache
def load_prompt(name: str, version: str) -> Prompt:
    """Prompts are versioned files, not inline strings (spec §52) — `(name, version)` is
    recorded on every `ai_conversations` row so a prompt regression traces back to the exact
    file that produced it. Cached: prompt files don't change at runtime."""
    path = _PROMPTS_DIR / name / f"{version}.md"
    if not path.exists():
        raise PromptNotFoundError(f"No prompt file at {path}")

    raw = path.read_text(encoding="utf-8")
    _, _, body = raw.partition(_BODY_SEPARATOR)
    system = (body or raw).strip()
    if not system:
        raise PromptNotFoundError(f"Prompt file at {path} has no system instructions.")

    return Prompt(name=name, version=version, system=system)
