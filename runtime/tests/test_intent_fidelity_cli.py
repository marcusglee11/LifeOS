import json
import subprocess
import sys
from pathlib import Path

FIXTURE_DIR = Path("runtime/tests/fixtures/intent_fidelity")


def _run_cli(source: str, brief: str):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "lifeos",
            "intent-fidelity",
            "check",
            "--source",
            str(FIXTURE_DIR / source),
            "--brief",
            str(FIXTURE_DIR / brief),
            "--brief-type",
            "worker_prompt",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_intent_fidelity_cli_good_brief_exits_zero_with_json_report():
    result = _run_cli("v120_source.md", "v120_good_brief.md")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["dry_run"] is True
    assert payload["implementation_authority_granted"] is False
    assert payload["fidelity_report"]["decision"] == "pass"


def test_intent_fidelity_cli_bad_brief_exits_nonzero_with_json_report():
    result = _run_cli("v120_source.md", "v120_bad_brief.md")
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["fidelity_report"]["decision"] == "fail_closed"
    assert payload["conductor_verification"]["implementation_authority_granted"] is False
