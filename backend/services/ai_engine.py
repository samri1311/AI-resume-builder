from groq import Groq, AsyncGroq
from backend.core.config import GROQ_API_KEY, GROQ_MODEL
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
