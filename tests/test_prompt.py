"""Tests for prompt.py.

build_prompt() needs no AI, so these run instantly and offline.

Run with:  python -m pytest -v
"""

from prompt import build_prompt


def test_prompt_contains_both_documents():
    """The resume text and job description both appear in the finished prompt."""
    prompt = build_prompt("Developed a Python app.", "Junior Python Developer")

    assert "Developed a Python app." in prompt
    assert "Junior Python Developer" in prompt


def test_prompt_has_no_unfilled_placeholders():
    """Every placeholder in the template is filled in."""
    prompt = build_prompt("Developed a Python app.", "Junior Python Developer")

    assert "{job_description}" not in prompt
    assert "{resume_text}" not in prompt


def test_resume_with_braces_does_not_crash():
    """Braces in the resume text are kept as they are, not treated as placeholders."""
    prompt = build_prompt("Developed a {Python} app.", "Junior Python Developer")

    assert "Developed a {Python} app." in prompt
    assert "Junior Python Developer" in prompt
