"""API tests for the routes in main.py.

TestClient sends fake HTTP requests straight to the FastAPI app, so these
tests check the full request -> response path (status codes and error
messages) without starting uvicorn.

Uploads are built in memory as bytes, so no real resume files are needed.

Run with:  python -m pytest -v
"""

from fastapi.testclient import TestClient

from main import app, MAX_FILE_SIZE

# TestClient sends requests straight to the app, so uvicorn doesn't need to be running
client = TestClient(app)


def test_health():
    """The health check route responds with 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200


def test_analyze_fake_pdf_returns_400():
    """A fake PDF (plain text renamed to .pdf) gets a 400 and a readable message, not a 500 crash."""
    # files= sends the upload and data= sends the form fields, together as multipart/form-data.
    # The file is a tuple: (filename, contents as bytes, content type).
    # The "resume" key must match the parameter name in analyze()
    response = client.post(
        "/analyze",
        files={"resume": ("resume.pdf", b"This is plain text, not a PDF.", "application/pdf")},
        data={"job_description": "Junior Python developer"},
    )

    assert response.status_code == 400
    # HTTPException's detail ends up under "detail" in the JSON body
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
    # The upload only needs to be one byte over the limit; that also tests the exact boundary
    response = client.post(
        "/analyze",
        files={"resume": ("resume.pdf", b"a" * (MAX_FILE_SIZE + 1), "application/pdf")},
        data={"job_description": "Junior Python developer"},
    )

    assert response.status_code == 413
    assert "upload is too large max size " in response.json()["detail"]
