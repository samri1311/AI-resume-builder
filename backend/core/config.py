# Configuration and settings
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./resumes.db")

# Which Groq model powers AI enhancement. Was hardcoded in ai_engine.py —
# moved here so a model deprecation/rename only needs a .env change, not a
# code change.
#
# NOTE: llama-3.1-8b-instant moved to Groq's Enterprise-only tier on
# 2026-08-16 and is no longer reachable with a free/Developer API key —
# using it now fails with a 404 "model_not_found" error. openai/gpt-oss-20b
# is on Groq's free tier (30 req/min, 1,000 req/day at time of writing) and
# is fast/cheap enough for this app's parsing + tailoring calls.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
