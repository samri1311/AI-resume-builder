# backend/tests/test_draft_service.py
"""Phase C: draft_service.generate_draft orchestrates parse_background,
the Phase B tailoring calls, and calculate_ats_score_for_draft. These
tests mock all three at the point draft_service imports them (its own
module namespace) - Groq mechanics themselves are already covered by
test_background_parser.py and test_job_tailoring.py, so these tests only
prove the orchestration/assembly logic is correct.
"""

import time
from unittest.mock import patch

from backend.services import draft_service


JOB_DESCRIPTION = "Looking for a backend engineer experienced with Kubernetes and gRPC."


def _parsed_background(**overrides):
    base = {
        "name": "Jordan Rivera",
        "title": None,
        "email": "jordan@example.com",
        "phone": None,
        "website": None,
        "summary": "Backend developer.",
        "experiences": [
            {"job_title": "Engineer", "company": "Test Corp", "description": "Ran backend services."}
        ],
        "education": [],
        "skills": ["Python"],
        "certifications": [],
        "awards": [],
    }
    base.update(overrides)
    return base


def test_generate_draft_requires_job_description():
    result = draft_service.generate_draft("", "Some background text.")

    assert result["success"] is False
    assert "job description" in result["error"].lower()


@patch("backend.services.draft_service.parse_background")
def test_generate_draft_propagates_parse_background_failure(mock_parse):
    mock_parse.return_value = {"success": False, "error": "No background text provided", "data": {}}

    result = draft_service.generate_draft(JOB_DESCRIPTION, "")

    assert result["success"] is False
    assert result["error"] == "No background text provided"


@patch("backend.services.draft_service.calculate_ats_score_for_draft")
@patch("backend.services.draft_service.generate_tailored_summary_async")
@patch("backend.services.draft_service.enhance_experience_for_job_async")
@patch("backend.services.draft_service.parse_background")
def test_generate_draft_happy_path_assembles_full_response(
    mock_parse, mock_enhance, mock_summary, mock_ats
):
    mock_parse.return_value = {"success": True, "data": _parsed_background()}
    mock_ats.return_value = {"missing_keywords": ["kubernetes", "grpc"]}

    async def fake_enhance(text, job_description, missing_keywords=None):
        return {"success": True, "data": ["Deployed services on Kubernetes."]}

    async def fake_summary(background_summary, job_description, missing_keywords=None):
        return {"success": True, "data": "Backend engineer with Kubernetes experience."}

    mock_enhance.side_effect = fake_enhance
    mock_summary.side_effect = fake_summary

    result = draft_service.generate_draft(JOB_DESCRIPTION, "some background text")

    assert result["success"] is True
    data = result["data"]
    assert data["name"] == "Jordan Rivera"
    assert data["summary"] == "Backend engineer with Kubernetes experience."
    assert len(data["experiences"]) == 1
    assert data["experiences"][0]["ai_description"] == ["Deployed services on Kubernetes."]
    # The original parsed description is preserved alongside the tailored bullets
    assert data["experiences"][0]["description"] == "Ran backend services."
    assert data["warnings"] == []


@patch("backend.services.draft_service.calculate_ats_score_for_draft")
@patch("backend.services.draft_service.generate_tailored_summary_async")
@patch("backend.services.draft_service.enhance_experience_for_job_async")
@patch("backend.services.draft_service.parse_background")
def test_generate_draft_threads_missing_keywords_into_tailoring_calls(
    mock_parse, mock_enhance, mock_summary, mock_ats
):
    mock_parse.return_value = {"success": True, "data": _parsed_background()}
    mock_ats.return_value = {"missing_keywords": ["kubernetes", "grpc"]}

    captured = {}

    async def fake_enhance(text, job_description, missing_keywords=None):
        captured["experience_keywords"] = missing_keywords
        return {"success": True, "data": ["A bullet."]}

    async def fake_summary(background_summary, job_description, missing_keywords=None):
        captured["summary_keywords"] = missing_keywords
        return {"success": True, "data": "A summary."}

    mock_enhance.side_effect = fake_enhance
    mock_summary.side_effect = fake_summary

    draft_service.generate_draft(JOB_DESCRIPTION, "some background text")

    assert captured["experience_keywords"] == ["kubernetes", "grpc"]
    assert captured["summary_keywords"] == ["kubernetes", "grpc"]


@patch("backend.services.draft_service.calculate_ats_score_for_draft")
@patch("backend.services.draft_service.generate_tailored_summary_async")
@patch("backend.services.draft_service.enhance_experience_for_job_async")
@patch("backend.services.draft_service.parse_background")
def test_generate_draft_skips_tailoring_for_experience_with_no_description(
    mock_parse, mock_enhance, mock_summary, mock_ats
):
    parsed = _parsed_background(experiences=[{"job_title": "Engineer", "company": "Test Corp", "description": None}])
    mock_parse.return_value = {"success": True, "data": parsed}
    mock_ats.return_value = {"missing_keywords": []}

    async def fake_summary(background_summary, job_description, missing_keywords=None):
        return {"success": True, "data": "A summary."}

    mock_summary.side_effect = fake_summary

    result = draft_service.generate_draft(JOB_DESCRIPTION, "some background text")

    assert result["data"]["experiences"][0]["ai_description"] == []
    mock_enhance.assert_not_called()


