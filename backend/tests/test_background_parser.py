# backend/tests/test_background_parser.py
"""Phase A: parse_background should turn freeform text into a structured
ParsedBackground dict, tolerate messy/malformed model output the same way
_parse_bullets already does, and never crash - a failure or an unparseable
response should come back as a fully-shaped, blank draft rather than
raising or returning a partial/inconsistent shape."""

import json
from unittest.mock import MagicMock, patch

from backend.schemas.draft import ParsedBackground
from backend.services.ai_engine import parse_background


def _fake_response(content: str):
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


WELL_FORMED = {
    "name": "Jordan Rivera",
    "title": "QA Engineer",
    "email": "jordan.rivera@example.com",
    "phone": "555-0101",
    "website": None,
    "summary": "Detail-oriented QA engineer with 4 years of experience.",
    "experiences": [
        {
            "job_title": "QA Engineer",
            "company": "Test Corp",
            "location": "Remote",
            "start_date": "Jan 2021",
            "end_date": None,
            "description": "Wrote automated tests. Improved release quality.",
            "is_current": True,
        }
    ],
    "education": [
        {
            "college": "State University",
            "degree": "B.S. Computer Science",
            "field_of_study": None,
            "start_year": "2015",
            "end_year": "2019",
            "details": None,
        }
    ],
    "skills": ["Python", "Selenium"],
    "certifications": [],
    "awards": [],
}


@patch("backend.services.ai_engine.client")
def test_parses_well_formed_json(mock_client):
    mock_client.chat.completions.create.return_value = _fake_response(json.dumps(WELL_FORMED))

    result = parse_background("Jordan Rivera. QA Engineer. jordan.rivera@example.com...")

    assert result["success"] is True
    assert result["data"]["name"] == "Jordan Rivera"
    assert result["data"]["experiences"][0]["company"] == "Test Corp"
    assert result["data"]["skills"] == ["Python", "Selenium"]


@patch("backend.services.ai_engine.client")
def test_recovers_from_messy_output_with_prose_and_trailing_commas(mock_client):
    messy = (
        "Sure, here's the JSON:\n```json\n"
        + json.dumps(WELL_FORMED).rstrip("}") + ",}\n```\nLet me know if you need anything else!"
    )
    mock_client.chat.completions.create.return_value = _fake_response(messy)

    result = parse_background("some background text")

    assert result["success"] is True
    assert result["data"]["name"] == "Jordan Rivera"
    assert result["data"]["experiences"][0]["job_title"] == "QA Engineer"


@patch("backend.services.ai_engine.client")
def test_unparseable_response_still_reports_success_but_data_is_blank(mock_client):
    # Mirrors enhance_experience's philosophy: the Groq call itself
    # succeeded, so success=True, even though nothing useful came back.
    mock_client.chat.completions.create.return_value = _fake_response("I couldn't find any resume content here.")

    result = parse_background("asdkjhaskjdh not really a resume")

    assert result["success"] is True
    assert result["data"] == ParsedBackground().model_dump()


@patch("backend.services.ai_engine.client")
def test_response_shaped_wrong_falls_back_to_blank_draft(mock_client):
    # "experiences" as a string instead of a list - Pydantic can't coerce
    # this, so it should fall back to a blank draft rather than raising.
    bad_shape = json.dumps({"name": "Sam", "experiences": "a string, not a list"})
    mock_client.chat.completions.create.return_value = _fake_response(bad_shape)

    result = parse_background("some text")

    assert result["success"] is True
    assert result["data"] == ParsedBackground().model_dump()


@patch("backend.services.ai_engine.client")
def test_groq_api_failure_returns_success_false_with_blank_data(mock_client):
    mock_client.chat.completions.create.side_effect = Exception("connection error")

    result = parse_background("some background text")

    assert result["success"] is False
    assert "error" in result
    assert result["data"] == ParsedBackground().model_dump()


@patch("backend.services.ai_engine.client")
def test_empty_background_text_short_circuits_without_calling_groq(mock_client):
    result = parse_background("   ")

    assert result["success"] is False
    mock_client.chat.completions.create.assert_not_called()


@patch("backend.services.ai_engine.client")
def test_partial_fields_default_correctly(mock_client):
    partial = {
        "name": "Alex Chen",
        "experiences": [{"job_title": "Engineer"}],  # company/dates/etc missing
    }
    mock_client.chat.completions.create.return_value = _fake_response(json.dumps(partial))

    result = parse_background("some background text")

    assert result["success"] is True
    assert result["data"]["name"] == "Alex Chen"
    assert result["data"]["email"] is None
    assert result["data"]["education"] == []
    exp = result["data"]["experiences"][0]
    assert exp["job_title"] == "Engineer"
    assert exp["company"] is None
    assert exp["is_current"] is False


@patch("backend.services.ai_engine.client")
def test_unexpected_extra_keys_are_ignored_not_fatal(mock_client):
    extra = dict(WELL_FORMED)
    extra["hallucinated_field"] = "the model made this up"
    mock_client.chat.completions.create.return_value = _fake_response(json.dumps(extra))

    result = parse_background("some background text")

    assert result["success"] is True
    assert "hallucinated_field" not in result["data"]
    assert result["data"]["name"] == "Jordan Rivera"
