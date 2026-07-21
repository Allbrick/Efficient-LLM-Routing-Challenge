import pytest

from routing_stack.input import normalize_input


def test_normalize_text_input_returns_router_features():
    normalized = normalize_input({"prompt": "hello"})

    assert normalized.input_type == "text"
    assert normalized.text == "hello"
    assert normalized.router_features["simple_directive"] is True
    assert normalized.metadata["normalizer"] == "text_v1"


def test_normalizer_rejects_unsupported_input_types_until_parser_exists():
    with pytest.raises(ValueError, match="unsupported_input_type"):
        normalize_input({"input_type": "image", "prompt": "image bytes placeholder"})
