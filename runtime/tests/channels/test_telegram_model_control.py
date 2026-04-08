"""Tests for runtime/channels/telegram/model_control.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.channels.telegram import model_control as mc_mod
from runtime.channels.telegram.model_control import (
    ModelControlError,
    bootstrap_telegram_agent,
    get_telegram_agent_primary,
    list_allowed_models,
    load_telegram_model_config,
    set_telegram_model,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MODEL_CFG = {
    "primary": "openai-codex/gpt-5.4",
    "fallbacks": ["openai-codex/gpt-5.3-codex", "openai-codex/gpt-5.1"],
}

_OPENCLAW_CFG = {
    "agents": {
        "defaults": {
            "models": {
                "openai-codex/gpt-5.4": {},
                "openai-codex/gpt-5.3-codex": {},
                "openai-codex/gpt-5.1": {},
                "github-copilot/gpt-5-mini": {},
            }
        },
        "list": [
            {
                "id": "main",
                "model": {
                    "primary": "openai-codex/gpt-5.3-codex",
                    "fallbacks": ["openai-codex/gpt-5.1", "github-copilot/gpt-5-mini"],
                },
            }
        ],
    }
}


def _write_model_cfg(repo_root: Path, cfg: dict | None = None) -> None:
    path = repo_root / "config" / "coo" / "telegram_model.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg or _MODEL_CFG))


def _write_openclaw_cfg(openclaw_path: Path, cfg: dict | None = None) -> None:
    openclaw_path.parent.mkdir(parents=True, exist_ok=True)
    openclaw_path.write_text(json.dumps(cfg or _OPENCLAW_CFG))


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _write_model_cfg(tmp_path)
    return tmp_path


@pytest.fixture()
def openclaw_cfg_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    p = tmp_path / ".openclaw" / "openclaw.json"
    _write_openclaw_cfg(p)
    monkeypatch.setattr(mc_mod, "_OPENCLAW_CONFIG_PATH", p)
    return p


# ---------------------------------------------------------------------------
# load_telegram_model_config
# ---------------------------------------------------------------------------


def test_load_telegram_model_config(repo: Path) -> None:
    cfg = load_telegram_model_config(repo)
    assert cfg["primary"] == "openai-codex/gpt-5.4"
    assert "openai-codex/gpt-5.3-codex" in cfg["fallbacks"]


def test_load_telegram_model_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ModelControlError, match="Cannot read"):
        load_telegram_model_config(tmp_path)


# ---------------------------------------------------------------------------
# set_telegram_model
# ---------------------------------------------------------------------------


def test_set_telegram_model_updates_primary(
    repo: Path, openclaw_cfg_path: Path
) -> None:
    set_telegram_model(repo, "openai-codex/gpt-5.3-codex")
    cfg = load_telegram_model_config(repo)
    assert cfg["primary"] == "openai-codex/gpt-5.3-codex"


def test_set_telegram_model_preserves_fallbacks(
    repo: Path, openclaw_cfg_path: Path
) -> None:
    original_fallbacks = load_telegram_model_config(repo)["fallbacks"]
    set_telegram_model(repo, "openai-codex/gpt-5.1")
    cfg = load_telegram_model_config(repo)
    assert cfg["fallbacks"] == original_fallbacks


# ---------------------------------------------------------------------------
# list_allowed_models
# ---------------------------------------------------------------------------


def test_list_allowed_models_returns_keys(
    repo: Path, openclaw_cfg_path: Path
) -> None:
    models = list_allowed_models()
    assert "openai-codex/gpt-5.4" in models
    assert "github-copilot/gpt-5-mini" in models


def test_list_allowed_models_raises_if_config_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(mc_mod, "_OPENCLAW_CONFIG_PATH", tmp_path / "missing.json")
    with pytest.raises(ModelControlError):
        list_allowed_models()


# ---------------------------------------------------------------------------
# get_telegram_agent_primary
# ---------------------------------------------------------------------------


def test_get_telegram_agent_primary_returns_none_when_absent(
    openclaw_cfg_path: Path,
) -> None:
    assert get_telegram_agent_primary() is None


def test_get_telegram_agent_primary_returns_value_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = json.loads(json.dumps(_OPENCLAW_CFG))
    cfg["agents"]["list"].append({
        "id": "telegram",
        "model": {"primary": "openai-codex/gpt-5.4", "fallbacks": []},
    })
    p = tmp_path / ".openclaw" / "openclaw.json"
    _write_openclaw_cfg(p, cfg)
    monkeypatch.setattr(mc_mod, "_OPENCLAW_CONFIG_PATH", p)
    assert get_telegram_agent_primary() == "openai-codex/gpt-5.4"


# ---------------------------------------------------------------------------
# bootstrap_telegram_agent
# ---------------------------------------------------------------------------


def test_bootstrap_creates_telegram_agent_from_main(
    repo: Path, openclaw_cfg_path: Path
) -> None:
    bootstrap_telegram_agent(repo)
    cfg = json.loads(openclaw_cfg_path.read_text())
    agent_ids = [a["id"] for a in cfg["agents"]["list"]]
    assert "telegram" in agent_ids
    telegram = next(a for a in cfg["agents"]["list"] if a["id"] == "telegram")
    assert telegram["model"]["primary"] == "openai-codex/gpt-5.4"


def test_bootstrap_updates_existing_telegram_agent(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = json.loads(json.dumps(_OPENCLAW_CFG))
    cfg["agents"]["list"].append({
        "id": "telegram",
        "model": {"primary": "openai-codex/gpt-5.1", "fallbacks": []},
    })
    p = tmp_path / ".openclaw" / "openclaw.json"
    _write_openclaw_cfg(p, cfg)
    monkeypatch.setattr(mc_mod, "_OPENCLAW_CONFIG_PATH", p)
    bootstrap_telegram_agent(repo)
    updated = json.loads(p.read_text())
    telegram = next(a for a in updated["agents"]["list"] if a["id"] == "telegram")
    assert telegram["model"]["primary"] == "openai-codex/gpt-5.4"


def test_bootstrap_raises_if_agents_list_missing(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = {"agents": {"defaults": {"models": {}}}}  # no "list" key
    p = tmp_path / ".openclaw" / "openclaw.json"
    _write_openclaw_cfg(p, cfg)
    monkeypatch.setattr(mc_mod, "_OPENCLAW_CONFIG_PATH", p)
    with pytest.raises(ModelControlError, match="agents.list"):
        bootstrap_telegram_agent(repo)


def test_bootstrap_raises_if_main_missing(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = {"agents": {"defaults": {"models": {}}, "list": []}}
    p = tmp_path / ".openclaw" / "openclaw.json"
    _write_openclaw_cfg(p, cfg)
    monkeypatch.setattr(mc_mod, "_OPENCLAW_CONFIG_PATH", p)
    with pytest.raises(ModelControlError, match="main agent not found"):
        bootstrap_telegram_agent(repo)


def test_bootstrap_preserves_other_agents(
    repo: Path, openclaw_cfg_path: Path
) -> None:
    bootstrap_telegram_agent(repo)
    cfg = json.loads(openclaw_cfg_path.read_text())
    agent_ids = [a["id"] for a in cfg["agents"]["list"]]
    assert "main" in agent_ids
    assert "telegram" in agent_ids


# ---------------------------------------------------------------------------
# Regression: model validation — fall back to main agent when primary unavailable
# ---------------------------------------------------------------------------


def test_bootstrap_falls_back_to_main_model_when_primary_unavailable(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If telegram_model.json primary is not in allowed_models, use main agent's model."""
    # OpenClaw only knows about "claude-3-5-sonnet" — not the configured gpt-5.4
    cfg = {
        "agents": {
            "defaults": {
                "models": {
                    "claude-3-5-sonnet": {},
                    "claude-3-haiku": {},
                }
            },
            "list": [
                {
                    "id": "main",
                    "model": {
                        "primary": "claude-3-5-sonnet",
                        "fallbacks": ["claude-3-haiku"],
                    },
                }
            ],
        }
    }
    p = tmp_path / ".openclaw" / "openclaw.json"
    _write_openclaw_cfg(p, cfg)
    monkeypatch.setattr(mc_mod, "_OPENCLAW_CONFIG_PATH", p)

    bootstrap_telegram_agent(repo)

    updated = json.loads(p.read_text())
    telegram = next(a for a in updated["agents"]["list"] if a["id"] == "telegram")
    # Should have fallen back to main agent's model
    assert telegram["model"]["primary"] == "claude-3-5-sonnet"


