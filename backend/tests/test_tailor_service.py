# backend/tests/test_tailor_service.py
"""Phase F: build_tailoring_preview - runs the same job-description-aware
tailoring calls Phase B/C use (enhance_experience_for_job_async,
generate_tailored_summary_async), but against a real saved resume instead
of a freeform parsed background dict. Groq is mocked the same way
test_job_tailoring.py mocks it - only the async client matters here since
tailor_service exclusively uses the *_async variants for concurrency.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.database import Base
from backend.database import models
from backend.services.tailor_service import build_tailoring_preview


def _fake_response(content: str):
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def saved_resume(db_session):
    user = models.User(name="Jordan Rivera", email="jordan@example.com")
    db_session.add(user)
    db_session.flush()

    resume = models.Resume(user_id=user.id, summary="Backend engineer with 5 years of experience.")
    db_session.add(resume)
    db_session.flush()

    exp = models.Experience(
        resume_id=resume.id,
        job_title="Engineer",
        company="Acme",
        description="Built REST APIs using FastAPI.",
        ai_description=[],
    )
    db_session.add(exp)
    db_session.add(models.Skill(resume_id=resume.id, skill_name="Python"))
    db_session.commit()

    return resume


JOB_DESCRIPTION = "Looking for a backend engineer experienced with Kubernetes and gRPC."


@patch("backend.services.ai_engine.async_client")
def test_build_tailoring_preview_returns_tailored_summary_and_bullets(mock_async_client, saved_resume):
    def fake_create(*args, **kwargs):
        content = kwargs["messages"][1]["content"]
        if "Candidate's existing summary" in content:
            return _fake_response(json.dumps({"summary": "Tailored summary mentioning Kubernetes."}))
        return _fake_response(json.dumps({"bullets": ["Deployed services on Kubernetes clusters."]}))

    mock_async_client.chat.completions.create = AsyncMock(side_effect=fake_create)

    result = build_tailoring_preview(saved_resume, JOB_DESCRIPTION)

    assert result["success"] is True
    data = result["data"]
    assert data["original_summary"] == "Backend engineer with 5 years of experience."
    assert data["tailored_summary"] == "Tailored summary mentioning Kubernetes."
    assert len(data["experiences"]) == 1
    assert data["experiences"][0]["tailored_bullets"] == ["Deployed services on Kubernetes clusters."]
    assert data["experiences"][0]["original_description"] == "Built REST APIs using FastAPI."
    assert isinstance(data["missing_keywords"], list)


def test_build_tailoring_preview_rejects_blank_job_description(saved_resume):
    result = build_tailoring_preview(saved_resume, "   ")

    assert result["success"] is False
    assert "job description" in result["error"].lower()


@patch("backend.services.ai_engine.async_client")
def test_build_tailoring_preview_skips_experience_with_no_description(mock_async_client, db_session, saved_resume):
    blank_exp = models.Experience(
        resume_id=saved_resume.id, job_title="Intern", company="Acme", description=None, ai_description=[]
    )
    db_session.add(blank_exp)
    db_session.commit()
    db_session.refresh(saved_resume)

    mock_async_client.chat.completions.create = AsyncMock(
        return_value=_fake_response(json.dumps({"bullets": ["A bullet."]}))
    )

    result = build_tailoring_preview(saved_resume, JOB_DESCRIPTION)

    blank_entry = next(e for e in result["data"]["experiences"] if e["job_title"] == "Intern")
    assert blank_entry["tailored_bullets"] == []


@patch("backend.services.ai_engine.async_client")
def test_build_tailoring_preview_falls_back_to_original_summary_on_failure(mock_async_client, saved_resume):
    mock_async_client.chat.completions.create = AsyncMock(side_effect=Exception("groq down"))

    result = build_tailoring_preview(saved_resume, JOB_DESCRIPTION)

    assert result["success"] is True  # the preview itself still succeeds
    assert result["data"]["tailored_summary"] == "Backend engineer with 5 years of experience."
    assert result["data"]["experiences"][0]["tailored_bullets"] == []
