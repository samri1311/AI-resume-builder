# CLAUDE.md

AI Resume Builder: a FastAPI backend and a Streamlit frontend. Users build a resume by hand or generate a draft from a job description (JD). Groq LLMs rewrite the bullets and tailor them to a JD. A TF-IDF engine scores the resume against the JD (ATS score), and ReportLab exports a PDF.

## Commands

Run everything from the project root (imports are `backend.*`).

```bash
python -m venv .venv                                    # then activate it
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                    # set GROQ_API_KEY

python run_app.py                                       # backend (:8000) + frontend (:8501)
uvicorn backend.main:app --reload                       # backend only, docs at /docs
streamlit run frontend/app.py                           # frontend only

alembic upgrade head                                    # apply migrations to an empty DB
alembic stamp head                                      # DB already matches the models
alembic revision --autogenerate -m "message"            # new migration

pytest backend/tests                                    # tests
```

Environment variables (`.env`, loaded by `python-dotenv`):

| Variable | Default | Used by |
|---|---|---|
| `GROQ_API_KEY` | none | backend (`core/config.py`) |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | backend |
| `DATABASE_URL` | `sqlite:///./resumes.db` (relative to the cwd) | backend, Alembic |
| `RESUME_BUILDER_API_URL` | `http://127.0.0.1:8000` | frontend |

## Project layout

| Path | Purpose |
|---|---|
| `backend/main.py` | FastAPI app; mounts the routers; also calls `Base.metadata.create_all()` at import |
| `backend/core/config.py` | Env-based settings |
| `backend/database/` | Engine, `SessionLocal`, `get_db`, and `models.py` (SQLAlchemy models) |
| `backend/routes/` | `resume`, `ai`, `ats`, `pdf`, `draft` routers |
| `backend/schemas/` | Pydantic request/response models |
| `backend/services/` | Business logic (see Workflow) |
| `backend/assets/fonts/` | Lato TTFs embedded in the PDFs |
| `backend/tests/` | pytest suite |
| `frontend/app.py` | The whole Streamlit UI (about 1100 lines, one flat script) |
| `alembic/`, `alembic.ini` | Migrations; `env.py` reads `DATABASE_URL` from `core/config.py` |
| `run_app.py` | Launches uvicorn and Streamlit as subprocesses |
| `generated/` | Runtime PDF output (git-ignored) |
| `resumes.db` | SQLite database (**tracked in git**, see Suggested improvements) |

Legacy or dead files: `fix_schema.py` (stamps the DB to `0002`, so it is stale now), `backend/database/update_ats_table.py`, `backend/services/pdf_service.py` and `backend/utils/helpers.py` (both empty stubs).

## Workflow

**Manual path**
1. Fill in the form. Optionally click "Enhance Experience" (`POST /ai/enhance`, style `professional`, `impactful` or `concise`).
2. "Create Resume" calls `POST /resume/`. If an experience already carries `ai_description`, the backend skips its own Groq call.
3. "Check ATS Score" calls `POST /ats/score`.
4. "Generate PDF" calls `GET /pdf/resume/{id}`.

**Generate from Job Description path**
1. Paste a JD and a background, or upload a PDF/docx (`POST /draft/extract-text`).
2. `POST /draft/generate` parses the background, then tailors the summary and every experience concurrently. Nothing is saved.
3. The result pre-fills the same form, and the flow continues on the manual path.

**Tailor loop** (after an ATS score)
`POST /resume/{id}/tailor-preview` returns a preview and saves nothing. `PUT /resume/{id}` saves the accepted parts. The score is then re-run.

| Route | Purpose |
|---|---|
| `POST /resume/`, `GET /resume/{id}`, `PUT /resume/{id}` | Create, fetch, update summary and experience text |
| `POST /resume/{id}/tailor-preview` | Preview only |
| `POST /ai/enhance` | Groq bullet rewrite |
| `POST /ats/score` | Score and persist an `ats_scores` row |
| `POST /draft/generate`, `POST /draft/extract-text` | Draft from JD, file text extraction |
| `GET /pdf/resume/{id}` | PDF download |
| `GET /`, `GET /health` | Status |

