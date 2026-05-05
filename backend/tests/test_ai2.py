from backend.services.ai_engine import enhance_experience

text = "Worked on backend APIs and improved performance"

print("\n--- PROFESSIONAL ---")
print(enhance_experience(text, style="professional"))

print("\n--- IMPACTFUL ---")
print(enhance_experience(text, style="impactful"))

print("\n--- CONCISE ---")
print(enhance_experience(text, style="concise"))