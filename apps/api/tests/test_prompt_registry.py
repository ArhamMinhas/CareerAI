import pytest

from app.ai.prompts.registry import PromptNotFoundError, load_prompt


def test_load_prompt_reads_resume_extraction_v1() -> None:
    prompt = load_prompt("resume_extraction", "v1")
    assert prompt.name == "resume_extraction"
    assert prompt.version == "v1"
    # The metadata header above the `---` separator must not leak into the system text sent
    # to the model.
    assert "Output schema" not in prompt.system
    assert "extract structured data from resume text" in prompt.system


def test_load_prompt_is_cached() -> None:
    assert load_prompt("resume_extraction", "v1") is load_prompt("resume_extraction", "v1")


def test_load_prompt_raises_for_missing_file() -> None:
    with pytest.raises(PromptNotFoundError):
        load_prompt("does_not_exist", "v1")
