from pathlib import Path

from runtime.tools.openclaw_policy_assert import assert_policy, command_authorized


def _cfg():
    return {
        "commands": {"ownerAllowFrom": ["owner-1"]},
        "agents": {
            "defaults": {
                "workspace": "/home/tester/.openclaw/workspace",
                "thinkingDefault": "low",
                "model": {
                    "primary": "openai-codex/gpt-5.3-codex",
                    "fallbacks": ["openai-codex/gpt-5.1", "openai-codex/gpt-5.1-codex-max"],
                },
                "memorySearch": {
                    "enabled": False,
                    "provider": "local",
                    "fallback": "none",
                    "sources": ["memory"],
                },
            },
            "list": [
                {
                    "id": "main",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": ["openai-codex/gpt-5.1", "openai-codex/gpt-5.1-codex-max"],
                    },
                },
                {
                    "id": "quick",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": ["openai-codex/gpt-5.1", "openai-codex/gpt-5.1-codex-max"],
                    },
                },
                {
                    "id": "think",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": ["openai-codex/gpt-5.1", "openai-codex/gpt-5.1-codex-max"],
                    },
                },
            ],
        },
    }


def test_assert_policy_passes_for_expected_ladders():
    cfg = _cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    result = assert_policy(cfg)
    assert result["owners"] == ["owner-1"]
    assert result["defaults_thinking"] == "low"
    assert result["required_subscription_fallbacks"] == [
        "openai-codex/gpt-5.1",
        "openai-codex/gpt-5.1-codex-max",
    ]
    assert result["policy_phase"] == "burnin"
    assert result["memory"]["policy_phase"] == "burnin"
    assert result["memory"]["canonical_backend"] in {"missing", "local"}
    assert result["memory"]["legacy_memory_search"]["provider"] == "local"


def test_non_owner_cannot_model_or_think_switch():
    cfg = _cfg()
    assert command_authorized(cfg, "owner-1", "/model openai-codex/gpt-5.3-codex")
    assert not command_authorized(cfg, "outsider", "/model openai-codex/gpt-5.3-codex")
    assert not command_authorized(cfg, "outsider", "/think high")


def test_qmd_phase_requires_qmd_backend():
    cfg = _cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    cfg["memory"] = {"backend": "qmd"}
    result = assert_policy(cfg, policy_phase="qmd")
    assert result["memory"]["canonical_backend"] == "qmd"


def test_qmd_phase_rejects_non_qmd_backend():
    cfg = _cfg()
    cfg["agents"]["defaults"]["workspace"] = str(Path.home() / ".openclaw" / "workspace")
    cfg["memory"] = {"backend": "local"}
    try:
        assert_policy(cfg, policy_phase="qmd")
    except AssertionError as exc:
        assert "memory.backend must be qmd" in str(exc)
    else:
        raise AssertionError("expected qmd backend assertion")
