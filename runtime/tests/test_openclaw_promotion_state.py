from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


def test_seq_allocate_is_monotonic(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    state_dir = tmp_path / "state"

    cmd = [
        "python3",
        "runtime/tools/openclaw_promotion_state.py",
        "--state-dir",
        str(state_dir),
        "seq-allocate",
        "--instance",
        "coo",
    ]
    first = _run(cmd, repo)
    second = _run(cmd, repo)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    first_obj = json.loads(first.stdout)
    second_obj = json.loads(second.stdout)
    assert int(second_obj["change_seq"]) == int(first_obj["change_seq"]) + 1


def test_apply_rejects_replay_ticket(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    state_dir = tmp_path / "state"
    packet_dir = tmp_path / "packet"
    bin_dir = tmp_path / "bin"
    packet_dir.mkdir(parents=True)
    bin_dir.mkdir(parents=True)

    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    now = int(time.time())
    packet = {
        "packet_id": "pkt-1",
        "target_commit": head_sha,
        "target_version": "1.0.0",
        "previous_version": "0.9.0",
        "ticket": {
            "ticket_id": "ticket-1",
            "change_seq": 7,
            "target_instance": "coo",
            "issued_at": now,
            "expires_at": now + 3600,
            "tip_at_issue": head_sha,
            "issuer": "coo",
            "signature": "UNSIGNED",
        },
    }
    (packet_dir / "promotion_packet.json").write_text(json.dumps(packet) + "\n", encoding="utf-8")
    (bin_dir / "openclaw").write_text(
        '#!/usr/bin/env bash\nif [ "$1" = "--version" ]; then\n  echo "1.0.0"\n  exit 0\nfi\nexit 1\n',
        encoding="utf-8",
    )
    (bin_dir / "openclaw").chmod(0o755)

    attestation = tmp_path / "attestation.json"
    attestation.write_text(
        json.dumps(
            {
                "attestation_type": "preclose",
                "issued_unix": now,
                "expires_unix": now + 600,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    apply_cmd = [
        "python3",
        "runtime/tools/openclaw_promotion_state.py",
        "--state-dir",
        str(state_dir),
        "apply",
        "--packet-dir",
        str(packet_dir),
        "--attestation",
        str(attestation),
    ]
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    first = subprocess.run(
        apply_cmd, cwd=repo, check=False, capture_output=True, text=True, env=env
    )
    second = subprocess.run(
        apply_cmd, cwd=repo, check=False, capture_output=True, text=True, env=env
    )

    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["pass"] is True

    assert second.returncode == 1
    second_payload = json.loads(second.stdout)
    assert second_payload["pass"] is False
    assert "promotion_replay_detected" in second_payload["errors"]


def test_normalize_version_strips_prefixes() -> None:
    from runtime.tools.openclaw_promotion_state import _normalize_version

    assert _normalize_version("2026.3.13") == "2026.3.13"
    assert _normalize_version("OpenClaw CLI v2026.3.13") == "2026.3.13"
    assert _normalize_version("v1.2.3") == "1.2.3"
    assert _normalize_version("openclaw/1.0.0-beta.1") == "1.0.0-beta.1"
    assert _normalize_version("  Version: 3.14.159  ") == "3.14.159"
    assert _normalize_version("") == ""
    assert _normalize_version("no-version-here") == "no-version-here"


def test_apply_accepts_prefixed_version_output(tmp_path: Path) -> None:
    """apply succeeds when openclaw --version outputs 'OpenClaw CLI v<ver>' matching packet target."""
    repo = Path(__file__).resolve().parents[2]
    state_dir = tmp_path / "state"
    packet_dir = tmp_path / "packet"
    bin_dir = tmp_path / "bin"
    packet_dir.mkdir(parents=True)
    bin_dir.mkdir(parents=True)

    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    now = int(time.time())
    packet = {
        "packet_id": "pkt-prefix",
        "target_commit": head_sha,
        "target_version": "2026.3.13",
        "previous_version": "2026.3.2",
        "ticket": {
            "ticket_id": "ticket-prefix",
            "change_seq": 9,
            "target_instance": "coo",
            "issued_at": now,
            "expires_at": now + 3600,
            "tip_at_issue": head_sha,
            "issuer": "coo",
            "signature": "UNSIGNED",
        },
    }
    (packet_dir / "promotion_packet.json").write_text(json.dumps(packet) + "\n", encoding="utf-8")
    # Fake openclaw that outputs prefixed version string
    (bin_dir / "openclaw").write_text(
        '#!/usr/bin/env bash\nif [ "$1" = "--version" ]; then\n  echo "OpenClaw CLI v2026.3.13"\n  exit 0\nfi\nexit 1\n',
        encoding="utf-8",
    )
    (bin_dir / "openclaw").chmod(0o755)

    attestation = tmp_path / "attestation.json"
    attestation.write_text(
        json.dumps({"attestation_type": "preclose", "issued_unix": now, "expires_unix": now + 600})
        + "\n",
        encoding="utf-8",
    )

    apply_cmd = [
        "python3",
        "runtime/tools/openclaw_promotion_state.py",
        "--state-dir",
        str(state_dir),
        "apply",
        "--packet-dir",
        str(packet_dir),
        "--attestation",
        str(attestation),
    ]
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    proc = subprocess.run(apply_cmd, cwd=repo, check=False, capture_output=True, text=True, env=env)

    assert proc.returncode == 0, f"Expected success but got rc={proc.returncode}: {proc.stdout}"
    assert json.loads(proc.stdout)["pass"] is True


def test_apply_rejects_when_installed_version_does_not_match_packet(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    state_dir = tmp_path / "state"
    packet_dir = tmp_path / "packet"
    bin_dir = tmp_path / "bin"
    packet_dir.mkdir(parents=True)
    bin_dir.mkdir(parents=True)

    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    now = int(time.time())
    packet = {
        "packet_id": "pkt-2",
        "target_commit": head_sha,
        "target_version": "2026.3.13",
        "previous_version": "2026.3.2",
        "ticket": {
            "ticket_id": "ticket-2",
            "change_seq": 8,
            "target_instance": "coo",
            "issued_at": now,
            "expires_at": now + 3600,
            "tip_at_issue": head_sha,
            "issuer": "coo",
            "signature": "UNSIGNED",
        },
    }
    (packet_dir / "promotion_packet.json").write_text(json.dumps(packet) + "\n", encoding="utf-8")
    (bin_dir / "openclaw").write_text(
        '#!/usr/bin/env bash\nif [ "$1" = "--version" ]; then\n  echo "2026.3.2"\n  exit 0\nfi\nexit 1\n',
        encoding="utf-8",
    )
    (bin_dir / "openclaw").chmod(0o755)

    attestation = tmp_path / "attestation.json"
    attestation.write_text(
        json.dumps(
            {
                "attestation_type": "preclose",
                "issued_unix": now,
                "expires_unix": now + 600,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    apply_cmd = [
        "python3",
        "runtime/tools/openclaw_promotion_state.py",
        "--state-dir",
        str(state_dir),
        "apply",
        "--packet-dir",
        str(packet_dir),
        "--attestation",
        str(attestation),
    ]
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    proc = subprocess.run(apply_cmd, cwd=repo, check=False, capture_output=True, text=True, env=env)

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["pass"] is False
    assert payload["errors"] == ["installed_version_mismatch:2026.3.13:2026.3.2"]
