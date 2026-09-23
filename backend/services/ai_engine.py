from groq import Groq, AsyncGroq
from backend.core.config import GROQ_API_KEY, GROQ_MODEL
from backend.schemas.draft import ParsedBackground
import json
import re

# Two clients: `client` for the existing synchronous call sites (kept so the
# /ai/enhance route and the existing tests don't have to change), and
# `async_client` for resume_service's concurrent enhancement of several
# experience entries at once (see enhance_experience_async).
client = Groq(api_key=GROQ_API_KEY)
async_client = AsyncGroq(api_key=GROQ_API_KEY)

ACTION_VERBS = [
    "Developed", "Designed", "Implemented", "Optimized",
    "Built", "Led", "Improved", "Automated", "Enhanced",
    "Delivered", "Engineered", "Collaborated"
]


def _build_system_prompt(style: str) -> str:
    # 🔥 Style-based prompts
    if style == "impactful":
        return f"""
        You are a senior resume expert.

        - Use action verbs: {", ".join(ACTION_VERBS)}
        - Focus on achievements
        - Add measurable impact (%/numbers)
        """

    if style == "concise":
        return f"""
        Generate 2-3 short bullet points.
        Use action verbs: {", ".join(ACTION_VERBS)}
        Keep it crisp.
        """

    return f"""
    You are a professional resume writer.

    - Use action verbs: {", ".join(ACTION_VERBS)}
    - Keep it clear and ATS-friendly
    """


def _build_user_prompt(text: str) -> str:
    return f"""
    Convert the following into bullet points.

    Text:
    {text}

    Output format (STRICT JSON):
    {{
      "bullets": ["...", "...", "..."]
    }}

    Return ONLY valid JSON.
    Do not include markdown.
    Do not include ```json.
    """


def _parse_bullets(content: str) -> list:
    print("Raw AI Response:\n", content)

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return [line.strip() for line in content.split("\n") if line.strip()]

    json_str = match.group()

    # Remove trailing commas (IMPORTANT FIX)
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    try:
        parsed = json.loads(json_str)
        bullets = parsed.get("bullets", [])

        if not isinstance(bullets, list):
            bullets = [str(bullets)]
        return bullets
    except Exception:
        return [line.strip() for line in content.split("\n") if line.strip()]


def enhance_experience(text: str, style: str = "professional") -> dict:
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _build_system_prompt(style)},
                {"role": "user", "content": _build_user_prompt(text)}
            ],
            temperature=0.5
        )

        bullets = _parse_bullets(response.choices[0].message.content)

        return {
            "success": True,
            "data": bullets
        }

    except Exception as e:
        print("Error:", e)
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


async def enhance_experience_async(text: str, style: str = "professional") -> dict:
    """Same as enhance_experience, but awaits the Groq call instead of
    blocking. Used by resume_service to enhance several experience entries
    concurrently instead of one Groq round-trip at a time."""
    try:
        response = await async_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _build_system_prompt(style)},
                {"role": "user", "content": _build_user_prompt(text)}
            ],
            temperature=0.5
        )

        bullets = _parse_bullets(response.choices[0].message.content)

        return {
            "success": True,
            "data": bullets
        }

    except Exception as e:
        print("Error:", e)
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


# ---------------------------------------------------------------------------
# Phase A (pivot: paste a job description + background -> tailored draft).
# Turns freeform background text (an old resume, a LinkedIn export, rough
# notes) into a structured draft the frontend can load into the existing
# form for review. See backend/schemas/draft.py for the output shape.
# ---------------------------------------------------------------------------

def _build_background_parse_prompt() -> str:
    return """
    You are an expert resume parser. The user will give you freeform text
    describing their career background - this could be an existing resume,
    a LinkedIn export, or rough notes. Extract a structured resume from it.

    Return STRICT JSON matching exactly this shape (use null or an empty
    list for anything not present in the text - never invent details):
    {
      "name": string or null,
      "title": string or null,
      "email": string or null,
      "phone": string or null,
      "website": string or null,
      "summary": string or null,
      "experiences": [
        {"job_title": string or null, "company": string or null, "location": string or null,
         "start_date": string or null, "end_date": string or null, "description": string or null,
         "is_current": true or false}
      ],
      "education": [
        {"college": string or null, "degree": string or null, "field_of_study": string or null,
         "start_year": string or null, "end_year": string or null, "details": string or null}
      ],
      "skills": [string, ...],
      "certifications": [
        {"name": string or null, "issuing_organization": string or null, "year": string or null}
      ],
      "awards": [
        {"title": string or null, "year": string or null}
      ]
    }

    Rules:
    - Only extract what's actually present in the text. Never invent or guess details.
    - "description" for an experience is the person's own words, lightly
      cleaned up (fix obvious typos, tidy line breaks) - not rewritten or embellished.
    - Keep dates in whatever format the source text uses (e.g. "Jan 2022", "2019").
    - Return ONLY the JSON object. No markdown, no commentary, no ```json fences.
    """


