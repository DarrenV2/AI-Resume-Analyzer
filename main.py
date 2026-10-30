"""FastAPI app for the AI Resume & Job Description Analyzer.

This file defines the API routes only. Reading PDF/DOCX files lives in
resume_extractor.py, and AI calls will live in their own module, so each
part can be tested on its own.

Run the server with:  uvicorn main:app --reload
Interactive docs at:  http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, UploadFile, Form, HTTPException
from typing import Annotated
from resume_extractor import extract_resume_content
import tempfile
from pathlib import Path

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


app = FastAPI()


@app.get("/health")
def health():
    """Report that the server is running."""
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(resume: UploadFile, job_description: Annotated[str, Form()]):
    """Extract the text from an uploaded resume.

    For now this only returns the extracted text

    Responses:
        200: {"RESULT": <extracted text>}
        400: the file is the wrong type, unreadable, or has too little text
        413: the file is larger than MAX_FILE_SIZE
        422: a required field is missing (sent by FastAPI before this function runs)
    """
    file_bytes = await resume.read()

    # Checked before anything is written to disk, so oversized uploads are never saved
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"upload is too large max size is {MAX_FILE_SIZE} Bytes")
    else:
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
        return {"RESULT":text}
