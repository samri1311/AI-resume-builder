# Demo Resumes

Two realistic example resumes generated through the actual app code (FastAPI `POST /resume/` → `GET /pdf/resume/{id}`, same path `run_app.py`'s server executes), using the current Lato-embedded PDF template with all fields (title, website, education details, certifications, awards).

- `demo_resume_priya_sharma_frontend_engineer.pdf` — Senior Frontend Engineer
- `demo_resume_ethan_brooks_growth_marketing_manager.pdf` — Growth Marketing Manager

Both people, employers, and details are fictional, generated for demo/reference purposes only.

These were produced against a throwaway database, not `resumes.db`, so no real user data is involved. AI-enhanced bullet rewriting (Groq) was not live when these were generated, so the bullet text shown is the original (already bullet-formatted) experience descriptions rather than AI-rewritten versions — regenerate via the running app with a valid `GROQ_API_KEY` if you want AI-enhanced wording in these reference PDFs.
