"""Tests for schemas.py.

These check that the Pydantic models accept a valid analysis and reject
replies that are shaped wrongly, which is what protects the app from a bad AI response.
No AI is called; the test data is written by hand.

Run with:  python -m pytest -v
"""

import pytest
from pydantic import ValidationError
from schemas import MatchStatus, RequirementMatch, ResumeAnalysis


def make_valid_match():
    """Return a dict for one valid RequirementMatch. Tests change one field at a time."""
    return {
        "requirement": "REST API development",
        "priority": "required",
        "status": "partial_evidence",
        "resume_evidence": ["Developed a Python application that retrieves weather information from an external API."],
        "reasoning": "The resume shows consuming an API, not building one.",
        "suggestion": "If you have built API endpoints, describe that work.",
    }


def make_valid_analysis():
    """Return a dict for one valid ResumeAnalysis containing one match."""
    return {
        "job_title": "Junior Python Developer",
        "summary": "Evidence of Python development; REST API development is only partly shown.",
        "requirements": [make_valid_match()],
        "strengths": ["Python application development"],
        "improvement_priorities": ["Clarify API consumption vs API development"],
    }


def test_invalid_status_raises_validation_error():
    """A status outside MatchStatus is rejected."""
    data = make_valid_match()
    data["status"] = "supported"

    with pytest.raises(ValidationError, match="Input should be 'strong_evidence'"):
        RequirementMatch(**data)


def test_extra_field_raises_validation_error():
    """A field the model doesn't define is rejected, because of extra="forbid"."""
    data = make_valid_match()
    data["confidence"] = 98

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RequirementMatch(**data)


def test_valid_analysis_parses():
    """A complete, valid analysis is accepted, and its nested items become RequirementMatch objects."""
    analysis = ResumeAnalysis(**make_valid_analysis())

    assert analysis.job_title == "Junior Python Developer"
    assert len(analysis.requirements) == 1
    assert isinstance(analysis.requirements[0], RequirementMatch)


def test_valid_analysis_parses_from_json():
    """A JSON string, which is what the AI will actually send, is parsed and validated."""
    json_text = """
    {
        "summary": "Evidence of Python development.",
        "requirements": [
            {
                "requirement": "Python programming",
                "priority": "required",
                "status": "strong_evidence",
                "resume_evidence": ["Developed a Python application."],
                "reasoning": "The resume describes building a Python application."
            }
        ]
    }
    """
    analysis = ResumeAnalysis.model_validate_json(json_text)

    assert analysis.requirements[0].requirement == "Python programming"


def test_status_becomes_enum_member():
    """The status text from the AI's JSON is converted into a real MatchStatus member."""
    match = RequirementMatch(**make_valid_match())

    # "is", not "==": MatchStatus inherits from str, so the unconverted text would also pass "=="
    assert match.status is MatchStatus.PARTIAL_EVIDENCE


def test_invalid_priority_raises_validation_error():
    """A priority with the wrong capitalization is rejected, since enum values are case-sensitive."""
    data = make_valid_match()
    data["priority"] = "Preferred"

    with pytest.raises(ValidationError, match="Input should be 'required', 'preferred' or 'unspecified'"):
        RequirementMatch(**data)


def test_missing_reasoning_raises_validation_error():
    """A match without reasoning is rejected, because every assessment must explain itself."""
    data = make_valid_match()
    del data["reasoning"]

    with pytest.raises(ValidationError, match="Field required"):
        RequirementMatch(**data)


def test_empty_requirements_raises_validation_error():
    """An analysis with no requirements is rejected, because that means the analysis failed."""
    data = make_valid_analysis()
    data["requirements"] = []

    with pytest.raises(ValidationError, match="List should have at least 1 item"):
        ResumeAnalysis(**data)


def test_optional_fields_get_defaults():
    """Leaving out the optional fields gives an empty evidence list and no suggestion."""
    data = make_valid_match()
    del data["resume_evidence"]
    del data["suggestion"]

    match = RequirementMatch(**data)

    assert match.resume_evidence == []
    assert match.suggestion is None


def test_analysis_optional_fields_get_defaults():
    """An analysis with only summary and requirements gets defaults for everything else."""
    data = make_valid_analysis()
    del data["job_title"]
    del data["strengths"]
    del data["improvement_priorities"]

    analysis = ResumeAnalysis(**data)

    assert analysis.job_title is None
    assert analysis.strengths == []
    assert analysis.improvement_priorities == []