from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CLASSIFY_SNIPPET = r"""
import json
import re
import sys

model_re = re.compile(r'^[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)+$', re.IGNORECASE)
d = json.load(open(sys.argv[1], encoding='utf-8', errors='replace'))
lines = open(sys.argv[2], encoding='utf-8', errors='replace').read().splitlines()
has_rows = any(
    (cols := line.strip().split()) and len(cols) >= 5 and model_re.match(cols[0])
    for line in lines
    if line.strip() and not line.startswith('Model ') and not line.startswith('rc=') and not line.startswith('BUILD_REPO=')
)
raise SystemExit(0 if d.get('auth_missing_providers') and has_rows else 1)
"""

AUTH_HEALTH_PARSE_SNIPPET = r"""
import json
import sys

obj = json.load(open(sys.argv[1], encoding='utf-8', errors='replace'))
state = str(obj.get('state') or 'unknown').strip() or 'unknown'
reason = str(obj.get('reason_code') or 'auth_health_reason_missing').strip() or 'auth_health_reason_missing'
action = str(obj.get('recommended_action') or 'none').strip() or 'none'
print(f"{state}\t{reason}\t{action}")
"""


def _classify(tmp_path: Path, payload: dict[str, object], models_list_text: str) -> str:
    json_path = tmp_path / "model_ladder_policy_assert.json"
    list_path = tmp_path / "models_list_raw.txt"
    json_path.write_text(json.dumps(payload, ensure_ascii=True) + "\n", encoding="utf-8")
    list_path.write_text(models_list_text, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-c", CLASSIFY_SNIPPET, str(json_path), str(list_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    return "model_ladder_auth_failed" if proc.returncode == 0 else "model_ladder_policy_failed"


def test_classifies_auth_failure_when_auth_missing_and_model_rows_present(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        {"auth_missing_providers": ["openai-codex"], "violations": [], "policy_ok": False},
        "Model Input Ctx Local Auth Tags\nopenai-codex/gpt-5.3-codex text+image 266k no yes configured\n",
    )
    assert result == "model_ladder_auth_failed"


def test_classifies_policy_failure_when_auth_missing_is_empty(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        {"auth_missing_providers": [], "violations": ["ladder mismatch"], "policy_ok": False},
        "Model Input Ctx Local Auth Tags\nopenai-codex/gpt-5.3-codex text+image 266k no yes configured\n",
    )
    assert result == "model_ladder_policy_failed"


def test_classifies_policy_failure_when_models_list_has_no_parseable_rows(tmp_path: Path) -> None:
    result = _classify(
        tmp_path,
        {"auth_missing_providers": ["openai-codex"], "violations": [], "policy_ok": False},
        "",
    )
    assert result == "model_ladder_policy_failed"


def test_parses_auth_health_refresh_reuse_reason_and_action(tmp_path: Path) -> None:
    path = tmp_path / "auth_health.json"
    path.write_text(
        json.dumps(
            {
                "state": "invalid_missing",
                "reason_code": "refresh_token_reused",
                "recommended_action": "python3 runtime/tools/openclaw_codex_auth_repair.py --apply --json",
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "-c", AUTH_HEALTH_PARSE_SNIPPET, str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip().split("\t") == [
        "invalid_missing",
        "refresh_token_reused",
        "python3 runtime/tools/openclaw_codex_auth_repair.py --apply --json",
    ]
