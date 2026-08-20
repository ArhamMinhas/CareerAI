import io
import re

from docx import Document
from pypdf import PdfReader

from app.models.resume import FileType

# Standard resume section headers — used for the deterministic ATS/structure sub-scores
# (docs/ML_PIPELINE.md §2.1), not for extraction itself (the LLM handles that).
SECTION_HEADERS = {
    "experience": [
        "experience",
        "work experience",
        "employment history",
        "professional experience",
    ],
    "education": ["education", "academic background"],
    "skills": ["skills", "technical skills", "core competencies"],
    "projects": ["projects", "personal projects", "portfolio"],
    "summary": ["summary", "objective", "profile"],
}


class UnsupportedFileError(Exception):
    pass


class TextExtractionError(Exception):
    """Raised when a file claims to be a PDF/DOCX but no text could be pulled from it — e.g. a
    scanned image PDF with no text layer. Distinct from `UnsupportedFileError` (wrong file type
    entirely) so the caller can give a more specific failure reason."""


def extract_text(content: bytes, file_type: FileType) -> str:
    if file_type == FileType.PDF:
        text = _extract_pdf_text(content)
    elif file_type == FileType.DOCX:
        text = _extract_docx_text(content)
    else:
        raise UnsupportedFileError(f"Unsupported file type: {file_type}")

    if not text.strip():
        raise TextExtractionError(
            "No extractable text found — this may be a scanned/image-only document."
        )
    return text


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx_text(content: bytes) -> str:
    document = Document(io.BytesIO(content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def detect_sections(text: str) -> set[str]:
    """Which of the standard resume sections have a recognizable header present. A cheap,
    dependency-free stand-in for the spaCy-based NLP pass docs/AI_ARCHITECTURE.md describes —
    regex/keyword matching on header lines, not a trained model, per the "baseline first"
    principle in docs/ML_PIPELINE.md §1."""
    lower_lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    found: set[str] = set()
    for section, headers in SECTION_HEADERS.items():
        for line in lower_lines:
            # A header line is short (not a paragraph that happens to mention "education") and
            # starts with one of the known phrases.
            if len(line) < 40 and any(line.startswith(h) for h in headers):
                found.add(section)
                break
    return found


_BULLET_METRIC_RE = re.compile(r"\d")


def quantification_ratio(bullets: list[str]) -> float:
    """Fraction of bullets containing a number — feeds `achievements`/`experience`
    (docs/ML_PIPELINE.md §2.1's own note on what quantification means here)."""
    if not bullets:
        return 0.0
    with_numbers = sum(1 for b in bullets if _BULLET_METRIC_RE.search(b))
    return with_numbers / len(bullets)
