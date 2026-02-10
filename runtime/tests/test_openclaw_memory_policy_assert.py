from runtime.tools.openclaw_policy_assert import assert_policy
from pathlib import Path


def _base_cfg():
    return {
        "commands": {"ownerAllowFrom": ["owner-1"]},
        "agents": {
            "defaults": {
                "workspace": "/home/tester/.openclaw/workspace",
                "thinkingDefault": "low",
                "model": {
                    "primary": "openai-codex/gpt-5.3-codex",
                    "fallbacks": ["google-gemini-cli/gemini-3-flash-preview"],
                },
                "memorySearch": {
                    "enabled": True,
                    "provider": "local",
                    "fallback": "none",
                    "sources": ["memory"],
                },
            },
            "list": [
                {"id": "main", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["google-gemini-cli/gemini-3-flash-preview"]}},
                {"id": "quick", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["google-gemini-cli/gemini-3-flash-preview"]}},
                {"id": "think", "model": {"primary": "openai-codex/gpt-5.3-codex", "fallbacks": ["github-copilot/claude-opus-4.6"]}},
            ],
        },
    }


def test_memory_policy_accepts_local_no_fallback_and_memory_source_only():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    result = assert_policy(cfg)
    assert result["memory"]["provider"] == "local"
    assert result["memory"]["fallback"] == "none"
    assert result["memory"]["sources"] == ["memory"]


def test_memory_policy_rejects_non_local_provider():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    cfg["agents"]["defaults"]["memorySearch"]["provider"] = "openai"
    try:
        assert_policy(cfg)
    except AssertionError as exc:
        assert "memorySearch.provider must be local" in str(exc)
    else:
        raise AssertionError("expected memory provider assertion")


def test_memory_policy_rejects_sessions_source():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    cfg["agents"]["defaults"]["memorySearch"]["sources"] = ["memory", "sessions"]
    try:
        assert_policy(cfg)
    except AssertionError as exc:
        assert 'must not include "sessions"' in str(exc)
    else:
        raise AssertionError("expected sessions source assertion")


def test_memory_policy_rejects_workspace_outside_openclaw_home():
    cfg = _base_cfg()
    cfg["agents"]["defaults"]["workspace"] = "/mnt/c/Users/cabra/Projects/LifeOS"
    try:
        assert_policy(cfg)
    except AssertionError as exc:
        assert "workspace must be under ~/.openclaw" in str(exc)
    else:
        raise AssertionError("expected workspace boundary assertion")
