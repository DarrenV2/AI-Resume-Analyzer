"""FastAPI app for the AI Resume & Job Description Analyzer.

This file defines the API routes only. Reading PDF/DOCX files lives in
resume_extractor.py and the AI call lives in ai_analyzer.py, so each part
can be tested on its own.

Run the server with:  uvicorn main:app --reload
Interactive docs at:  http://127.0.0.1:8000/docs
"""

import logging
import tempfile
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from google.genai import errors
from pydantic import ValidationError

from ai_analyzer import analyze_resume, MissingAPIKeyError
from resume_extractor import extract_resume_content
from schemas import ResumeAnalysis


MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Shown for both kinds of timeout: Gemini's own deadline (504) and httpx's on our side
AI_TIMEOUT_MESSAGE = "The AI took too long to respond. Please try again."

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/health")
def health():
    """Report that the server is running."""
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(resume: UploadFile, job_description: Annotated[str, Form()]) -> ResumeAnalysis:
    """Extract the text from an uploaded resume and analyze it against the job description.

    Responses:
        200: the analysis, in the shape of ResumeAnalysis
        400: the file is the wrong type, unreadable, or has too little text
        413: the file is larger than MAX_FILE_SIZE
        422: a required field is missing (sent by FastAPI before this function runs)
        500: the AI service isn't configured (no API key on the server)
        502: the AI request failed, or the AI's reply didn't match ResumeAnalysis
        503: the AI service is busy or over its quota; the user can try again later
        504: the AI took longer than the timeout (GEMINI_TIMEOUT_MS in ai_analyzer.py)
    """
    file_bytes = await resume.read()

    # Checked before anything is written to disk, so oversized uploads are never saved
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"upload is too large max size is {MAX_FILE_SIZE} Bytes",
        )

    # The extractor needs a file path and picks PDF or DOCX from the extension,
    # so the upload is written to a temp file that keeps the original extension
    found_suffix = Path(resume.filename).suffix.lower()
    error_message = None

    # delete_on_close=False: the file must survive close() below, and is deleted when "with" ends
    with tempfile.NamedTemporaryFile(suffix=found_suffix, delete_on_close=False) as temp_file:
        temp_file.write(file_bytes)

        # On Windows another library can't open a file that's still open here
        temp_file.close()

        try:
            text = extract_resume_content(temp_file.name)
        except ValueError as error:
            # Keep only the message. Raising inside the "with" keeps PyMuPDF's failed
            # open alive, and Windows then refuses to delete the temp file
            error_message = str(error)

    # The temp file is gone now, so it's safe to raise
    if error_message is not None:
        raise HTTPException(status_code=400, detail=error_message)

    # The AI only needs the text, so it runs after the temp file has been deleted.
    # Users get a short message; the details are logged for the developer, never the resume text
    try:
        # The Gemini call takes seconds and isn't async, so it runs in a worker thread;
        # calling it directly would stop the server handling any other request meanwhile
        return await run_in_threadpool(analyze_resume, text, job_description)

    except MissingAPIKeyError as error:
        logger.error("Analysis not configured: %s", error)
        raise HTTPException(status_code=500, detail="The analysis service isn't configured.")

    except httpx.TimeoutException as error:
        # Raised by the HTTP client when it gives up first, e.g. when Google can't be reached
        logger.error("Gemini request timed out on our side: %r", error)
        raise HTTPException(status_code=504, detail=AI_TIMEOUT_MESSAGE)

    except errors.APIError as error:
        logger.error("Gemini request failed: %s %s", error.code, error.message)

        # 504 = Gemini passed the deadline we sent it (tested: it times out before httpx does)
        if error.code == 504:
            raise HTTPException(status_code=504, detail=AI_TIMEOUT_MESSAGE)

        # 503 = Gemini overloaded, 429 = our free-tier quota is used up: both are temporary
        if error.code in (429, 503):
            raise HTTPException(
                status_code=503,
                detail="The AI service is busy. Please try again in a minute.",
            )

        raise HTTPException(
            status_code=502,
            detail="The AI service could not complete the analysis.",
        )

    except ValidationError as error:
        # include_input=False: the invalid reply may quote the resume, which must not be logged
        logger.error("Gemini reply failed validation: %s", error.errors(include_input=False))
        raise HTTPException(
            status_code=502,
            detail="The AI returned an unexpected response. Please try again.",
        )


# Serves the web page: the files in static/ (index.html, style.css, app.js), with index.html
# sent for "/". Kept this last, so /health and /analyze are matched before the file server
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