Services (`backend/services/`):
- `ai_engine.py`: every Groq call. Module-level `client` and `async_client`, sync and async twins, and tolerant JSON parsing. Every function returns `{"success", "data", "error"}`.
- `ats_engine.py`: final score is `0.7 * TF-IDF cosine similarity + 0.3 * skill match`. Skills match as whole words. An experience counts as relevant at similarity 0.15 or more (`RELEVANT_EXPERIENCE_THRESHOLD`). Missing keywords are the top 10 TF-IDF terms of the JD absent from the resume. `calculate_ats_score_for_draft` scores an unsaved dict through duck-typed shim classes.
- `resume_service.py`: create (finds or creates the `User` by email, enhances experiences concurrently) and update.
- `tailor_service.py`: tailoring preview for a saved resume.
- `draft_service.py`: JD plus background into a draft, with warnings for a missing name, email or experience.
- `file_extraction.py`: PDF (`pypdf`) and docx (`python-docx`) text. There is no OCR.
- `pdf_generator.py`: A4 ReportLab PDF with embedded Lato, written to `generated/` and deleted after the response.

## Database

SQLite through SQLAlchemy (legacy `Column` and `declarative_base` style). Tables: `users`, `resumes`, `experiences` (`ai_description` is a JSON list), `education`, `skills`, `certifications`, `awards`, `ats_scores`.

Migrations:
- `0001`: initial schema.
- `0002`: `users.website`, `resumes.title`, `education.details`, and the `certifications` and `awards` tables.
- `0003`: the four ATS explainability count columns (uncommitted).

`main.py` also runs `create_all()`, which can hide a missing migration.

## Packages

All pinned in `requirements.txt`; `pytest>=8,<9` is in `requirements-dev.txt`.

| Package | Purpose |
|---|---|
| `fastapi` 0.135.3, `uvicorn` 0.44.0 | API framework and ASGI server |
| `sqlalchemy` 2.0.49, `alembic` 1.18.4 | ORM and migrations |
| `pydantic` 2.12.5, `email-validator` 2.3.0 | Schemas, and `EmailStr` support |
| `python-dotenv` 1.2.2 | `.env` loading (backend and frontend) |
| `python-multipart` 0.0.32 | `UploadFile` for `/draft/extract-text` |
| `pypdf` 6.19.0, `python-docx` 1.2.0 | Text extraction from uploaded resumes |
| `groq` 1.1.2 | LLM client (sync and async) |
| `scikit-learn` 1.8.0 | TF-IDF and cosine similarity for ATS (pulls in `numpy`) |
| `reportlab` 4.5.0 | PDF generation |
| `streamlit` 1.56.0, `requests` 2.33.1 | Frontend and its HTTP calls |
| `pytest` (dev) | Tests |

## Conventions and gotchas

- Tests mock the Groq clients (`backend.services.ai_engine.client` and `async_client`). DB tests use an in-memory SQLite fixture. There is no `conftest.py`.
- `pytest` is not installed in the local `.venv`; install `requirements-dev.txt` first.
- Error handling is mixed: the resume and PDF routes use HTTP status codes; the ai, ats and draft routes return an `APIResponse` envelope, often with HTTP 200 (a missing resume in `/ats/score` is HTTP 200 with `success: false`).
- Sync routes call `asyncio.run()` to run concurrent Groq calls.
- The frontend is one script driven by `st.session_state`. The draft pre-fill sets each widget's own key by hand (`job_title_0`, `college_0`, and so on).
- The frontend header comments use "Phase 1-6, D, E, F, G" labels as a changelog.
- `resumes.db` is tracked in git, so every run shows it as modified. Do not commit it.
- Uncommitted work in progress: Phase E (ATS explainability: counts, migration `0003`) and Phase F (tailor preview and `PUT /resume/{id}`, with `tailor_service.py` and its tests).

## Suggested improvements

