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


def test_calculate_ats_score_flags_unrelated_job_description():
    resume = FakeResume()
    job_description = "Looking for a Java developer with Kubernetes and AWS experience"

    result = calculate_ats_score(resume, job_description)

    # None of the resume's skills appear in this unrelated job description
    assert result["matched_skills"] == []
    assert result["skill_match_score"] == 0
    assert "Improve alignment with job description" in result["suggestions"]
