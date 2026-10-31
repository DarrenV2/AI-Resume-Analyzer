"""Send a resume and job description to Gemini and return the validated analysis.

All communication with the AI provider lives here, separate from the API
routes in main.py, so the analysis logic can be tested on its own
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from prompt import build_prompt
from schemas import ResumeAnalysis

# A "lite" model: in testing it gave the same verdicts as the bigger models, about 4x faster,
# and it was available while the larger Flash models were overloaded
GEMINI_MODEL = "gemini-3.5-flash-lite"
# The SDK has no timeout by default (it waits forever). In milliseconds; the SDK also sends
# it to Gemini as a deadline, and Gemini rejects any deadline under 10 s
GEMINI_TIMEOUT_MS = 60_000


class MissingAPIKeyError(Exception):
    """Raised when GEMINI_API_KEY is not set."""


def get_api_key() -> str:
    """Return the Gemini API key from the environment or the .env file.

    Raises:
        MissingAPIKeyError: GEMINI_API_KEY is missing or empty.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    # "not" catches both a missing variable (None) and an empty one ("")
    if not api_key:
        raise MissingAPIKeyError(
            "GEMINI_API_KEY is not set. Add it to the .env file in the project root."
        )
    return api_key


def analyze_resume(resume_text: str, job_description: str) -> ResumeAnalysis:
    """Send the resume and job description to Gemini and return the validated analysis.

    Args:
        resume_text: the text extracted from the resume.
        job_description: the job description pasted by the user.

    Returns:
        The analysis, validated against the ResumeAnalysis model.

    Raises:
        MissingAPIKeyError: GEMINI_API_KEY is missing or empty.
        google.genai.errors.APIError: the Gemini request failed (e.g. 503 when it's busy,
            or 504 when it passed the GEMINI_TIMEOUT_MS deadline).
        httpx.TimeoutException: the request timed out on our side (e.g. Google unreachable).
        pydantic.ValidationError: Gemini's reply doesn't match ResumeAnalysis.
    """
    api_key = get_api_key()
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS))

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=build_prompt(resume_text, job_description),
        config={
            "response_mime_type": "application/json",
            # response_json_schema, not response_schema: the latter rejects extra="forbid"
            "response_json_schema": ResumeAnalysis.model_json_schema(),
        },
    )

    # Gemini is asked for this shape, but the reply is only trusted after our own validation
    return ResumeAnalysis.model_validate_json(response.text)
