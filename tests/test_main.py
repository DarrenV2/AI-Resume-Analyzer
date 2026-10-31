"""API tests for the routes in main.py.

Uploads are built in memory as bytes, so no real resume files are needed.
The AI call is replaced by a fake in every test that reaches it, so the tests
never contact Gemini, cost nothing and send no data anywhere.

Run with:  python -m pytest -v
"""

import pymupdf
from fastapi.testclient import TestClient
from google.genai import errors

import main
from ai_analyzer import MissingAPIKeyError
from main import app, MAX_FILE_SIZE
from schemas import ResumeAnalysis

client = TestClient(app)


def make_pdf_bytes():
    """Return a small valid PDF with enough text to pass the extractor."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Built a Flask web app with a SQLite database. " * 3)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def post_valid_resume():
    """Send a valid resume and job description to /analyze and return the response."""
    return client.post(
        "/analyze",
        files={"resume": ("resume.pdf", make_pdf_bytes(), "application/pdf")},
        data={"job_description": "Junior Python Developer"},
    )


def test_health():
    """The health check route responds with 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200


def test_analyze_fake_pdf_returns_400():
    """A fake PDF (plain text renamed to .pdf) gets a 400 and a readable message, not a 500 crash."""
    response = client.post(
        "/analyze",
        files={"resume": ("resume.pdf", b"This is plain text, not a PDF.", "application/pdf")},
        data={"job_description": "Junior Python developer"},
    )

    assert response.status_code == 400
    assert "isn't a valid or readable PDF" in response.json()["detail"]


def test_analyze_txt_returns_400():
    """An unsupported file type (.txt) gets a 400 explaining the allowed formats."""
    response = client.post(
        "/analyze",
        files={"resume": ("resume.txt", b"This is plain text, not a PDF.", "application/txt")},
        data={"job_description": "Junior Python developer"},
    )

    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_analyze_over_file_size():
    """A file over MAX_FILE_SIZE gets a 413.

    The size check runs before the file type is looked at, so the
    contents and filename don't matter here, only the size.
    """
    # One byte over the limit, which also tests the exact boundary
    response = client.post(
        "/analyze",
        files={"resume": ("resume.pdf", b"a" * (MAX_FILE_SIZE + 1), "application/pdf")},
        data={"job_description": "Junior Python developer"},
    )

    assert response.status_code == 413
    assert "upload is too large max size " in response.json()["detail"]


# The tests below replace analyze_resume with a fake, so Gemini is never called.
# The fake must be set on main, not on ai_analyzer: main.py's "from ai_analyzer import
# analyze_resume" gave main its own reference to the function, and that's the one the route calls


def test_analyze_success_returns_analysis(monkeypatch):
    """A successful analysis is returned as JSON, built from the extracted text and job description."""
    received = {}

    def fake_analyze_resume(resume_text, job_description):
        received["resume_text"] = resume_text
        received["job_description"] = job_description
        return ResumeAnalysis(
            summary="Fake summary for testing.",
            requirements=[
                {
                    "requirement": "SQL",
                    "priority": "required",
                    "status": "partial_evidence",
                    "reasoning": "A SQLite database is mentioned, but SQL use is not described.",
                }
            ],
        )

    monkeypatch.setattr(main, "analyze_resume", fake_analyze_resume)

    response = post_valid_resume()

    assert response.status_code == 200
    assert response.json()["summary"] == "Fake summary for testing."
    assert response.json()["requirements"][0]["status"] == "partial_evidence"
    # The route passed the text it extracted from the PDF, and the user's job description
    assert "Flask web app" in received["resume_text"]
    assert received["job_description"] == "Junior Python Developer"


def test_analyze_missing_api_key_returns_500(monkeypatch):
    """A missing API key gets a 500 with a message that doesn't reveal server details."""
    def fake_analyze_resume(resume_text, job_description):
        raise MissingAPIKeyError("GEMINI_API_KEY is not set.")

    monkeypatch.setattr(main, "analyze_resume", fake_analyze_resume)

    response = post_valid_resume()

    assert response.status_code == 500
    assert "GEMINI_API_KEY" not in response.json()["detail"]


def test_analyze_gemini_busy_returns_503(monkeypatch):
    """Gemini being overloaded (its 503) gets a 503 telling the user to try again."""
    def fake_analyze_resume(resume_text, job_description):
        raise errors.APIError(503, {"error": {"message": "busy"}})

    monkeypatch.setattr(main, "analyze_resume", fake_analyze_resume)

    response = post_valid_resume()

    assert response.status_code == 503
    assert "try again" in response.json()["detail"]


def test_analyze_gemini_quota_returns_503(monkeypatch):
    """Our free-tier quota running out (Gemini's 429) is also a temporary 503, not the user's fault."""
    def fake_analyze_resume(resume_text, job_description):
        raise errors.APIError(429, {"error": {"message": "quota exceeded"}})

    monkeypatch.setattr(main, "analyze_resume", fake_analyze_resume)

    response = post_valid_resume()

    assert response.status_code == 503


def test_analyze_gemini_other_error_returns_502(monkeypatch):
    """Any other Gemini failure gets a 502 Bad Gateway."""
    def fake_analyze_resume(resume_text, job_description):
        raise errors.APIError(400, {"error": {"message": "bad request"}})

    monkeypatch.setattr(main, "analyze_resume", fake_analyze_resume)

    response = post_valid_resume()

    assert response.status_code == 502


def test_analyze_invalid_ai_reply_returns_502(monkeypatch):
    """A reply from Gemini that doesn't match ResumeAnalysis gets a 502 Bad Gateway."""
    def fake_analyze_resume(resume_text, job_description):
        # Raises a real ValidationError: an empty requirements list is rejected
        return ResumeAnalysis.model_validate_json('{"summary": "x", "requirements": []}')

    monkeypatch.setattr(main, "analyze_resume", fake_analyze_resume)

    response = post_valid_resume()

    assert response.status_code == 502
