"""Extract plain text from resume files (PDF or DOCX).

The main entry point is extract_resume_content(), which checks the file and
picks the right helper based on the extension. Every expected problem with
the file (wrong type, corrupted, empty or scanned) is raised as a ValueError
with a message that's safe to show to the user.
"""

import pymupdf
from docx import Document
from pathlib import Path
from docx.opc.exceptions import PackageNotFoundError

# Fewer characters than this usually means a scanned (image-only) or empty document
MIN_TEXT_LENGTH = 100


def extract_pdf_text(file_path):
    """Return all the text in a PDF, one page after another.

    Args:
        file_path: path to the .pdf file (a string or a Path).

    Raises:
        ValueError: the file isn't a real PDF (for example, a renamed .txt)
            or is corrupted.
    """
    text = ""
    try:
        with pymupdf.open(file_path) as doc:
            for page in doc:
                text += page.get_text() + "\n"
    except pymupdf.FileDataError as error:
        raise ValueError("This file isn't a valid or readable PDF.") from error

    return text


def extract_docx_text(file_path):
    """Return all the paragraph text in a Word (.docx) file, one paragraph per line.

    Args:
        file_path: path to the .docx file (a string or a Path).

    Raises:
        ValueError: the file isn't a real .docx or is corrupted.
    """
    text = ""
    try:
        doc = Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except PackageNotFoundError as error:
        # python-docx raises PackageNotFoundError for both missing and invalid files
        raise ValueError("This file isn't a valid or readable .docx document.") from error

    return text


def extract_resume_content(file_path):
    """Check a resume file and return its text.

    Picks the PDF or DOCX helper from the file extension, then makes sure
    enough real text came out to be worth analysing.

    Args:
        file_path: path to the resume file (a string or a Path).

    Returns:
        The extracted text as a single string.

    Raises:
        FileNotFoundError: nothing exists at file_path.
        ValueError: the extension isn't .pdf or .docx, the file can't be
            read, or it contains fewer than MIN_TEXT_LENGTH characters
            (usually an empty or scanned document).
    """
    # Checked here because each library reports a missing file differently
    if not Path(file_path).is_file():
        raise FileNotFoundError(f"No file found at '{file_path}'.")

    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        text = extract_pdf_text(file_path)
    elif extension == ".docx":
        text = extract_docx_text(file_path)
    else:
        raise ValueError(f"Unsupported file format: '{extension}'. Please upload a .pdf or .docx file.")

    # One check for both file types; whitespace and blank pages don't count as text
    if len(text.strip()) < MIN_TEXT_LENGTH:
        raise ValueError(
            "Little or no text could be extracted. The file may be empty or a scanned image; "
            "please upload a text-based PDF or .docx file."
        )

    return text
