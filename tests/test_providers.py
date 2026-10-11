"""
tests/test_providers.py
Tests for the provider abstraction (HF Inference API, fallback, parser utilities).
"""
import io
import unittest.mock as mock
from PIL import Image

from app.services.providers import (
    parse_label_json,
    parse_story_text,
    call_hf_vision,
    call_hf_story,
)
from app.services.vision import label_image, FALLBACK
from app.services.story import generate_story


def test_parse_label_json():
    # Clean json
    assert parse_label_json('{"label": "Pine cone", "description": "sharp and dry"}') == {
        "label": "Pine cone",
        "description": "sharp and dry"
    }

    # Markdown code fence
    fence = '```json\n{"label": "Acorn cap", "description": "smooth cup"}\n```'
    assert parse_label_json(fence) == {
        "label": "Acorn cap",
        "description": "smooth cup"
    }

    # Text wrapping json
    wrapped = 'Here is the find: {"label": "River stone", "description": "cool to touch"}. Hope you like it!'
    assert parse_label_json(wrapped) == {
        "label": "River stone",
        "description": "cool to touch"
    }

    # Invalid / empty
    assert parse_label_json("Not a json at all") is None
    assert parse_label_json("") is None


def test_parse_story_text():
    raw = "The Autumn River\n\nWe walked down to the edge of the water and found small relics."
    parsed = parse_story_text(raw, "Fallback Title")
    assert parsed == {
        "title": "The Autumn River",
        "text": "We walked down to the edge of the water and found small relics."
    }

    # Single line
    single = "Just a single short tale of leaves."
    parsed_single = parse_story_text(single, "Fallback Title")
    assert parsed_single == {
        "title": "Fallback Title",
        "text": "Just a single short tale of leaves."
    }

    # Empty
    assert parse_story_text("", "Fallback Title") is None


def test_hf_vision_provider_mock():
    img = Image.new("RGB", (50, 50), "green")
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {"message": {"content": '{"label": "Oak leaf", "description": "golden and notched"}'}}
        ]
    }

    with mock.patch("httpx.Client.post", return_value=mock_resp):
        res = call_hf_vision(img, "test-model")
        assert res == {"label": "Oak leaf", "description": "golden and notched"}


def test_vision_fallback_provider():
    img = Image.new("RGB", (50, 50), "red")
    with mock.patch("app.config.WAYSIDE_VISION_PROVIDER", "fallback"):
        res = label_image(img)
        assert res == FALLBACK


def test_story_fallback_provider():
    items = [{"label": "Leaf", "description": "crinkled", "note": ""}]
    with mock.patch("app.config.WAYSIDE_STORY_PROVIDER", "fallback"):
        res = generate_story(items, "quiet", "the trail")
        assert "title" in res and "text" in res
