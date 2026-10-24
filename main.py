# FastAPI app: defines the API routes only.
# Document processing lives in resume_extractor.py, and AI calls will live in their own module.

from fastapi import FastAPI, UploadFile, Form, HTTPException
from typing import Annotated
from resume_extractor import extract_resume_content
import tempfile 
from pathlib import Path
# Uploads larger than this are rejected. len() on bytes counts bytes, so the limit is in bytes too
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB in bytes


# The application object; uvicorn finds it through "main:app"
app = FastAPI()

# The decorator registers home() to handle GET requests to "/"
@app.get("/")

def home():
    return {"message": "test me "}

# The resume arrives as a file and the job description as a text field,
# both sent together as multipart/form-data (the way HTML forms upload files)
@app.post("/analyze")
async def analyze(resume: UploadFile, job_description: Annotated[str, Form()]):
    # read() is async, so "await" lets the server handle other requests while the upload is read
    file_bytes = await resume.read()

    # 413 is the standard status code for "Content Too Large".
    # raise stops the function here, and FastAPI turns the exception into a {"detail": ...} response
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"upload is too large max size is {MAX_FILE_SIZE} Bytes")
    else:
        found_suffix = Path(resume.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=found_suffix, delete_on_close=False) as temp_file:
            temp_file.write(file_bytes)
            temp_file.close()
            try:
                text = extract_resume_content(temp_file.name)
            except ValueError as error:
                raise HTTPException(status_code = 400, detail=str(error)) from error    
        # here the temp file has been deleted
        return {"RESULT":text}

