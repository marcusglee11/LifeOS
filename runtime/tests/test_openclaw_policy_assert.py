from runtime.tools.openclaw_policy_assert import assert_policy, command_authorized
from pathlib import Path

def _cfg():
    return {
        'commands': {'ownerAllowFrom': ['owner-1']},
        'agents': {
            'defaults': {
                'workspace': '/home/tester/.openclaw/workspace',
                'thinkingDefault': 'low',
                'model': {
                    'primary': 'openai-codex/gpt-5.3-codex',
                    'fallbacks': ['github-copilot/gpt-5-mini', 'google-gemini-cli/gemini-3-flash-preview'],
                },
                'memorySearch': {
                    'enabled': False,
                    'provider': 'local',
                    'fallback': 'none',
                    'sources': ['memory'],
                },
            },
            'list': [
                {'id': 'main', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['github-copilot/gpt-5-mini', 'google-gemini-cli/gemini-3-flash-preview']}},
                {'id': 'quick', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['github-copilot/gpt-5-mini', 'google-gemini-cli/gemini-3-flash-preview']}},
                {'id': 'think', 'model': {'primary': 'openai-codex/gpt-5.3-codex', 'fallbacks': ['github-copilot/gpt-5-mini', 'google-gemini-cli/gemini-3-flash-preview']}},
            ],
        },
    }

def test_assert_policy_passes_for_expected_ladders():
    cfg = _cfg()
    cfg['agents']['defaults']['workspace'] = str(Path.home() / '.openclaw' / 'workspace')
    result = assert_policy(cfg)
    assert result['owners'] == ['owner-1']
    assert result['defaults_thinking'] == 'low'
    assert result['required_subscription_fallbacks'] == ['github-copilot/gpt-5-mini', 'google-gemini-cli/gemini-3-flash-preview']
    assert result['memory']['enabled'] is False
    assert result['memory']['provider'] == 'local'
    assert result['memory']['fallback'] == 'none'

def test_non_owner_cannot_model_or_think_switch():
    cfg = _cfg()
    assert command_authorized(cfg, 'owner-1', '/model openai-codex/gpt-5.3-codex')
    assert not command_authorized(cfg, 'outsider', '/model openai-codex/gpt-5.3-codex')
    assert not command_authorized(cfg, 'outsider', '/think high')
