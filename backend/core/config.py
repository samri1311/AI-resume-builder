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
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
