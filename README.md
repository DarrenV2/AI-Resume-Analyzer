# AI Resume Analyzer

Upload a resume and paste a job description to see, requirement by requirement, how well the resume's evidence supports the role, with exact quotes from the resume and honest, practical suggestions.

**Live demo:** https://ai-resume-analyzer-9tai.onrender.com/

> It runs on a free hosting tier, so the first visit after a quiet period can take about a minute to wake up.


## What it does

- Reads a **PDF or DOCX** resume and splits the job description into individual requirements
- Gives each requirement a **priority** (required / preferred / unspecified) and a **status** (see below)
- Shows the quoted resume evidence and the reasoning for each status, plus a suggestion where one is useful
- Summarizes strengths and the most important improvements

Each requirement gets one of four statuses:

| Status | Meaning |
|---|---|
| Strong evidence | The resume directly demonstrates the requirement |
| Partial evidence | Related or incomplete evidence, e.g. a skill only listed, or an API *used* but not *built* |
| Not identified | The resume doesn't mention it. This does **not** mean the person lacks the skill |
| Needs review | The evidence is ambiguous or contradictory |

## Design principles

- **Evidence over keywords.** Every status is backed by quotes from the resume, and the prompt has explicit rules: consuming an API isn't building one, and using a database isn't proof of SQL skills.
- **Honest wording.** Missing evidence is "not identified", never "lacks". Suggestions never invent experience.
- **No fake match score.** The status counts are calculated in code from the requirements, not invented by the AI.
- **AI output isn't trusted blindly.** Gemini is asked for JSON in a fixed schema, and every reply is validated with Pydantic before it's shown. An invalid reply becomes a clear error, not a crash.

## How it works

```
Browser (static/)  ── POST /analyze ──▶  FastAPI (main.py)
                                           1. check the upload (type, size, real content)
                                           2. extract the text        (resume_extractor.py)
                                           3. build the prompt        (prompt.py)
                                           4. ask Gemini for JSON     (ai_analyzer.py)
                                           5. validate the reply      (schemas.py, Pydantic)
Browser shows the report  ◀── JSON ──────┘
```

Each file has one job, so the extraction, the prompt, the AI call and the routes can each be tested on their own.

## Tech stack

**Python** · **FastAPI** · **Pydantic** · **Google Gemini API** (`google-genai`) · **PyMuPDF** · **python-docx** · **pytest** · **HTML, CSS and JavaScript** (no framework) · deployed on **Render**

## Run it locally

You'll need **Python 3.12+** and a Gemini API key from [Google AI Studio](https://aistudio.google.com/).

```bash
git clone https://github.com/DarrenV2/AI-Resume-Analyzer.git
cd AI-Resume-Analyzer
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your key:

```
GEMINI_API_KEY=your-api-key-here
```

Start the server, then open http://127.0.0.1:8000:

```bash
uvicorn main:app --reload
```

## Tests

```bash
python -m pytest
```

The tests cover the text extraction, the schema validation, the prompt, and the API's main success and error paths. Gemini is replaced by a fake in the tests, so they run offline, cost nothing, and send no data anywhere.

## Error handling

Every failure gets a clear message instead of a crash:

| Status | When |
|---|---|
| 400 | Wrong file type, a fake or corrupted file, or too little text (e.g. a scanned PDF) |
| 413 | The file is over 5 MB |
| 502 | Gemini's reply failed, or didn't match the schema |
| 503 | Gemini is busy, or the free-tier quota is used up |
| 504 | Gemini took longer than the 60-second timeout |

## Security and privacy

- **Resume text is sent to Google Gemini for analysis.** On the free tier, Google may use it to improve its products, and the page says so before upload.
- Resume text is never logged. Uploads are written to a temporary file that's deleted straight after extraction.
- Uploads are checked by their content, not just their file extension.
- AI output is put on the page with `textContent`, never `innerHTML`, so text copied from a resume can't run as code (XSS).
- The resume and job description are wrapped in tags in the prompt, and marked as data rather than instructions. That makes it harder for instructions hidden in a resume to take effect (prompt injection).
- The API key lives in `.env`, which is git-ignored.

## Limitations

- Scanned (image-only) PDFs aren't supported: there's no OCR.
- Text inside tables in DOCX files isn't read yet.
- The live demo sleeps when idle, so the first visit can take about a minute.
- The analysis is AI-generated guidance. Check it against your own judgment.

## Future improvements

- Check that every quote really appears in the resume
- Read DOCX tables, and add OCR for scanned PDFs
- Split the analysis into stages (extract requirements → extract evidence → match), so each step can be tested and checked on its own

## Disclaimer

- This project was developed for learning and demonstration purposes.
- AI analysis results may vary and should not be considered professional career advice.

## Author

Built by **Darren Drummond** ([@DarrenV2](https://github.com/DarrenV2)).
