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

# Uploads larger than this are rejected. len() on bytes counts bytes, so the limit is in bytes too
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB in bytes


# The application object; uvicorn finds it through "main:app"
app = FastAPI()

# The decorator registers home() to handle GET requests to "/health"
@app.get("/health")
def health():
    """Report that the server is running.

    A health check is a cheap route that monitoring tools (and tests) can
    call to confirm the app is up, without doing any real work.
    """
    return {"status": "ok"}

# The resume arrives as a file and the job description as a text field,
# both sent together as multipart/form-data (the way HTML forms upload files)
@app.post("/analyze")
async def analyze(resume: UploadFile, job_description: Annotated[str, Form()]):
    """Extract the text from an uploaded resume.

    For now this only returns the extracted text; the AI analysis against
    job_description will be added in Milestone 4.

    Responses:
        200: {"RESULT": <extracted text>}
        400: the file is the wrong type, unreadable, or has too little text
        413: the file is larger than MAX_FILE_SIZE
        422: a required field is missing (FastAPI sends this automatically,
             before this function runs)
    """
    # read() is async, so "await" lets the server handle other requests while the upload is read
    file_bytes = await resume.read()

    # 413 is the standard status code for "Content Too Large".
    # This check runs before anything touches the disk, so huge uploads are never written out.
    # raise stops the function here, and FastAPI turns the exception into a {"detail": ...} response
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"upload is too large max size is {MAX_FILE_SIZE} Bytes")
    else:
        # The extractor needs a file path, but the upload is only bytes in memory,
        # so the bytes are written to a temporary file first.
        # The original extension is kept because the extractor picks PDF or DOCX from it.
        found_suffix = Path(resume.filename).suffix.lower()
        error_message = None

        # NamedTemporaryFile gives every request its own random file name in the OS temp folder,
        # so uploads can't overwrite each other and never end up in the project or in Git.
        # delete_on_close=False: close() only finishes writing; the file is deleted when "with" ends
        with tempfile.NamedTemporaryFile(suffix=found_suffix, delete_on_close=False) as temp_file:
            temp_file.write(file_bytes)
            # On Windows, another library can't open a file we still have open, so close it first
            temp_file.close()
            try:
                text = extract_resume_content(temp_file.name)
            except ValueError as error:
                # Only keep the message. Raising here, inside the "with", keeps PyMuPDF's
                # failed open alive, and Windows then refuses to delete the temp file
                error_message = str(error)
        # here the temp file has been deleted, so it's now safe to raise
        if error_message is not None:
            # 400 Bad Request: the problem is the user's file, not the server
            raise HTTPException(status_code=400, detail=error_message)
        return {"RESULT":text}