def _parse_json_object(content: str) -> dict:
    """Same tolerant-extraction approach as _parse_bullets (regex out the
    JSON block, drop trailing commas, then json.loads), generalized to a
    full object instead of a {"bullets": [...]} shape. Returns {} - not a
    line-split fallback - when nothing usable can be found, since there's
    no sane way to reconstruct a structured resume from unparseable text;
    callers turn that into a fully-blank ParsedBackground."""
    print("Raw AI Response:\n", content)

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return {}

    json_str = match.group()
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    try:
        parsed = json.loads(json_str)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def parse_background(background_text: str) -> dict:
    """Phase A: turn freeform background text into a structured draft.

    Returns {"success": True/False, "data": <ParsedBackground as a dict>,
    "error": str (only on failure)} - the same success/data/error shape
    enhance_experience already uses, so callers can handle both the same
    way. "data" is ALWAYS a fully-shaped ParsedBackground dict (every field
    present, defaulting to None/[] ) even on failure, so a caller never has
    to special-case a missing key - only whether success is True.

    Note: success=True does not guarantee anything was actually extracted -
    if the model's response couldn't be parsed as JSON at all, this still
    reports success (the Groq call itself worked) but "data" comes back
    fully blank. This mirrors how enhance_experience already treats an
    unparseable response as still "successful" rather than an error.
    """
    if not background_text or not background_text.strip():
        return {
            "success": False,
            "error": "No background text provided",
            "data": ParsedBackground().model_dump(),
        }

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _build_background_parse_prompt()},
                {"role": "user", "content": background_text}
            ],
            # Lower than enhancement's 0.5 - extraction should be literal
            # and consistent, not creative.
            temperature=0.2
        )

        raw = _parse_json_object(response.choices[0].message.content)

        try:
            validated = ParsedBackground(**raw)
        except Exception:
            # The model returned JSON, but not shaped closely enough for
            # ParsedBackground to coerce (e.g. a string where a list was
            # expected) - fall back to a blank draft rather than raising,
            # same philosophy as the JSON-parse failure path above.
            validated = ParsedBackground()

        return {
            "success": True,
            "data": validated.model_dump()
        }

    except Exception as e:
        print("Error parsing background:", e)
        return {
            "success": False,
            "error": str(e),
            "data": ParsedBackground().model_dump()
        }


# ---------------------------------------------------------------------------
# Phase B (pivot: paste a job description + background -> tailored draft).
# Extends the existing enhancement call to also take the target job
# description into account, and adds a new tailored-summary generator.
# Both accept an optional missing_keywords list (see
# ats_engine.calculate_ats_score_for_draft) - terms the job description uses
# that the draft doesn't yet, to naturally work in where they genuinely fit.
# ---------------------------------------------------------------------------

def _build_tailoring_system_prompt(style: str, job_description: str, missing_keywords: list = None) -> str:
    base = _build_system_prompt(style)

    keyword_hint = ""
    if missing_keywords:
        keyword_hint = f"""
    The job description also uses these terms, which the candidate's background
    doesn't currently reflect - work them in naturally ONLY where they genuinely
    fit what the person actually did. Never fabricate experience just to use a
    keyword: {", ".join(missing_keywords[:8])}."""

    return f"""{base}

    You are tailoring this specifically for the job description below. Emphasize
    the parts of the candidate's experience that are most relevant to it, and
    mirror its terminology where it genuinely matches what they did - don't
    invent skills or achievements the person didn't describe.

    Job description:
    {job_description}
    {keyword_hint}
    """


