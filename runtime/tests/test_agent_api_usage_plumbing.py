from __future__ import annotations

from runtime.agents.api import _normalize_usage


def test_normalize_usage_maps_openrouter_fields() -> None:
    usage = _normalize_usage(
        {
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "total_tokens": 18,
        }
    )
    assert usage == {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18}


def test_normalize_usage_returns_empty_when_unavailable() -> None:
    assert _normalize_usage({}) == {}
    assert _normalize_usage(None) == {}
