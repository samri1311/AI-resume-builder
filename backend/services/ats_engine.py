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
def _skill_present(skill: str, text: str) -> bool:
    """Whole-word-ish presence check: True only if `skill` appears in
    `text` with a non-alphanumeric character (or the string's edge) on
    both sides.

    Phase E fix: plain substring matching (`skill in text`) let a short
    skill like "r", "go", or "c" falsely "match" inside an unrelated word
    (e.g. "r" inside "reporting"). A plain `\\b` word-boundary regex isn't
    quite right either, since it doesn't handle skills that end in a
    symbol (e.g. "c++", "c#") - `\\b` requires a transition between a word
    and non-word character, which never happens right after a "+". This
    instead just checks that neither neighboring character is
    alphanumeric, regardless of what the skill itself starts/ends with.
    """
    if not skill:
        return False
    pattern = r'(?<![a-z0-9])' + re.escape(skill) + r'(?![a-z0-9])'
    return re.search(pattern, text) is not None


def compute_skill_match(resume, job_desc: str):
    jd = job_desc.lower()
    resume_skills = [s.skill_name.lower() for s in resume.skills]

    matched = [s for s in resume_skills if _skill_present(s, jd)]
    missing = [s for s in resume_skills if s not in matched]

    total = len(resume_skills) or 1

    return {
        "score": len(matched) / total,
        "matched": matched,
        "missing_from_jd": missing
    }


# ---------------- RELEVANT EXPERIENCE ----------------
# Phase E: pic-1's results screen only ever showed bare percentages with no
# explanation attached. This adds the third "why" signal the redesigned UI
# needs - how many of the resume's experience entries are actually relevant
# to this job description - using the same TF-IDF similarity approach
# already used resume-wide, just applied per experience entry instead.
# Deliberately NOT semantic (see conversation) - this stays keyword/TF-IDF
# based, consistent with the rest of the engine.
RELEVANT_EXPERIENCE_THRESHOLD = 0.15


