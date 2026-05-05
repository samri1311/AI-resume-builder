# backend/tests/test_ai.py

from backend.services.ai_engine import enhance_experience

text = "Worked on APIs and backend development"

result = enhance_experience(text)

print(result)