#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Dict, List
DAILY_PRIMARY='openai-codex/gpt-5.3-codex'
DAILY_FALLBACKS=['google-gemini-cli/gemini-3-flash-preview']
REVIEW_PRIMARY='openai-codex/gpt-5.3-codex'
REVIEW_FALLBACKS=['github-copilot/claude-opus-4.6']
MANUAL_ONLY_MODELS=['openrouter/pony-alpha','openrouter/deepseek-v3.2','opencode/kimi-k2.5-free']
OWNER_ONLY_COMMANDS={'/model','/models','/think'}

def _agent_by_id(cfg: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    for item in ((cfg.get('agents') or {}).get('list') or []):
        if isinstance(item, dict) and item.get('id') == agent_id:
            return item
    return {}

def _owner_allow_from(cfg: Dict[str, Any]) -> List[str]:
    raw = (((cfg.get('commands') or {}).get('ownerAllowFrom')) or [])
    if not isinstance(raw, list):
        return []
    return sorted({str(x).strip() for x in raw if str(x).strip()})

def _model_cfg(entry: Dict[str, Any]) -> Dict[str, Any]:
    model = entry.get('model')
    return model if isinstance(model, dict) else {}

def _assert_ladder(entry: Dict[str, Any], primary: str, fallbacks: List[str], label: str) -> None:
    model = _model_cfg(entry)
    got_primary = str(model.get('primary', ''))
    got_fallbacks = model.get('fallbacks')
    if not isinstance(got_fallbacks, list):
        got_fallbacks = []
    if got_primary != primary:
        raise AssertionError(f'{label} primary mismatch: {got_primary} != {primary}')
    if got_fallbacks != fallbacks:
        raise AssertionError(f'{label} fallbacks mismatch: {got_fallbacks} != {fallbacks}')

def _assert_manual_models_not_in_fallbacks(cfg: Dict[str, Any]) -> None:
    all_fallbacks: set[str] = set()
    defaults = ((cfg.get('agents') or {}).get('defaults') or {})
    default_fallbacks = (((defaults.get('model') or {}).get('fallbacks')) or [])
    if isinstance(default_fallbacks, list):
        all_fallbacks.update(str(x) for x in default_fallbacks)
    for agent_id in ('main', 'quick', 'think'):
        model = _model_cfg(_agent_by_id(cfg, agent_id))
        fallbacks = model.get('fallbacks')
        if isinstance(fallbacks, list):
            all_fallbacks.update(str(x) for x in fallbacks)
    for model_id in MANUAL_ONLY_MODELS:
        if model_id in all_fallbacks:
            raise AssertionError(f'manual-only model present in fallback list: {model_id}')

def command_authorized(cfg: Dict[str, Any], sender: str, command: str) -> bool:
    cmd = command.strip().split(' ', 1)[0].lower()
    if cmd not in OWNER_ONLY_COMMANDS:
        return True
    owners = _owner_allow_from(cfg)
    if not owners:
        return False
    return sender in owners

def assert_policy(cfg: Dict[str, Any]) -> Dict[str, Any]:
    defaults = ((cfg.get('agents') or {}).get('defaults') or {})
    defaults_think = str(defaults.get('thinkingDefault') or 'unknown')
    if defaults_think not in {'low', 'off'}:
        raise AssertionError(f'agents.defaults.thinkingDefault must be low/off, got {defaults_think}')
    _assert_ladder(_agent_by_id(cfg, 'main'), DAILY_PRIMARY, DAILY_FALLBACKS, 'main')
    _assert_ladder(_agent_by_id(cfg, 'quick'), DAILY_PRIMARY, DAILY_FALLBACKS, 'quick')
    _assert_ladder(_agent_by_id(cfg, 'think'), REVIEW_PRIMARY, REVIEW_FALLBACKS, 'think')
    _assert_manual_models_not_in_fallbacks(cfg)
    owners = _owner_allow_from(cfg)
    if not owners:
        raise AssertionError('commands.ownerAllowFrom must be non-empty')
    owner = owners[0]
    if not command_authorized(cfg, owner, '/model openai-codex/gpt-5.3-codex'):
        raise AssertionError('owner must be authorized for /model')
    if command_authorized(cfg, '__non_owner__', '/model openai-codex/gpt-5.3-codex'):
        raise AssertionError('non-owner must be rejected for /model')
    if command_authorized(cfg, '__non_owner__', '/think high'):
        raise AssertionError('non-owner must be rejected for /think')
    return {
        'daily_ladder': {'primary': DAILY_PRIMARY, 'fallbacks': DAILY_FALLBACKS},
        'review_ladder': {'primary': REVIEW_PRIMARY, 'fallbacks': REVIEW_FALLBACKS},
        'manual_only_models': MANUAL_ONLY_MODELS,
        'owners': owners,
        'defaults_thinking': defaults_think,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description='Assert OpenClaw model policy invariants.')
    parser.add_argument('--config', default=str(Path.home() / '.openclaw' / 'openclaw.json'))
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    result = assert_policy(cfg)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=True))
    else:
        print(f'POLICY_ASSERT_PASS config={args.config}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
