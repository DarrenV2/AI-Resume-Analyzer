"""Tests for resume_extractor.py.

These call the extractor functions directly. Each test builds the file it
needs in tmp_path, so no real resumes are needed.

Run with:  python -m pytest -v
"""

import pytest
import pymupdf
from resume_extractor import extract_resume_content, extract_pdf_text


def test_unsupported_extension_raises_value_error(tmp_path):
    """A .txt file is rejected with a ValueError about the file format."""
    # A real file, so the "file exists" check passes and the extension check is what gets tested
    text_file = tmp_path / "resume.txt"
    text_file.write_text("This is a plain text resume, not a PDF or DOCX.")

    with pytest.raises(ValueError, match="Unsupported file format"):
        extract_resume_content(text_file)


def test_invalid_file_pdf(tmp_path):
    """A plain text file renamed to .pdf is rejected as an unreadable PDF."""
    text_file = tmp_path / "resume.pdf"
    text_file.write_text("This is a plain text resume, not a PDF.")

    with pytest.raises(ValueError, match="This file isn't a valid or readable PDF"):
        extract_pdf_text(text_file)


def test_little_or_no_content_pdf(tmp_path):
    """A valid PDF with no text (like a scanned resume) is rejected as too short."""
    # It has to be a real PDF; an empty file would fail the "valid PDF" check first instead
    pdf_file = tmp_path / "resume.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(pdf_file)
    doc.close()

    with pytest.raises(ValueError, match="Little or no text could be extracted"):
        extract_resume_content(pdf_file)
