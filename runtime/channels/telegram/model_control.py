"""Telegram model control — local config read/write and OpenClaw agent bootstrap."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from runtime.util.atomic_write import atomic_write_text

_TELEGRAM_MODEL_CONFIG_RELATIVE = Path("config/coo/telegram_model.json")
_OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
_TELEGRAM_AGENT_ID = "telegram"
_MAIN_AGENT_ID = "main"


class ModelControlError(RuntimeError):
    pass


def load_telegram_model_config(repo_root: Path) -> dict:
    """Return {"primary": str, "fallbacks": list[str]} from config/coo/telegram_model.json."""
    path = repo_root / _TELEGRAM_MODEL_CONFIG_RELATIVE
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelControlError(f"Cannot read telegram model config at {path}: {exc}") from exc


def set_telegram_model(repo_root: Path, primary: str) -> None:
    """Write a new primary model to config/coo/telegram_model.json.

    Fallbacks are preserved from the existing config. Then bootstraps
    the OpenClaw telegram agent to pick up the change.
    """
    cfg = load_telegram_model_config(repo_root)
    cfg["primary"] = primary
    path = repo_root / _TELEGRAM_MODEL_CONFIG_RELATIVE
    atomic_write_text(path, json.dumps(cfg, indent=2))
    bootstrap_telegram_agent(repo_root)


def list_allowed_models() -> list[str]:
    """Return model IDs from agents.defaults.models in ~/.openclaw/openclaw.json."""
    try:
        config = json.loads(_OPENCLAW_CONFIG_PATH.read_text())
        return list(config["agents"]["defaults"]["models"].keys())
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise ModelControlError(f"Cannot read openclaw config: {exc}") from exc


def get_telegram_agent_primary() -> str | None:
    """Return the current primary model for the telegram agent in openclaw.json, or None."""
    try:
        config = json.loads(_OPENCLAW_CONFIG_PATH.read_text())
        agents_list = config["agents"]["list"]
        entry = next((a for a in agents_list if a.get("id") == _TELEGRAM_AGENT_ID), None)
        if entry is None:
            return None
        return entry.get("model", {}).get("primary")
    except (OSError, json.JSONDecodeError, KeyError):
        return None


def bootstrap_telegram_agent(repo_root: Path) -> None:
    """Ensure the telegram agent exists in ~/.openclaw/openclaw.json.

    If the telegram entry is absent, it is cloned from the main agent entry.
    The primary model and fallbacks are then updated to match
    config/coo/telegram_model.json.

    Raises ModelControlError on missing main agent or unreadable config.
    """
    model_cfg = load_telegram_model_config(repo_root)

    try:
        raw = _OPENCLAW_CONFIG_PATH.read_text()
        config = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelControlError(
            f"Cannot read openclaw config at {_OPENCLAW_CONFIG_PATH}: {exc}"
        ) from exc

    try:
        agents_list: list = config["agents"]["list"]
    except KeyError as exc:
        raise ModelControlError(
            f"openclaw.json missing expected structure (agents.list): {exc}"
        ) from exc

    telegram_entry = next(
        (a for a in agents_list if a.get("id") == _TELEGRAM_AGENT_ID), None
    )
    if telegram_entry is None:
        main_entry = next(
            (a for a in agents_list if a.get("id") == _MAIN_AGENT_ID), None
        )
        if main_entry is None:
            raise ModelControlError(
                "main agent not found in openclaw.json — cannot bootstrap telegram agent"
            )
        telegram_entry = copy.deepcopy(main_entry)
        telegram_entry["id"] = _TELEGRAM_AGENT_ID
        agents_list.append(telegram_entry)

    if "model" not in telegram_entry:
        telegram_entry["model"] = {}

    # Validate configured primary model against what OpenClaw actually supports.
    # If the configured model is absent from allowed_models, fall back to the
    # main agent's model rather than writing an unusable config.
    try:
        allowed = list_allowed_models()
    except ModelControlError:
        allowed = []

    primary = model_cfg["primary"]
    fallbacks = model_cfg.get("fallbacks", [])

    if allowed and primary not in allowed:
        main_entry = next(
            (a for a in agents_list if a.get("id") == _MAIN_AGENT_ID), None
        )
        main_primary = main_entry.get("model", {}).get("primary") if main_entry else None
        if main_primary and main_primary in allowed:
            primary = main_primary
            fallbacks = [m for m in fallbacks if m in allowed]
        else:
            raise ModelControlError(
                f"Telegram primary model '{model_cfg['primary']}' not in allowed models "
                f"and main agent has no usable fallback. Allowed: {allowed}"
            )

    telegram_entry["model"]["primary"] = primary
    telegram_entry["model"]["fallbacks"] = fallbacks

    atomic_write_text(_OPENCLAW_CONFIG_PATH, json.dumps(config, indent=2))
