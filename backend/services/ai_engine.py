from groq import Groq
from backend.core.config import GROQ_API_KEY
import json
import re

client = Groq(api_key=GROQ_API_KEY)

ACTION_VERBS = [
    "Developed", "Designed", "Implemented", "Optimized",
    "Built", "Led", "Improved", "Automated", "Enhanced",
    "Delivered", "Engineered", "Collaborated"
]


def enhance_experience(text: str, style: str = "professional") -> dict:
    try:
        # 🔥 Style-based prompts
        if style == "impactful":
            system_prompt = f"""
            You are a senior resume expert.

            - Use action verbs: {", ".join(ACTION_VERBS)}
            - Focus on achievements
            - Add measurable impact (%/numbers)
            """

        elif style == "concise":
            system_prompt = f"""
            Generate 2-3 short bullet points.
            Use action verbs: {", ".join(ACTION_VERBS)}
            Keep it crisp.
            """

        else:
            system_prompt = f"""
            You are a professional resume writer.

            - Use action verbs: {", ".join(ACTION_VERBS)}
            - Keep it clear and ATS-friendly
            """

        prompt = f"""
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

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )

        content = response.choices[0].message.content
        print("Raw AI Response:\n", content)

        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            json_str = match.group()

            # Remove trailing commas (IMPORTANT FIX)
            json_str = re.sub(r",\s*}", "}", json_str)
            json_str = re.sub(r",\s*]", "]", json_str)
            try:
                parsed = json.loads(json_str)
                bullets = parsed.get("bullets", [])

                if not isinstance(bullets, list):
                    bullets = [str(bullets)]
            except Exception:
                bullets = [line.strip() for line in content.split("\n") if line.strip()]
                
        else:
            bullets = [line.strip() for line in content.split("\n") if line.strip()]
            
    

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