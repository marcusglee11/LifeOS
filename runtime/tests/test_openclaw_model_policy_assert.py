from runtime.tools.openclaw_model_policy_assert import (
    _discover_kimi_id,
    _parse_models_list_text,
    assert_policy,
)


def _cfg() -> dict:
    return {
        "agents": {
            "list": [
                {
                    "id": "main",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "openai-codex/gpt-5.1",
                            "openai-codex/gpt-5.1-codex-max",
                            "openrouter/openai/gpt-4.1-mini",
                        ],
                    },
                },
                {
                    "id": "quick",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "openai-codex/gpt-5.1",
                            "openai-codex/gpt-5.1-codex-max",
                        ],
                    },
                },
                {
                    "id": "think",
                    "thinking": "extra_high",
                    "model": {
                        "primary": "openai-codex/gpt-5.3-codex",
                        "fallbacks": [
                            "openai-codex/gpt-5.1",
                            "openai-codex/gpt-5.1-codex-max",
                            "openrouter/openai/gpt-4.1-mini",
                        ],
                    },
                },
            ]
        }
    }


def _models_list_text() -> str:
    return """\
Model                                      Input      Ctx      Local Auth  Tags
openai-codex/gpt-5.3-codex                 text+image 266k     no    yes   configured
openai-codex/gpt-5.1                       text+image 266k     no    yes   configured
openai-codex/gpt-5.1-codex-max             text+image 266k     no    yes   configured
openrouter/openai/gpt-4.1-mini             text+image 200k     no    yes   configured
opencode/kimi-k2.5-free                    text+image 256k     no    yes   configured
"""


def test_policy_assert_passes_for_subscription_prefix_and_api_standby_tail():
    cfg = _cfg()
    status = _parse_models_list_text(_models_list_text())
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is True
    assert result["ladders"]["main"]["working_count"] >= 1
    assert result["ladders"]["quick"]["working_count"] >= 1
    assert result["ladders"]["think"]["working_count"] >= 1


def test_policy_assert_fails_on_wrong_prefix_order():
    cfg = _cfg()
    cfg["agents"]["list"][0]["model"]["fallbacks"] = [
        "openai-codex/gpt-5.1-codex-max",
        "openai-codex/gpt-5.1",
    ]
    status = _parse_models_list_text(_models_list_text())
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is False
    assert any("prefix mismatch" in v for v in result["violations"])


def test_policy_assert_fails_on_disallowed_haiku():
    cfg = _cfg()
    cfg["agents"]["list"][1]["model"]["fallbacks"] = [
        "openai-codex/gpt-5.1",
        "openai-codex/gpt-5.1-codex-max",
        "anthropic/claude-3-haiku-20240307",
    ]
    status = _parse_models_list_text(_models_list_text())
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is False
    assert any("disallowed fallback" in v for v in result["violations"])


def test_policy_assert_fails_when_agent_has_no_working_models():
    cfg = _cfg()
    status = _parse_models_list_text(_models_list_text())
    for model_id in list(status.keys()):
        status[model_id]["working"] = False
    result = assert_policy(cfg, status, None)
    assert result["policy_ok"] is False
    assert any("no working model detected" in v for v in result["violations"])


def test_discover_kimi_id_retained_for_backward_compat():
    kimi = _discover_kimi_id([], ["opencode/kimi-k2.5-free"])
    assert kimi == "opencode/kimi-k2.5-free"
