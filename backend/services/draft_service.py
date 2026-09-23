# backend/services/draft_service.py
"""Phase C (pivot: paste a job description + background -> tailored draft).

Orchestrates Phase A (parse_background) and Phase B (job-description-aware
tailoring + calculate_ats_score_for_draft) into the one function the new
POST /draft/generate route calls: generate_draft(job_description,
background_text) -> {"success", "data": DraftResponse-shaped dict, "error"
on failure}.

Deliberately additive, not a rewrite: this reuses parse_background,
enhance_experience_for_job_async, generate_tailored_summary_async, and
calculate_ats_score_for_draft exactly as Phases A/B left them - nothing
here duplicates Groq-calling or scoring logic that's already tested.
"""

import asyncio

from backend.schemas.draft import DraftResponse
from backend.services.ai_engine import (
    enhance_experience_for_job_async,
    generate_tailored_summary_async,
    parse_background,
)
from backend.services.ats_engine import calculate_ats_score_for_draft


async def _tailor_experience_or_skip(exp: dict, job_description: str, missing_keywords: list) -> list:
    # Mirrors resume_service._enhance_or_skip's "don't call Groq for
    # nothing" guard: an experience with no description has nothing to
    # tailor, so skip it rather than sending an empty string to the model.
    description = exp.get("description")
    if not description:
        return []

    result = await enhance_experience_for_job_async(
        description, job_description, missing_keywords=missing_keywords
    )
    # On a per-experience tailoring failure, fall back to no AI bullets for
    # just that one experience rather than failing the whole draft - the
    # person still gets everything else, and can retry that one experience
    # from the review screen (Phase D) same as they already can today via
    # the "Enhance Experience" button.
    return result["data"] if result["success"] else []


async def _tailor_all(parsed: dict, job_description: str, missing_keywords: list) -> tuple:
    # One asyncio.gather() covering the summary call AND every experience's
    # tailoring call together, so a background with several jobs listed
    # doesn't wait on N+1 sequential Groq round-trips - same concurrency
    # pattern as resume_service._enhance_all.
    summary_coro = generate_tailored_summary_async(
        parsed.get("summary") or "", job_description, missing_keywords=missing_keywords
    )
    experience_coros = [
        _tailor_experience_or_skip(exp, job_description, missing_keywords)
        for exp in parsed.get("experiences") or []
    ]

    results = await asyncio.gather(summary_coro, *experience_coros)
    summary_result, experience_bullets = results[0], results[1:]
    return summary_result, experience_bullets


def _build_warnings(parsed: dict) -> list:
    warnings = []

    if not parsed.get("name"):
        warnings.append("No name was found in the pasted background - check and fill it in.")
    if not parsed.get("email"):
        warnings.append("No email was found in the pasted background - check and fill it in.")
    if not parsed.get("experiences"):
        warnings.append("No work experience was found in the pasted background - check and add it if you have any.")

    return warnings


def generate_draft(job_description: str, background_text: str) -> dict:
    """Returns {"success": True, "data": <DraftResponse dict>} on success,
    or {"success": False, "error": str} on failure - same success/data/error
    shape as parse_background and enhance_experience, so the route can
    handle all three the same way.
    """
    if not job_description or not job_description.strip():
        return {"success": False, "error": "No job description provided"}

    parsed_result = parse_background(background_text)
    if not parsed_result["success"]:
        # parse_background failed outright (e.g. no background text at
        # all) - nothing to tailor, so propagate its error rather than
        # trying to generate a draft from a blank parse.
        return {"success": False, "error": parsed_result["error"]}

    parsed = parsed_result["data"]

    # Missing keywords steer the tailoring calls toward terms the job
    # description uses that the background doesn't yet - computed against
    # the PRE-tailoring parsed background (calculate_ats_score_for_draft
    # doesn't need or use ai_description). An empty-vocabulary edge case
    # (e.g. a background with no usable words at all) shouldn't block the
    # whole draft, so fall back to no keyword hints rather than raising.
    try:
        ats_result = calculate_ats_score_for_draft(parsed, job_description)
        missing_keywords = ats_result.get("missing_keywords", [])
    except Exception as e:
        print("Error computing missing keywords for draft tailoring:", e)
        missing_keywords = []

    summary_result, experience_bullets = asyncio.run(
        _tailor_all(parsed, job_description, missing_keywords)
    )

    # Tailored summary falls back to the ORIGINAL parsed summary text (not
    # blank) on failure - unlike a full structured object, raw summary text
    # is still usable even if the tailoring call itself failed.
    tailored_summary = summary_result["data"] if summary_result["success"] else (parsed.get("summary") or "")

    experiences_out = [
        {**exp, "ai_description": bullets}
        for exp, bullets in zip(parsed.get("experiences") or [], experience_bullets)
    ]

    draft = DraftResponse(
        name=parsed.get("name"),
        title=parsed.get("title"),
        email=parsed.get("email"),
        phone=parsed.get("phone"),
        website=parsed.get("website"),
        summary=tailored_summary,
        experiences=experiences_out,
        education=parsed.get("education") or [],
        skills=parsed.get("skills") or [],
        certifications=parsed.get("certifications") or [],
        awards=parsed.get("awards") or [],
        warnings=_build_warnings(parsed),
    )

    return {"success": True, "data": draft.model_dump()}
