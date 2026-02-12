from runtime.tools.openclaw_embedding_trial import build_trial_config


def _base_cfg() -> dict:
    return {
        "agents": {
            "defaults": {
                "workspace": "/home/tester/.openclaw/workspace",
                "memorySearch": {
                    "enabled": True,
                    "provider": "local",
                    "fallback": "auto",
                    "sources": ["memory", "sessions"],
                },
            }
        }
    }


def test_trial_config_enforces_safe_defaults_for_remote_provider():
    cfg = build_trial_config(_base_cfg(), provider="openai", model="text-embedding-3-small")
    memory = cfg["agents"]["defaults"]["memorySearch"]
    assert memory["enabled"] is True
    assert memory["provider"] == "openai"
    assert memory["fallback"] == "none"
    assert memory["sources"] == ["memory"]
    assert memory["openai"]["model"] == "text-embedding-3-small"
    assert memory["query"]["hybrid"]["enabled"] is True
    assert memory["cache"]["enabled"] is True
    assert memory["sync"]["watch"] is True


def test_trial_config_sets_local_model_path_when_requested():
    cfg = build_trial_config(_base_cfg(), provider="local", model="hf:BAAI/bge-small-en-v1.5")
    memory = cfg["agents"]["defaults"]["memorySearch"]
    assert memory["provider"] == "local"
    assert memory["local"]["modelPath"] == "hf:BAAI/bge-small-en-v1.5"


def test_trial_config_keeps_provider_default_when_model_not_set():
    cfg = build_trial_config(_base_cfg(), provider="gemini", model=None)
    memory = cfg["agents"]["defaults"]["memorySearch"]
    assert memory["provider"] == "gemini"
    assert "gemini" not in memory or "model" not in memory.get("gemini", {})
