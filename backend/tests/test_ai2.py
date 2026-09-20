# backend/tests/test_ai2.py
"""Tests for enhance_experience's per-style prompt selection.

Verifies that "professional", "impactful", "concise", and an unrecognized
style each build the system prompt ai_engine.py intends for them.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.services.ai_engine import enhance_experience


def _fake_groq_response(bullets):
    message = MagicMock()
    message.content = json.dumps({"bullets": bullets})
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.parametrize(
    "style,expected_prompt_fragment",
    [
        ("professional", "professional resume writer"),
        ("impactful", "senior resume expert"),
        ("concise", "2-3 short bullet points"),
        ("not-a-real-style", "professional resume writer"),  # falls back to default
    ],
)
@patch("backend.services.ai_engine.client")
def test_each_style_uses_its_own_system_prompt(mock_client, style, expected_prompt_fragment):
    mock_client.chat.completions.create.return_value = _fake_groq_response(["A bullet point"])

    result = enhance_experience(
        "Worked on backend APIs and improved performance", style=style
    )

    assert result["success"] is True

    sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    system_prompt = sent_messages[0]["content"]
    assert expected_prompt_fragment in system_prompt