@patch("backend.services.draft_service.calculate_ats_score_for_draft")
@patch("backend.services.draft_service.generate_tailored_summary_async")
@patch("backend.services.draft_service.enhance_experience_for_job_async")
@patch("backend.services.draft_service.parse_background")
def test_generate_draft_falls_back_to_original_summary_when_tailoring_fails(
    mock_parse, mock_enhance, mock_summary, mock_ats
):
    mock_parse.return_value = {"success": True, "data": _parsed_background(summary="Original summary text.")}
    mock_ats.return_value = {"missing_keywords": []}

    async def fake_enhance(text, job_description, missing_keywords=None):
        return {"success": True, "data": ["A bullet."]}

    async def fake_summary(background_summary, job_description, missing_keywords=None):
        return {"success": False, "error": "connection error", "data": ""}

    mock_enhance.side_effect = fake_enhance
    mock_summary.side_effect = fake_summary

    result = draft_service.generate_draft(JOB_DESCRIPTION, "some background text")

    assert result["data"]["summary"] == "Original summary text."


@patch("backend.services.draft_service.calculate_ats_score_for_draft")
@patch("backend.services.draft_service.generate_tailored_summary_async")
@patch("backend.services.draft_service.enhance_experience_for_job_async")
@patch("backend.services.draft_service.parse_background")
def test_generate_draft_falls_back_to_no_bullets_when_one_experience_tailoring_fails(
    mock_parse, mock_enhance, mock_summary, mock_ats
):
    mock_parse.return_value = {"success": True, "data": _parsed_background()}
    mock_ats.return_value = {"missing_keywords": []}

    async def fake_enhance(text, job_description, missing_keywords=None):
        return {"success": False, "error": "connection error", "data": []}

    async def fake_summary(background_summary, job_description, missing_keywords=None):
        return {"success": True, "data": "A summary."}

    mock_enhance.side_effect = fake_enhance
    mock_summary.side_effect = fake_summary

    result = draft_service.generate_draft(JOB_DESCRIPTION, "some background text")

    assert result["data"]["experiences"][0]["ai_description"] == []


@patch("backend.services.draft_service.calculate_ats_score_for_draft")
@patch("backend.services.draft_service.generate_tailored_summary_async")
@patch("backend.services.draft_service.enhance_experience_for_job_async")
@patch("backend.services.draft_service.parse_background")
def test_generate_draft_builds_warnings_for_missing_fields(
    mock_parse, mock_enhance, mock_summary, mock_ats
):
    parsed = _parsed_background(name=None, email=None, experiences=[])
    mock_parse.return_value = {"success": True, "data": parsed}
    mock_ats.return_value = {"missing_keywords": []}

    async def fake_summary(background_summary, job_description, missing_keywords=None):
        return {"success": True, "data": "A summary."}

    mock_summary.side_effect = fake_summary

    result = draft_service.generate_draft(JOB_DESCRIPTION, "some background text")

    warnings = result["data"]["warnings"]
    assert any("name" in w.lower() for w in warnings)
    assert any("email" in w.lower() for w in warnings)
    assert any("experience" in w.lower() for w in warnings)
    mock_enhance.assert_not_called()


@patch("backend.services.draft_service.calculate_ats_score_for_draft")
@patch("backend.services.draft_service.generate_tailored_summary_async")
@patch("backend.services.draft_service.enhance_experience_for_job_async")
@patch("backend.services.draft_service.parse_background")
def test_generate_draft_survives_ats_scoring_exception(
    mock_parse, mock_enhance, mock_summary, mock_ats
):
    mock_parse.return_value = {"success": True, "data": _parsed_background()}
    mock_ats.side_effect = Exception("empty vocabulary")

    captured = {}

    async def fake_enhance(text, job_description, missing_keywords=None):
        captured["experience_keywords"] = missing_keywords
        return {"success": True, "data": ["A bullet."]}

    async def fake_summary(background_summary, job_description, missing_keywords=None):
        return {"success": True, "data": "A summary."}

    mock_enhance.side_effect = fake_enhance
    mock_summary.side_effect = fake_summary

    result = draft_service.generate_draft(JOB_DESCRIPTION, "some background text")

    assert result["success"] is True
    assert captured["experience_keywords"] == []


@patch("backend.services.draft_service.calculate_ats_score_for_draft")
@patch("backend.services.draft_service.generate_tailored_summary_async")
@patch("backend.services.draft_service.enhance_experience_for_job_async")
@patch("backend.services.draft_service.parse_background")
def test_generate_draft_tailoring_calls_run_concurrently(
    mock_parse, mock_enhance, mock_summary, mock_ats
):
    # Two experiences + the summary call = 3 concurrent calls, each sleeping
    # 0.2s. If they ran sequentially this would take >=0.6s; gathered
    # concurrently it should take well under that.
    parsed = _parsed_background(
        experiences=[
            {"job_title": "Engineer", "company": "A", "description": "Did A."},
            {"job_title": "Engineer", "company": "B", "description": "Did B."},
        ]
    )
    mock_parse.return_value = {"success": True, "data": parsed}
    mock_ats.return_value = {"missing_keywords": []}

    async def fake_enhance(text, job_description, missing_keywords=None):
        await _sleep()
        return {"success": True, "data": ["A bullet."]}

    async def fake_summary(background_summary, job_description, missing_keywords=None):
        await _sleep()
        return {"success": True, "data": "A summary."}

    import asyncio

    async def _sleep():
        await asyncio.sleep(0.2)

    mock_enhance.side_effect = fake_enhance
    mock_summary.side_effect = fake_summary

    start = time.monotonic()
    draft_service.generate_draft(JOB_DESCRIPTION, "some background text")
    elapsed = time.monotonic() - start

    assert elapsed < 0.5