def enhance_experience_for_job(
    text: str, job_description: str, style: str = "professional", missing_keywords: list = None
) -> dict:
    """Same contract as enhance_experience (success/data/error, data = a
    list of bullets), but tailored against a specific job description
    instead of just a writing style. Reuses _build_user_prompt as-is - the
    job description lives in the system prompt, so the user turn stays
    focused on the experience text itself."""
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _build_tailoring_system_prompt(style, job_description, missing_keywords)},
                {"role": "user", "content": _build_user_prompt(text)}
            ],
            temperature=0.5
        )

        bullets = _parse_bullets(response.choices[0].message.content)

        return {
            "success": True,
            "data": bullets
        }

    except Exception as e:
        print("Error:", e)
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


async def enhance_experience_for_job_async(
    text: str, job_description: str, style: str = "professional", missing_keywords: list = None
) -> dict:
    """Async twin of enhance_experience_for_job, for the same reason
    enhance_experience_async exists: tailoring several experiences at once
    (Phase C) should run concurrently, not one Groq round-trip at a time."""
    try:
        response = await async_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _build_tailoring_system_prompt(style, job_description, missing_keywords)},
                {"role": "user", "content": _build_user_prompt(text)}
            ],
            temperature=0.5
        )

        bullets = _parse_bullets(response.choices[0].message.content)

        return {
            "success": True,
            "data": bullets
        }

    except Exception as e:
        print("Error:", e)
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


def _build_summary_system_prompt(job_description: str, missing_keywords: list = None) -> str:
    keyword_hint = ""
    if missing_keywords:
        keyword_hint = f"""
    Where it genuinely fits, you may reference these terms from the job
    description: {", ".join(missing_keywords[:8])}. Never fabricate experience
    or skills just to use them."""

    return f"""
    You are a professional resume writer. Write a single, concise professional
    summary (2-3 sentences) that connects this candidate's background to the
    specific job description below. Be specific and honest - use only what's
    actually in their background, never invent experience or skills.

    Job description:
    {job_description}
    {keyword_hint}
    """


def _build_summary_user_prompt(background_summary: str) -> str:
    text = background_summary.strip() if background_summary else ""
    text = text or "(No existing summary was provided - infer a short one from the candidate's experience if there's enough to go on, otherwise keep it general.)"

    return f"""
    Candidate's existing summary or background notes:
    {text}

    Output format (STRICT JSON):
    {{
      "summary": "..."
    }}

    Return ONLY valid JSON. No markdown, no ```json fences.
    """


def _parse_summary(content: str) -> str:
    """Same tolerant JSON extraction as _parse_bullets/_parse_json_object,
    but for a single string field. Unlike parse_background's blank-draft
    fallback, falling back to the raw (stripped) response text here is a
    reasonable degrade - a plain-text summary the model wrote outside the
    requested JSON shape is still a perfectly usable summary, just not
    wrapped the way we asked for."""
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return content.strip()

    json_str = match.group()
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    try:
        parsed = json.loads(json_str)
        summary = parsed.get("summary", "")
        return str(summary).strip() if summary else content.strip()
    except Exception:
        return content.strip()


def generate_tailored_summary(background_summary: str, job_description: str, missing_keywords: list = None) -> dict:
    """Returns {"success": bool, "data": <summary string>, "error": str (on
    failure)}. "data" is "" only on failure - a successful call always
    returns some non-empty text (see _parse_summary's fallback)."""
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _build_summary_system_prompt(job_description, missing_keywords)},
                {"role": "user", "content": _build_summary_user_prompt(background_summary)}
            ],
            temperature=0.5
        )

        summary = _parse_summary(response.choices[0].message.content)

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        print("Error:", e)
        return {
            "success": False,
            "error": str(e),
            "data": ""
        }


async def generate_tailored_summary_async(background_summary: str, job_description: str, missing_keywords: list = None) -> dict:
    """Async twin of generate_tailored_summary, so Phase C can generate the
    summary concurrently with the per-experience tailoring calls instead of
    waiting for them to finish first."""
    try:
        response = await async_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _build_summary_system_prompt(job_description, missing_keywords)},
                {"role": "user", "content": _build_summary_user_prompt(background_summary)}
            ],
            temperature=0.5
        )

        summary = _parse_summary(response.choices[0].message.content)

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        print("Error:", e)
        return {
            "success": False,
            "error": str(e),
            "data": ""
        }