### Frontend (`frontend/app.py`)
1. **AI-enhanced labels.** "Using the AI-enhanced version" appears when the draft flow already applied the bullets, so it reads like a state the user never chose. Label it clearly ("Tailored to your JD during draft generation"), put the style picker next to the Enhance button, and rename the button "Rewrite in this style". Show a before/after diff, and say "already aligned, no change proposed" when nothing meaningful changed.
2. **Identical Current vs AI-Tailored summary.** Tailor-preview reruns the same prompt on text the draft flow already tailored. If the LLM call fails, the code silently falls back to the original summary (`tailor_service.py:105`). Surface both cases instead of showing two identical columns.
3. **JD asked twice.** Prefill the ATS box from the draft JD. Better, store `job_description` on the resume (new column and migration) so scoring, tailoring and the PDF reuse it.
4. **Score delta and gap plan** (its own phase):
   - Score the tailored version without saving it and show the change (for example 42% to 61%).
   - Tiers: 70% or more is a strong match, 50-70% is OK, and under 50% opens a gap plan.
   - The gap plan is a questionnaire: "Do you have X?" A yes plus a one-line detail feeds the tailoring as truthful evidence. A no goes to a skill-gap list with certification or course suggestions (no AI-generated URLs).
   - Do not guarantee a minimum score. TF-IDF cosine is naturally low, and forcing it invites keyword stuffing or invented experience. Consider LLM or embedding matching and recalibrating the 70/30 weights.
5. **Split the app.** Break the 1100-line file into a multipage app or modules, move the draft pre-fill into a helper, and replace the "Phase N" changelog header with real docs.
6. **Stronger validation.** A real email check, date formats or pickers, clear `end_date` when "Currently working here" is ticked, and phone and website checks.
7. **Skills as tags.** A tag or multiselect input pre-filled from the parsed draft, with JD missing-keyword suggestions and dedupe.
8. **Reorder and duplicate entries.** Move up/down and duplicate buttons, and a confirm before Remove.
9. **Save and reload resumes.** A "My resumes" list to load, edit and re-score, and draft autosave. Today there is no way to update a saved resume from the form, and a refresh loses everything.

### Backend
1. **LLM robustness.** `parse_background` reports success on unparseable output. Use JSON mode or schema-constrained output with retries, factor the sync/async twins in `ai_engine.py` (about 8 near-identical try/except blocks), and add a fallback model or provider.
2. **Async cleanup.** Routes are sync but call `asyncio.run()` per request (`resume_service`, `tailor_service`, `draft_service`). Make the routes async or use a background pattern. Guard TF-IDF against an empty vocabulary in `calculate_ats_score`.
3. **Dedupe and config.**
   - `_tailor_all` is duplicated in `draft_service.py` and `tailor_service.py`, and `_RESUME_RELATIONSHIPS` is duplicated in `routes/resume.py` and `routes/pdf.py`.
   - Move the ATS weights (0.7/0.3), the 0.15 threshold, temperatures and frontend timeouts into config.
   - Move to SQLAlchemy 2.0 typed (`Mapped`) models.
4. **Tests.** Add `TestClient` route tests, and tests for `create_resume_service`, `pdf_generator` and the migrations. Add `pytest.ini` and coverage.
5. **Docs.** Rewrite `README.md` (it lists the wrong frontend file and wrong endpoints, and never mentions Alembic or the draft flow). Fix `.env.example`, whose default `GROQ_MODEL` disagrees with `core/config.py`.

### Also worth flagging (lower priority)
- **`resumes.db` is tracked** and holds real user data (21 users with emails and phone numbers). Run `git rm --cached resumes.db`, and delete the stale `fix_schema.py`.
- No auth or ownership checks: any client can read or edit any resume by sequential id, and `POST /resume/` reuses an existing user by email.
- No rate limits on the Groq endpoints, and no upload-size or text-length limits.
- `User.resume` is declared one-to-one, but a user can have many resumes. `ats_scores.score` is a legacy duplicate of `ats_score`, and `ATSScoreResponse` declares dict types for list data.
