# backend/tests/test_ats.py
"""Tests for backend.services.ats_engine.calculate_ats_score.

Same fake resume fixtures as the original script, now with real assertions
instead of a print statement.
"""

from backend.services.ats_engine import calculate_ats_score


class FakeSkill:
    def __init__(self, name):
        self.skill_name = name


class FakeExp:
    def __init__(self, desc):
        self.description = desc
        self.ai_description = []


class FakeEdu:
    def __init__(self):
        self.degree = "B.Tech"
        self.field_of_study = "Computer Science"


class FakeResume:
    def __init__(self):
        self.summary = "Python developer"
        self.skills = [FakeSkill("Python"), FakeSkill("FastAPI"), FakeSkill("SQL")]
        self.experiences = [FakeExp("Built REST APIs using FastAPI")]
        self.education = [FakeEdu()]


def test_calculate_ats_score_for_a_well_matched_resume():
    resume = FakeResume()
    job_description = "Looking for a Python developer with FastAPI and SQL experience"

    result = calculate_ats_score(resume, job_description)

    assert 0 <= result["ats_score"] <= 100
    assert 0 <= result["similarity_score"] <= 100
    assert 0 <= result["skill_match_score"] <= 100
    assert set(result["matched_skills"]) == {"python", "fastapi", "sql"}
    assert isinstance(result["missing_keywords"], list)
    assert isinstance(result["suggestions"], list)
    assert result["suggestions"]  # always includes at least the generic tips

    # Phase E: the counts behind the percentages.
    assert result["matched_skills_count"] == 3
    assert result["total_skills_count"] == 3
    assert result["total_experience_count"] == 1
    assert 0 <= result["relevant_experience_count"] <= result["total_experience_count"]


def test_calculate_ats_score_flags_unrelated_job_description():
    resume = FakeResume()
    job_description = "Looking for a Java developer with Kubernetes and AWS experience"

    result = calculate_ats_score(resume, job_description)

    # None of the resume's skills appear in this unrelated job description
    assert result["matched_skills"] == []
    assert result["skill_match_score"] == 0
    assert result["matched_skills_count"] == 0
    assert result["total_skills_count"] == 3
    assert any("Improve alignment with job description" in s for s in result["suggestions"])


def test_short_skill_names_dont_false_match_inside_unrelated_words():
    # Phase E fix: a skill like "R" or "Go" used to match as a plain
    # substring anywhere it appeared, including inside unrelated words
    # ("r" inside "reporting", "go" inside "google").
    resume = FakeResume()
    resume.skills = [FakeSkill("R"), FakeSkill("Go")]

    job_description = "We use Google Analytics for reporting and marketing insights."

    result = calculate_ats_score(resume, job_description)

    assert result["matched_skills"] == []
    assert result["matched_skills_count"] == 0


def test_short_skill_names_do_match_as_whole_words():
    resume = FakeResume()
    resume.skills = [FakeSkill("R"), FakeSkill("Go")]

    job_description = "Looking for an engineer who knows R and Go for backend services."

    result = calculate_ats_score(resume, job_description)

    assert set(result["matched_skills"]) == {"r", "go"}
    assert result["matched_skills_count"] == 2
