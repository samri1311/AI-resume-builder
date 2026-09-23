# backend/tests/test_job_tailoring.py
"""Phase B: job-description-aware bullet tailoring and tailored summary
generation. Same mocking approach as test_ai.py/test_ai2.py - patch the
Groq client, assert on what gets sent and what comes back."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.ai_engine import (
    enhance_experience_for_job,
    enhance_experience_for_job_async,
    generate_tailored_summary,
    generate_tailored_summary_async,
)


def _fake_response(content: str):
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


JOB_DESCRIPTION = "Looking for a backend engineer experienced with Kubernetes and gRPC."


@patch("backend.services.ai_engine.client")
def test_enhance_experience_for_job_includes_job_description_in_prompt(mock_client):
    mock_client.chat.completions.create.return_value = _fake_response(
        json.dumps({"bullets": ["Deployed services on Kubernetes clusters."]})
    )

    result = enhance_experience_for_job("Ran backend services in production.", JOB_DESCRIPTION)

    assert result["success"] is True
    assert result["data"] == ["Deployed services on Kubernetes clusters."]
    system_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert JOB_DESCRIPTION in system_prompt


@patch("backend.services.ai_engine.client")
def test_enhance_experience_for_job_includes_missing_keywords_when_given(mock_client):
    mock_client.chat.completions.create.return_value = _fake_response(json.dumps({"bullets": ["A bullet."]}))

    enhance_experience_for_job(
        "Ran backend services.", JOB_DESCRIPTION, missing_keywords=["kubernetes", "grpc"]
    )

    system_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "kubernetes" in system_prompt
    assert "grpc" in system_prompt


@patch("backend.services.ai_engine.client")
def test_enhance_experience_for_job_still_uses_the_chosen_style(mock_client):
    mock_client.chat.completions.create.return_value = _fake_response(json.dumps({"bullets": ["A bullet."]}))

    enhance_experience_for_job("Ran backend services.", JOB_DESCRIPTION, style="concise")

    system_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "2-3 short bullet points" in system_prompt


@patch("backend.services.ai_engine.client")
def test_enhance_experience_for_job_reports_api_failure(mock_client):
    mock_client.chat.completions.create.side_effect = Exception("connection error")

    result = enhance_experience_for_job("Ran backend services.", JOB_DESCRIPTION)

    assert result["success"] is False
    assert result["data"] == []
    assert "error" in result


@patch("backend.services.ai_engine.async_client")
def test_enhance_experience_for_job_async_matches_sync_behavior(mock_async_client):
    mock_async_client.chat.completions.create = AsyncMock(
        return_value=_fake_response(json.dumps({"bullets": ["Async bullet."]}))
    )

    result = asyncio.run(enhance_experience_for_job_async("Ran backend services.", JOB_DESCRIPTION))

    assert result == {"success": True, "data": ["Async bullet."]}


@patch("backend.services.ai_engine.client")
def test_generate_tailored_summary_returns_parsed_summary(mock_client):
    mock_client.chat.completions.create.return_value = _fake_response(
        json.dumps({"summary": "Backend engineer with Kubernetes experience."})
    )

    result = generate_tailored_summary("Built backend services for 3 years.", JOB_DESCRIPTION)

    assert result["success"] is True
    assert result["data"] == "Backend engineer with Kubernetes experience."


@patch("backend.services.ai_engine.client")
def test_generate_tailored_summary_handles_empty_background(mock_client):
    mock_client.chat.completions.create.return_value = _fake_response(
        json.dumps({"summary": "Motivated engineer seeking new opportunities."})
    )

    result = generate_tailored_summary("", JOB_DESCRIPTION)

    assert result["success"] is True
    user_prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "No existing summary was provided" in user_prompt


@patch("backend.services.ai_engine.client")
def test_generate_tailored_summary_falls_back_to_raw_text_when_not_json(mock_client):
    mock_client.chat.completions.create.return_value = _fake_response(
        "Backend engineer with strong Kubernetes and gRPC experience."
    )

    result = generate_tailored_summary("Built backend services.", JOB_DESCRIPTION)

    assert result["success"] is True
    assert result["data"] == "Backend engineer with strong Kubernetes and gRPC experience."


@patch("backend.services.ai_engine.client")
def test_generate_tailored_summary_reports_api_failure(mock_client):
    mock_client.chat.completions.create.side_effect = Exception("connection error")

    result = generate_tailored_summary("Built backend services.", JOB_DESCRIPTION)

    assert result["success"] is False
    assert result["data"] == ""


@patch("backend.services.ai_engine.async_client")
def test_generate_tailored_summary_async_matches_sync_behavior(mock_async_client):
    mock_async_client.chat.completions.create = AsyncMock(
        return_value=_fake_response(json.dumps({"summary": "Async summary."}))
    )

    result = asyncio.run(generate_tailored_summary_async("Built backend services.", JOB_DESCRIPTION))

    assert result == {"success": True, "data": "Async summary."}
