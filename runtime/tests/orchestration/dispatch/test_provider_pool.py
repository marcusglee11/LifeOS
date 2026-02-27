"""Tests for ProviderPool health-aware routing."""
from __future__ import annotations

import pytest

from runtime.orchestration.dispatch.provider_pool import (
    COST_TIER_ORDER,
    ProviderHealth,
    ProviderPool,
)


def _pool(providers: dict, tmp_path=None):
    from pathlib import Path
    import tempfile

    root = tmp_path or Path(tempfile.mkdtemp())
    return ProviderPool(repo_root=root, providers=providers)


def test_resolve_explicit_provider():
    pool = _pool({})
    assert pool.resolve_provider("codex") == "codex"
    assert pool.resolve_provider("gemini") == "gemini"


def test_resolve_auto_no_providers():
    pool = _pool({})
    assert pool.resolve_provider("auto") == "auto"


def test_resolve_auto_selects_available(tmp_path):
    providers = {
        "codex": {"available": True, "cost_tier": "free"},
        "gemini": {"available": False, "cost_tier": "free"},
    }
    pool = _pool(providers, tmp_path)
    assert pool.resolve_provider("auto") == "codex"


def test_resolve_auto_deterministic_tie_break(tmp_path):
    """When all else equal, name ASC determines winner."""
    providers = {
        "zen": {"available": True, "cost_tier": "free"},
        "alpha": {"available": True, "cost_tier": "free"},
        "mids": {"available": True, "cost_tier": "free"},
    }
    pool = _pool(providers, tmp_path)
    assert pool.resolve_provider("auto") == "alpha"


def test_resolve_auto_cost_tier_order(tmp_path):
    providers = {
        "expensive": {"available": True, "cost_tier": "high"},
        "cheap": {"available": True, "cost_tier": "free"},
        "medium": {"available": True, "cost_tier": "medium"},
    }
    pool = _pool(providers, tmp_path)
    assert pool.resolve_provider("auto") == "cheap"


def test_resolve_auto_skips_unavailable_first(tmp_path):
    providers = {
        "cheap_unavailable": {"available": False, "cost_tier": "free"},
        "expensive_available": {"available": True, "cost_tier": "high"},
    }
    pool = _pool(providers, tmp_path)
    assert pool.resolve_provider("auto") == "expensive_available"


def test_snapshot_returns_serializable(tmp_path):
    providers = {
        "codex": {"available": True, "cost_tier": "free"},
    }
    pool = _pool(providers, tmp_path)
    snap = pool.snapshot()
    assert "codex" in snap
    assert isinstance(snap["codex"]["available"], bool)
    assert isinstance(snap["codex"]["latency_ms"], float)


def test_cost_tier_order_values():
    assert COST_TIER_ORDER["free"] < COST_TIER_ORDER["low"]
    assert COST_TIER_ORDER["low"] < COST_TIER_ORDER["medium"]
    assert COST_TIER_ORDER["medium"] < COST_TIER_ORDER["high"]


def test_persist_writes_file(tmp_path):
    providers = {"codex": {"available": True, "cost_tier": "free"}}
    pool = _pool(providers, tmp_path)
    pool.persist()

    state_path = tmp_path / "artifacts" / "health" / "provider_state.json"
    assert state_path.exists()
    import json

    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert "codex" in data


def test_record_call_updates_latency(tmp_path):
    providers = {"codex": {"available": True, "cost_tier": "free"}}
    pool = _pool(providers, tmp_path)
    pool.record_call("codex", 250, success=True)
    assert pool._health["codex"].latency_ms == 250.0


def test_all_providers(tmp_path):
    providers = {"a": {}, "b": {}, "c": {}}
    pool = _pool(providers, tmp_path)
    assert set(pool.all_providers()) == {"a", "b", "c"}
