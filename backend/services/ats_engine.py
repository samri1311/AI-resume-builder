# ATS engine for resume optimization
import re
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ---------------- TEXT CLEANING ----------------
def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text


# ---------------- EXTRACT RESUME TEXT ----------------
def extract_resume_text(resume) -> str:
    parts = []

    if resume.summary:
        parts.append(resume.summary)

    for exp in resume.experiences:
        if exp.ai_description:
            parts.extend(exp.ai_description)
        elif exp.description:
            parts.append(exp.description)

    for edu in resume.education:
        parts.append(f"{edu.degree} {edu.field_of_study}")

    skills = [skill.skill_name for skill in resume.skills]
    parts.extend(skills)

    return clean_text(" ".join(parts))


# ---------------- TF-IDF SIMILARITY ----------------
def compute_similarity(resume_text: str, job_desc: str) -> float:
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform([resume_text, job_desc])
    score = cosine_similarity(tfidf[0:1], tfidf[1:2])
    return float(score[0][0])


# ---------------- SKILL MATCH ----------------
def compute_skill_match(resume, job_desc: str):
    jd = job_desc.lower()
    resume_skills = [s.skill_name.lower() for s in resume.skills]

    matched = [s for s in resume_skills if s in jd]
    missing = [s for s in resume_skills if s not in jd]

    total = len(resume_skills) or 1

    return {
        "score": len(matched) / total,
        "matched": matched,
        "missing_from_jd": missing
    }


# ---------------- KEYWORD EXTRACTION ----------------
def extract_keywords(text: str, top_n: int = 10):
    vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
    tfidf_matrix = vectorizer.fit_transform([text])

    scores = zip(vectorizer.get_feature_names_out(), tfidf_matrix.toarray()[0])
    sorted_keywords = sorted(scores, key=lambda x: x[1], reverse=True)

    return [word for word, _ in sorted_keywords[:top_n]]


# ---------------- MISSING KEYWORDS ----------------
def find_missing_keywords(resume_text: str, job_desc: str):
    jd_keywords = extract_keywords(job_desc)
    resume_words = set(resume_text.split())

    missing = [kw for kw in jd_keywords if kw not in resume_words]

    return missing


# ---------------- SUGGESTIONS ENGINE ----------------
def generate_suggestions(missing_keywords, similarity_score):
    suggestions = []

    if similarity_score < 0.5:
        suggestions.append("Improve alignment with job description")

    if missing_keywords:
        suggestions.append(
            f"Add these keywords: {', '.join(missing_keywords[:5])}"
        )

    suggestions.append("Use more action verbs")
    suggestions.append("Add measurable achievements (%, numbers)")

    return suggestions


# ---------------- FINAL ATS ENGINE ----------------
def calculate_ats_score(resume, job_description: str):
    resume_text = extract_resume_text(resume)
    job_desc_clean = clean_text(job_description)

    # 1. Similarity
    similarity_score = compute_similarity(resume_text, job_desc_clean)

    # 2. Skill Match
    skill_data = compute_skill_match(resume, job_description)

    # 3. Missing Keywords
    missing_keywords = find_missing_keywords(resume_text, job_desc_clean)

    # 4. Final Score
    final_score = (0.7 * similarity_score) + (0.3 * skill_data["score"])

    # 5. Suggestions
    suggestions = generate_suggestions(missing_keywords, similarity_score)

    return {
        "ats_score": round(final_score * 100, 2),
        "similarity_score": round(similarity_score * 100, 2),
        "skill_match_score": round(skill_data["score"] * 100, 2),
        "matched_skills": skill_data["matched"],
        "missing_keywords": missing_keywords[:10],
        "suggestions": suggestions
    }