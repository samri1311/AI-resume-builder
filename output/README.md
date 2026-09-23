# Demo Resumes

Four realistic example resumes generated through the actual app code (FastAPI `POST /resume/` → `GET /pdf/resume/{id}`, same path `run_app.py`'s server executes), using the current Lato-embedded PDF template with all fields (title, website, education details, certifications, awards).

- `demo_resume_priya_sharma_frontend_engineer.pdf` — Senior Frontend Engineer
- `demo_resume_ethan_brooks_growth_marketing_manager.pdf` — Growth Marketing Manager
- `demo_resume_naomi_reyes_senior_data_engineer.pdf` — Senior Data Engineer
- `demo_resume_daniel_osei_software_engineer.pdf` — Software Engineer, generated via the **"Generate from Job Description"** pivot path (see note below)

All people, employers, and details are fictional, generated for demo/reference purposes only. All four were produced against a throwaway database, not `resumes.db`, so no real user data is involved.

## Priya Sharma, Ethan Brooks, Naomi Reyes — the manual path

Built by submitting a complete resume straight to `POST /resume/`, the same way the app's manual "Build manually" form does. AI-enhanced bullet rewriting (Groq) either wasn't live (Priya, Ethan) or was deliberately bypassed by supplying each experience's `ai_description` directly (Naomi) — either way, no live Groq call happened for these three, so the bullet text shown is hand-written rather than AI-rewritten. Regenerate via the running app with a valid `GROQ_API_KEY` if you want genuinely AI-enhanced wording in these reference PDFs.

## Daniel Osei — the "Generate from Job Description" path

This one exercises the actual pivot flow end to end: `POST /draft/generate` (`backend/services/draft_service.py` — `parse_background()` followed by job-description-aware tailoring) and only then `POST /resume/` → `GET /pdf/resume/{id}`, same as the others.

The pasted background was a plain-text resume dump for a generalist backend engineer. The target job description was a "Senior Backend Engineer — Platform Team" posting emphasizing Kubernetes, gRPC, and mentoring. The summary and every experience bullet on this PDF are the job-tailored output of that call — not the original background text. (The original, untailored description is still stored on each experience underneath the tailored bullets shown on the PDF, exactly like a real generated draft — it's just not what renders when `ai_description` is present.)

Groq itself was mocked for this one — no live `GROQ_API_KEY` was available from the session that generated it, so the parse/tailoring responses are hand-written stand-ins for what a real Groq call would return. Every other line of code between the pasted text and this PDF — background parsing, missing-keyword scoring, the concurrent tailoring calls, the dedup check that skips a second Groq call at resume-creation time, PDF rendering — ran for real, unmocked.

One real product behavior this demonstrates: the pivot currently only tailors the **summary** and **experience bullets** against the job description — the `title` field shown under the name is not rewritten, it's just whatever `parse_background` found in the pasted text. That's why Daniel's title still reads "Software Engineer" even though the target role was "Senior Backend Engineer." Worth knowing when reviewing a generated draft in the app.