def compute_relevant_experience(resume, job_desc_clean: str, threshold: float = RELEVANT_EXPERIENCE_THRESHOLD):
    experiences = resume.experiences or []
    total = len(experiences)
    if total == 0:
        return {"relevant": 0, "total": 0}

    relevant_count = 0
    for exp in experiences:
        text_parts = []
        if getattr(exp, "ai_description", None):
            text_parts.extend(exp.ai_description)
        elif getattr(exp, "description", None):
            text_parts.append(exp.description)

        exp_text = clean_text(" ".join(text_parts))
        if not exp_text.strip():
            continue

        try:
            score = compute_similarity(exp_text, job_desc_clean)
        except ValueError:
            # TfidfVectorizer raises "empty vocabulary" if a description
            # has nothing left after stopword removal (e.g. just one
            # common word) - treat that as "not relevant" rather than
            # crashing the whole ATS check over one thin entry.
            score = 0.0

        if score >= threshold:
            relevant_count += 1

    return {"relevant": relevant_count, "total": total}


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
# Phase E: suggestions used to be generic canned lines with no connection
# to the actual numbers shown above them. Now every suggestion that can
# reference a real count does - "Improve alignment with job description" is
# kept as an exact leading phrase (existing tests key off it) with the
# actual similarity percentage appended, not replaced.
def generate_suggestions(
    missing_keywords,
    similarity_score,
    skills_matched: int = 0,
    skills_total: int = 0,
    experience_relevant: int = 0,
    experience_total: int = 0,
):
    suggestions = []

    if similarity_score < 0.5:
        suggestions.append(
            f"Improve alignment with job description - overall wording only "
            f"matches about {round(similarity_score * 100)}% of it right now."
        )

    if skills_total:
        if skills_matched < skills_total:
            suggestions.append(
                f"{skills_matched} of {skills_total} listed skills appear in this "
                f"job description - review whether the other {skills_total - skills_matched} "
                f"are still worth including for this role."
            )
        else:
            suggestions.append(
                f"All {skills_total} listed skills appear in this job description - good match."
            )

    if missing_keywords:
        suggestions.append(
            f"Add these keywords: {', '.join(missing_keywords[:5])}"
        )

    if experience_total:
        if experience_relevant < experience_total:
            suggestions.append(
                f"Only {experience_relevant} of {experience_total} experience entries "
                f"closely relate to this job description - consider emphasizing the "
                f"more relevant ones."
            )
        else:
            suggestions.append(
                f"All {experience_total} experience entries relate well to this job description."
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
    skills_matched = len(skill_data["matched"])
    skills_total = skills_matched + len(skill_data["missing_from_jd"])

    # 3. Missing Keywords
    missing_keywords = find_missing_keywords(resume_text, job_desc_clean)

    # 4. Relevant Experience (Phase E)
    experience_data = compute_relevant_experience(resume, job_desc_clean)

    # 5. Final Score
    final_score = (0.7 * similarity_score) + (0.3 * skill_data["score"])

    # 6. Suggestions
    suggestions = generate_suggestions(
        missing_keywords,
        similarity_score,
        skills_matched=skills_matched,
        skills_total=skills_total,
        experience_relevant=experience_data["relevant"],
        experience_total=experience_data["total"],
    )

    return {
        "ats_score": round(final_score * 100, 2),
        "similarity_score": round(similarity_score * 100, 2),
        "skill_match_score": round(skill_data["score"] * 100, 2),
        "matched_skills": skill_data["matched"],
        "matched_skills_count": skills_matched,
        "total_skills_count": skills_total,
        "missing_keywords": missing_keywords[:10],
        "relevant_experience_count": experience_data["relevant"],
        "total_experience_count": experience_data["total"],
        "suggestions": suggestions
    }


# ---------------------------------------------------------------------------
# Phase B (pivot: paste a job description + background -> tailored draft).
#
# calculate_ats_score() above reads resume.summary / .experiences[].description
# / .ai_description / .education[].degree / .field_of_study / .skills[].skill_name
# off whatever object it's handed - it was written against a saved
# models.Resume, but never actually checks that it IS one. Before a draft is
# saved there's no such object yet, only the plain dict parse_background()
# returns (see backend/schemas/draft.py). Rather than duplicate the
# scoring/matching logic for that case, these small shim classes just expose
# the same attributes calculate_ats_score already reads, built from that
# dict, so the exact same scoring logic runs unchanged either way.
# ---------------------------------------------------------------------------

class _ShimExperience:
    def __init__(self, description=None):
        self.description = description
        self.ai_description = []  # a draft has no AI-enhanced bullets yet


class _ShimEducation:
    def __init__(self, degree=None, field_of_study=None):
        self.degree = degree
        self.field_of_study = field_of_study


class _ShimSkill:
    def __init__(self, skill_name):
        self.skill_name = skill_name


class _ShimResume:
    def __init__(self, summary, experiences, education, skills):
        self.summary = summary
        self.experiences = experiences
        self.education = education
        self.skills = skills


def _resume_shim_from_parsed_background(parsed_background: dict) -> _ShimResume:
    """parsed_background = a ParsedBackground.model_dump()-shaped dict, as
    returned by ai_engine.parse_background()'s "data" field."""
    return _ShimResume(
        summary=parsed_background.get("summary"),
        experiences=[
            _ShimExperience(description=exp.get("description"))
            for exp in parsed_background.get("experiences") or []
        ],
        education=[
            _ShimEducation(
                degree=edu.get("degree"),
                field_of_study=edu.get("field_of_study"),
            )
            for edu in parsed_background.get("education") or []
        ],
        skills=[
            _ShimSkill(skill_name=skill)
            for skill in parsed_background.get("skills") or []
            if skill  # a blank/None entry would otherwise crash .lower() in compute_skill_match
        ],
    )


def calculate_ats_score_for_draft(parsed_background: dict, job_description: str) -> dict:
    """Same return shape as calculate_ats_score, but for a not-yet-saved
    draft (a ParsedBackground dict) rather than a persisted models.Resume.

    Used to find which of the job description's keywords the draft is
    still missing, so the Phase B tailoring calls can be told what to
    naturally work in - see ai_engine.enhance_experience_for_job and
    generate_tailored_summary's missing_keywords parameter.
    """
    shim = _resume_shim_from_parsed_background(parsed_background)
    return calculate_ats_score(shim, job_description)