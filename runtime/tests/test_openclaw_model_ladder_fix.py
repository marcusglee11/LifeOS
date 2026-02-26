from runtime.tools.openclaw_model_ladder_fix import EXECUTION_BASE, apply_ladder_fixes


def test_apply_ladder_fixes_repairs_agents_defaults_model():
    cfg = {
        "agents": {
            "defaults": {
                "model": {
                    "primary": "openrouter/openai/gpt-4.1-mini",
                    "fallbacks": [
                        "anthropic/claude-3-haiku-20240307",
                        "github-copilot/gpt-5-mini",
                        "google-gemini-cli/gemini-3-flash-preview",
                        "openrouter/openai/gpt-4.1-mini",
                    ],
                }
            },
            "list": [],
        }
    }

    fixed, changes = apply_ladder_fixes(cfg)

    defaults_model = fixed["agents"]["defaults"]["model"]
    assert defaults_model["primary"] == EXECUTION_BASE[0]
    assert defaults_model["fallbacks"][:2] == EXECUTION_BASE[1:]
    assert "anthropic/claude-3-haiku-20240307" not in defaults_model["fallbacks"]
    assert "openrouter/openai/gpt-4.1-mini" in defaults_model["fallbacks"]
    assert any("agents.defaults: set primary" in c for c in changes)


def test_apply_ladder_fixes_creates_defaults_and_required_agents():
    fixed, changes = apply_ladder_fixes({})

    defaults_model = fixed["agents"]["defaults"]["model"]
    assert defaults_model["primary"] == EXECUTION_BASE[0]
    assert defaults_model["fallbacks"] == EXECUTION_BASE[1:]

    agent_ids = sorted(a["id"] for a in fixed["agents"]["list"])
    assert agent_ids == ["main", "quick", "think"]

    assert "Created agents section" in changes
    assert "Created agents.defaults section" in changes