def test_bootstrap_raises_when_primary_unavailable_and_main_also_unavailable(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Raise ModelControlError when configured primary is bad AND main has no usable fallback."""
    cfg = {
        "agents": {
            "defaults": {
                "models": {
                    "some-other-model": {},
                }
            },
            "list": [
                {
                    "id": "main",
                    "model": {
                        "primary": "also-not-allowed",
                        "fallbacks": [],
                    },
                }
            ],
        }
    }
    p = tmp_path / ".openclaw" / "openclaw.json"
    _write_openclaw_cfg(p, cfg)
    monkeypatch.setattr(mc_mod, "_OPENCLAW_CONFIG_PATH", p)

    with pytest.raises(ModelControlError, match="not in allowed models"):
        bootstrap_telegram_agent(repo)


def test_bootstrap_skips_validation_when_allowed_models_unavailable(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If list_allowed_models() raises (openclaw.json missing defaults.models), skip validation."""
    # openclaw.json exists but has no defaults.models — list_allowed_models() will raise
    cfg = {
        "agents": {
            "list": [
                {
                    "id": "main",
                    "model": {"primary": "openai-codex/gpt-5.4", "fallbacks": []},
                }
            ]
        }
    }
    p = tmp_path / ".openclaw" / "openclaw.json"
    _write_openclaw_cfg(p, cfg)
    monkeypatch.setattr(mc_mod, "_OPENCLAW_CONFIG_PATH", p)

    # Should not raise — skips validation when allowed_models can't be read
    bootstrap_telegram_agent(repo)
    updated = json.loads(p.read_text())
    telegram = next(a for a in updated["agents"]["list"] if a["id"] == "telegram")
    assert telegram["model"]["primary"] == "openai-codex/gpt-5.4"
