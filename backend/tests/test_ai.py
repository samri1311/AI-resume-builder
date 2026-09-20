# backend/tests/test_ai.py
"""Tests for enhance_experience's default (professional) behavior.

These mock the Groq client so the suite runs without a live GROQ_API_KEY
or network access, and actually assert on the result instead of just
printing it (as the original version of this file did).
"""

import json
from unittest.mock import MagicMock, patch

from backend.services.ai_engine import enhance_experience


def _fake_groq_response(bullets):
    """Build a fake Groq chat-completion response shaped like the real SDK's,
    with `bullets` as its JSON content."""
    message = MagicMock()
    message.content = json.dumps({"bullets": bullets})

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


@patch("backend.services.ai_engine.client")
def test_enhance_experience_returns_parsed_bullets(mock_client):
    mock_client.chat.completions.create.return_value = _fake_groq_response(
        ["Developed REST APIs using FastAPI", "Improved response times by 30%"]
    )

    result = enhance_experience("Worked on APIs and backend development")

    assert result["success"] is True
    assert result["data"] == [
        "Developed REST APIs using FastAPI",
        "Improved response times by 30%",
    ]


@patch("backend.services.ai_engine.client")
def test_enhance_experience_recovers_from_messy_output(mock_client):
    # The model wraps the JSON in prose and leaves a trailing comma — the
    # regex extraction + trailing-comma fix in ai_engine should still recover it.
    mock_client.chat.completions.create.return_value = _fake_groq_response([])
    mock_client.chat.completions.create.return_value.choices[0].message.content = (
        'Sure, here you go:\n{"bullets": ["Built internal tooling",]}\n'
    )

    result = enhance_experience("Worked on internal tooling")

    assert result["success"] is True
    assert result["data"] == ["Built internal tooling"]


@patch("backend.services.ai_engine.client")
def test_enhance_experience_reports_api_failure(mock_client):
    mock_client.chat.completions.create.side_effect = RuntimeError("Groq API unreachable")

    result = enhance_experience("Worked on backend systems")

    assert result["success"] is False
    assert result["data"] == []
    assert "Groq API unreachable" in result["error"]
