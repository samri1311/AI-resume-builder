# backend/services/tailor_service.py
"""Phase F (ATS suggestions -> action bridge).

The ATS Score screen could always tell you WHAT was wrong (missing
keywords, low skill match) but never gave you a way to actually act on it
- the tailoring logic that could fix it (enhance_experience_for_job_async /
generate_tailored_summary_async) only ever ran inside the separate
"Generate from Job Description" pivot (Phase C), which builds a brand new
draft from scratch rather than touching a resume you've already built and
saved.

build_tailoring_preview() runs those exact same calls, just pointed at a
REAL saved models.Resume's experiences/summary instead of a freeform
parsed-background dict. It only returns a preview - nothing is written to
the database here. See resume_service.update_resume_service for the step
that actually saves whichever parts of the preview the person accepts
(POST /resume/{id}/tailor-preview -> PUT /resume/{id}).
"""

import asyncio

from backend.services.ai_engine import (
    enhance_experience_for_job_async,
    generate_tailored_summary_async,
)
from backend.services.ats_engine import calculate_ats_score


async def _tailor_experience_or_skip(exp, job_description: str, missing_keywords: list) -> list:
    # Mirrors draft_service._tailor_experience_or_skip's "don't call Groq
    # for nothing" guard - an experience with no description has nothing
    # to tailor.
    description = exp.description
    if not description:
        return []

    result = await enhance_experience_for_job_async(
        description, job_description, missing_keywords=missing_keywords
    )
    # A per-experience tailoring failure shouldn't sink the whole preview -
    # that one experience just proposes no change (empty bullets), same
    # fallback philosophy as draft_service.
    return result["data"] if result["success"] else []


async def _tailor_all(resume, job_description: str, missing_keywords: list) -> tuple:
    # Same asyncio.gather() concurrency pattern as draft_service._tailor_all
    # and resume_service._enhance_all - one Groq round-trip in parallel per
    # experience plus the summary, instead of N+1 sequential calls.
    summary_coro = generate_tailored_summary_async(
        resume.summary or "", job_description, missing_keywords=missing_keywords
    )
    experience_coros = [
        _tailor_experience_or_skip(exp, job_description, missing_keywords)
        for exp in resume.experiences
    ]

    results = await asyncio.gather(summary_coro, *experience_coros)
    summary_result, experience_bullets = results[0], results[1:]
    return summary_result, experience_bullets


def build_tailoring_preview(resume, job_description: str) -> dict:
    """resume: a saved models.Resume with .experiences loaded (a joinedload
    or lazy-load both work - only .id/.job_title/.description/
    .ai_description/.summary/.skills/.education are read).

    Returns {"success": True, "data": {...}} or
    {"success": False, "error": str} - same success/data/error shape used
    throughout the AI-calling services (parse_background, generate_draft).

    "data" shape:
    {
        "original_summary": str,
        "tailored_summary": str,
        "missing_keywords": [str, ...],
        "experiences": [
            {"id": int, "job_title": str, "original_description": str,
             "current_ai_description": [str, ...], "tailored_bullets": [str, ...]},
            ...
        ],
    }
    """
    if not job_description or not job_description.strip():
        return {"success": False, "error": "No job description provided"}

    # Missing keywords steer the tailoring calls the same way they do in
    # draft_service.generate_draft - computed against the resume as it
    # stands right now. An empty-vocabulary edge case shouldn't block the
    # whole preview, so fall back to no keyword hints rather than raising.
    try:
        ats_result = calculate_ats_score(resume, job_description)
        missing_keywords = ats_result.get("missing_keywords", [])
    except Exception as e:
        print("Error computing missing keywords for tailoring preview:", e)
        missing_keywords = []

    summary_result, experience_bullets = asyncio.run(
        _tailor_all(resume, job_description, missing_keywords)
    )

    # Tailored summary falls back to the ORIGINAL summary text (not blank)
    # on failure - same reasoning as draft_service: some usable text beats
    # an empty preview.
    tailored_summary = summary_result["data"] if summary_result["success"] else (resume.summary or "")

    experiences_preview = [
        {
            "id": exp.id,
            "job_title": exp.job_title,
            "original_description": exp.description or "",
            "current_ai_description": exp.ai_description or [],
            "tailored_bullets": bullets,
        }
        for exp, bullets in zip(resume.experiences, experience_bullets)
    ]

    return {
        "success": True,
        "data": {
            "original_summary": resume.summary or "",
            "tailored_summary": tailored_summary,
            "missing_keywords": missing_keywords,
            "experiences": experiences_preview,
        },
    }
