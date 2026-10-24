import pymupdf
from docx import Document
from pathlib import Path
from docx.opc.exceptions import PackageNotFoundError

# Fewer characters than this usually means a scanned (image-only) or empty document
MIN_TEXT_LENGTH = 100


def extract_pdf_text(file_path):
    text = ""
    try:
        # "with" closes the PDF automatically when the block ends, even if an error occurs
        with pymupdf.open(file_path) as doc:
            for page in doc:
                text += page.get_text() + "\n"
    except pymupdf.FileDataError as error:
        raise ValueError("This file isn't a valid or readable PDF.") from error

    return text


def extract_docx_text(file_path):
    text = ""
    try:
        doc = Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except PackageNotFoundError as error:
        raise ValueError("This file isn't a valid or readable .docx document.") from error

    return text


def extract_resume_content(file_path):
    if not Path(file_path).is_file():
        raise FileNotFoundError(f"No file found at '{file_path}'.")

    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        text = extract_pdf_text(file_path)
    elif extension == ".docx":
        text = extract_docx_text(file_path)
    else:
        raise ValueError(f"Unsupported file format: '{extension}'. Please upload a .pdf or .docx file.")

    # strip() removes surrounding whitespace, so blank pages and empty lines don't count as text
    if len(text.strip()) < MIN_TEXT_LENGTH:
        raise ValueError(
            "Little or no text could be extracted. The file may be empty or a scanned image; "
            "please upload a text-based PDF or .docx file."
        )

    return text


