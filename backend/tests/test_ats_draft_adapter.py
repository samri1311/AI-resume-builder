# backend/tests/test_ats_draft_adapter.py
"""Phase B: calculate_ats_score_for_draft should score a not-yet-saved
draft (a plain dict) exactly the same way calculate_ats_score already
scores a saved models.Resume - same fixtures/style as test_ats.py, just
handed a dict instead of a FakeResume object."""

from backend.services.ats_engine import calculate_ats_score, calculate_ats_score_for_draft


PARSED_BACKGROUND = {
    "name": "Jordan Rivera",
    "title": None,
    "email": None,
    "phone": None,
    "website": None,
    "summary": "Python developer",
    "experiences": [{"job_title": "Engineer", "company": "Test Corp", "description": "Built REST APIs using FastAPI"}],
    "education": [{"degree": "B.Tech", "field_of_study": "Computer Science"}],
    "skills": ["Python", "FastAPI", "SQL"],
    "certifications": [],
    "awards": [],
}


def test_draft_adapter_matches_calculate_ats_score_for_well_matched_job():
    job_description = "Looking for a Python developer with FastAPI and SQL experience"

    result = calculate_ats_score_for_draft(PARSED_BACKGROUND, job_description)

    assert 0 <= result["ats_score"] <= 100
    assert set(result["matched_skills"]) == {"python", "fastapi", "sql"}
    assert isinstance(result["missing_keywords"], list)
    assert isinstance(result["suggestions"], list)


def test_draft_adapter_flags_unrelated_job_description():
    job_description = "Looking for a Java developer with Kubernetes and AWS experience"

    result = calculate_ats_score_for_draft(PARSED_BACKGROUND, job_description)

    assert result["matched_skills"] == []
    assert result["skill_match_score"] == 0
    assert "Improve alignment with job description" in result["suggestions"]


def test_draft_adapter_handles_missing_optional_fields_without_crashing():
    sparse = {
        "name": "Alex",
        "summary": None,
        "experiences": [],
        "education": [],
        "skills": [],
        "certifications": [],
        "awards": [],
    }

    result = calculate_ats_score_for_draft(sparse, "Any job description here")

    assert result["ats_score"] >= 0
    assert result["matched_skills"] == []


def test_draft_adapter_ignores_blank_skill_entries():
    with_blank_skill = dict(PARSED_BACKGROUND, skills=["Python", "", None, "SQL"])

    # Would raise AttributeError (None has no .lower()) if the blank/None
    # entries weren't filtered out before being wrapped as skill shims.
    result = calculate_ats_score_for_draft(with_blank_skill, "Python and SQL developer wanted")

    assert "python" in result["matched_skills"]
    assert "sql" in result["matched_skills"]


def test_draft_adapter_output_matches_calculate_ats_score_directly():
    # Same underlying data, expressed as a FakeResume vs. as a dict, should
    # produce identical scores - proving the shim is a faithful adapter,
    # not a parallel/divergent implementation.
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

    job_description = "Looking for a Python developer with FastAPI and SQL experience"

    via_orm_shape = calculate_ats_score(FakeResume(), job_description)
    via_draft_dict = calculate_ats_score_for_draft(PARSED_BACKGROUND, job_description)

    assert via_orm_shape == via_draft_dict
