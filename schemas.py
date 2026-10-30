"""Pydantic models describing the AI's analysis of a resume against a job description.

The AI's reply is validated against these models before the app uses it, so a
reply with a missing, invalid or unexpected field is rejected instead of shown
to the user. The models don't depend on any particular AI provider.
"""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class MatchStatus(str, Enum):
    """How well the resume evidence supports a requirement."""

    STRONG_EVIDENCE = "strong_evidence"
    PARTIAL_EVIDENCE = "partial_evidence"
    NOT_IDENTIFIED = "not_identified"
    NEEDS_REVIEW = "needs_review"


class RequirementPriority(str, Enum):
    """How important the job description says a requirement is."""

    REQUIRED = "required"
    PREFERRED = "preferred"
    UNSPECIFIED = "unspecified"


class RequirementMatch(BaseModel):
    """The analysis of one job requirement against the resume."""

    # Reject fields the AI wasn't asked for
    model_config = ConfigDict(extra="forbid")

    # The descriptions are sent to the AI with the schema, so they double as instructions
    requirement: str = Field(
        description="One specific requirement taken from the job description."
    )

    priority: RequirementPriority = Field(
        description=(
            "The priority stated by the job description's own wording. "
            "Use 'unspecified' when the wording does not make it clear."
        )
    )

    status: MatchStatus = Field(
        description="How well the resume evidence supports this requirement."
    )

    resume_evidence: list[str] = Field(
        default_factory=list,
        description=(
            "Exact quotations copied from the resume that support the assessment. "
            "Never paraphrase. Use an empty list when no relevant evidence was identified."
        ),
    )

    reasoning: str = Field(
        description=(
            "What the evidence establishes and what it does not. "
            "Never say the candidate lacks a skill; say it was not identified in the resume."
        )
    )

    # None when no action is needed
    suggestion: str | None = Field(
        default=None,
        description=(
            "An actionable recommendation based on this assessment. "
            "Never invent skills, experience or achievements the resume does not show."
        ),
    )


class ResumeAnalysis(BaseModel):
    """The complete analysis report for one resume and one job description."""

    # Reject fields the AI wasn't asked for
    model_config = ConfigDict(extra="forbid")

    job_title: str | None = Field(
        default=None,
        description="The title of the position being analyzed, or null if it can't be identified.",
    )

    summary: str = Field(
        description=(
            "A concise overview of the main findings. "
            "Do not give a percentage match or predict hiring outcomes."
        )
    )

    # A report with no requirements means the analysis failed, so it's rejected
    requirements: list[RequirementMatch] = Field(
        min_length=1,
        description=(
            "Every distinct requirement in the job description, each assessed separately. "
            "Include requirements with no resume evidence."
        ),
    )

    strengths: list[str] = Field(
        default_factory=list,
        description="The most relevant strengths that the resume explicitly supports.",
    )

    improvement_priorities: list[str] = Field(
        default_factory=list,
        description="The most important resume improvements, each following from the assessments above.",
    )
