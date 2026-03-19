#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class VerifyResult:
    ok: bool
    errors: List[str]
    packet: Dict[str, Any]


class LockedParityState:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.lock_path = root / "parity.lock"
        self._fh = None

    def __enter__(self) -> "LockedParityState":
        self.root.mkdir(parents=True, exist_ok=True)
        self._fh = self.lock_path.open("a+", encoding="utf-8")
        fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fh is not None:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            self._fh.close()



def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    with tmp.open("r+", encoding="utf-8") as fh:
        fh.flush()
        os.fsync(fh.fileno())
    tmp.replace(path)



def _read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default)
    if not isinstance(payload, dict):
        return dict(default)
    return payload



def _git_head() -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _normalize_version(raw: str) -> str:
    import re
    raw = raw.strip()
    m = re.search(r"(\d+(?:\.\d+)+(?:-[A-Za-z0-9._+-]+)?)", raw)
    return m.group(1) if m else raw


def _current_openclaw_version() -> str:
    try:
        proc = subprocess.run(["openclaw", "--version"], capture_output=True, text=True, check=False, timeout=10)
    except subprocess.TimeoutExpired:
        return ""
    if proc.returncode != 0:
        return ""
    for line in (proc.stdout or "").splitlines():
        candidate = line.strip()
        if candidate:
            return _normalize_version(candidate)
    for line in (proc.stderr or "").splitlines():
        candidate = line.strip()
        if candidate:
            return _normalize_version(candidate)
    return ""



def _is_ancestor(base: str, target: str) -> bool:
    if not base or not target:
        return False
    proc = subprocess.run(["git", "merge-base", "--is-ancestor", base, target], capture_output=True, text=True, check=False)
    return proc.returncode == 0



def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()



def _load_packet(packet_dir: Path) -> Dict[str, Any]:
    return json.loads((packet_dir / "promotion_packet.json").read_text(encoding="utf-8"))



def verify_packet(packet_dir: Path, staleness_hours: int) -> VerifyResult:
    errors: List[str] = []
    try:
        packet = _load_packet(packet_dir)
    except Exception as exc:
        return VerifyResult(ok=False, errors=[f"packet_read_failed:{type(exc).__name__}"], packet={})

    ticket = packet.get("ticket")
    if not isinstance(ticket, dict):
        errors.append("ticket_missing")
        return VerifyResult(ok=False, errors=errors, packet=packet)

    required_packet = ["target_commit", "target_version", "previous_version"]
    for key in required_packet:
        if not str(packet.get(key) or "").strip():
            errors.append(f"packet_field_missing:{key}")

    required_ticket = ["ticket_id", "change_seq", "target_instance", "issued_at", "expires_at", "tip_at_issue"]
    for key in required_ticket:
        if not str(ticket.get(key) or "").strip():
            errors.append(f"ticket_field_missing:{key}")

    try:
        change_seq = int(ticket.get("change_seq"))
        if change_seq <= 0:
            errors.append("change_seq_non_positive")
    except Exception:
        errors.append("change_seq_invalid")

    now = int(time.time())
    try:
        issued = int(ticket.get("issued_at"))
        expires = int(ticket.get("expires_at"))
        if now > expires:
            errors.append("ticket_expired")
        if now - issued > staleness_hours * 3600:
            errors.append("ticket_stale")
    except Exception:
        errors.append("ticket_time_invalid")

    target_commit = str(packet.get("target_commit") or "").strip()
    tip_at_issue = str(ticket.get("tip_at_issue") or "").strip()
    if target_commit and tip_at_issue and not _is_ancestor(tip_at_issue, target_commit):
        errors.append("target_not_descendant_of_tip_at_issue")

    return VerifyResult(ok=len(errors) == 0, errors=errors, packet=packet)



def cmd_seq_allocate(args: argparse.Namespace) -> int:
    state_root = Path(args.state_dir).expanduser()
    alloc_path = state_root / "sequence_allocator.json"

    with LockedParityState(state_root):
        alloc = _read_json(alloc_path, {"next_seq": 1, "allocator_id": "coo", "issued_tickets": 0})
        next_seq = int(alloc.get("next_seq") or 1)
        now = int(time.time())
        ticket = {
            "ticket_id": str(uuid.uuid4()),
            "change_seq": next_seq,
            "tip_at_issue": _git_head(),
            "target_instance": args.instance,
            "issued_at": now,
            "expires_at": now + int(args.ttl_hours) * 3600,
            "issuer": "coo",
            "signature": "UNSIGNED",
        }
        alloc["next_seq"] = next_seq + 1
        alloc["issued_tickets"] = int(alloc.get("issued_tickets") or 0) + 1
        _atomic_write_json(alloc_path, alloc)

    print(json.dumps(ticket, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0



def cmd_verify(args: argparse.Namespace) -> int:
    result = verify_packet(Path(args.packet_dir), staleness_hours=int(args.staleness_hours))
    payload = {
        "pass": result.ok,
        "errors": result.errors,
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0 if result.ok else 1



def cmd_apply(args: argparse.Namespace) -> int:
    attestation = Path(args.attestation)
    if not attestation.exists():
        print(json.dumps({"pass": False, "errors": ["attestation_missing"]}, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        return 1

    try:
        attest_obj = json.loads(attestation.read_text(encoding="utf-8"))
    except Exception:
        print(json.dumps({"pass": False, "errors": ["attestation_invalid"]}, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        return 1

    now = int(time.time())
    if int(attest_obj.get("expires_unix") or 0) < now:
        print(json.dumps({"pass": False, "errors": ["attestation_expired"]}, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        return 1

    result = verify_packet(Path(args.packet_dir), staleness_hours=int(args.staleness_hours))
    if not result.ok:
        print(json.dumps({"pass": False, "errors": result.errors}, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        return 1

    packet = result.packet
    target_version = _normalize_version(str(packet.get("target_version") or ""))
    observed_version = _current_openclaw_version()
    if not observed_version:
        print(
            json.dumps(
                {"pass": False, "errors": ["installed_version_unavailable"]},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
        )
        return 1
    if observed_version != target_version:
        print(
            json.dumps(
                {
                    "pass": False,
                    "errors": [f"installed_version_mismatch:{target_version}:{observed_version}"],
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
        )
        return 1

    ticket = packet.get("ticket") or {}
    state_root = Path(args.state_dir).expanduser()
    state_path = state_root / "state.json"
    journal_path = state_root / "journal.json"
    receipts_dir = state_root / "applied_receipts"

    tx_id = str(uuid.uuid4())
    with LockedParityState(state_root):
        state = _read_json(
            state_path,
            {
                "schema_version": 1,
                "floors": {},
                "used_ticket_ids": [],
                "last_tx_id": "",
            },
        )
        floors = state.get("floors")
        if not isinstance(floors, dict):
            floors = {}
        used = state.get("used_ticket_ids")
        if not isinstance(used, list):
            used = []

        instance = str(ticket.get("target_instance") or "")
        ticket_id = str(ticket.get("ticket_id") or "")
        seq = int(ticket.get("change_seq") or 0)
        floor = int(floors.get(instance) or 0)

        if ticket_id in used:
            print(json.dumps({"pass": False, "errors": ["promotion_replay_detected"]}, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
            return 1
        if seq <= floor:
            print(json.dumps({"pass": False, "errors": ["promotion_downgrade_detected"]}, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
            return 1

        journal = _read_json(journal_path, {"entries": []})
        entries = journal.get("entries")
        if not isinstance(entries, list):
            entries = []
        entries.append({"tx_id": tx_id, "phase": "intent", "ticket_id": ticket_id, "change_seq": seq, "ts": now})
        journal["entries"] = entries
        _atomic_write_json(journal_path, journal)

        floors[instance] = seq
        used.append(ticket_id)
        state["floors"] = floors
        state["used_ticket_ids"] = used
        state["last_tx_id"] = tx_id
        _atomic_write_json(state_path, state)

        entries.append({"tx_id": tx_id, "phase": "commit", "ticket_id": ticket_id, "change_seq": seq, "ts": int(time.time())})
        journal["entries"] = entries
        _atomic_write_json(journal_path, journal)

        receipts_dir.mkdir(parents=True, exist_ok=True)
        receipt = {
            "tx_id": tx_id,
            "ticket_id": ticket_id,
            "instance": instance,
            "change_seq": seq,
            "packet_sha256": _sha256_file(Path(args.packet_dir) / "promotion_packet.json"),
            "applied_at_unix": int(time.time()),
        }
        _atomic_write_json(receipts_dir / f"{tx_id}.json", receipt)

    print(json.dumps({"pass": True, "tx_id": tx_id}, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0



def cmd_record(args: argparse.Namespace) -> int:
    state_root = Path(args.state_dir).expanduser()
    inbox = state_root / "applied_receipts"
    inbox.mkdir(parents=True, exist_ok=True)
    packet_path = Path(args.packet_dir) / "promotion_packet.json"
    if not packet_path.exists():
        print(json.dumps({"pass": False, "errors": ["packet_missing"]}, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        return 1
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet_id = str(packet.get("packet_id") or uuid.uuid4())
    out = inbox / f"record_{packet_id}.json"
    payload = {
        "packet_id": packet_id,
        "recorded_at_unix": int(time.time()),
        "packet_sha256": _sha256_file(packet_path),
        "attestation": str(args.attestation or ""),
    }
    _atomic_write_json(out, payload)
    print(json.dumps({"pass": True, "record": str(out)}, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenClaw promotion runtime state operations.")
    parser.add_argument("--state-dir", default=str(Path.home() / ".openclaw" / "runtime" / "parity"))

    sub = parser.add_subparsers(dest="command", required=True)

    p_alloc = sub.add_parser("seq-allocate")
    p_alloc.add_argument("--instance", required=True)
    p_alloc.add_argument("--ttl-hours", type=int, default=24)
    p_alloc.set_defaults(func=cmd_seq_allocate)

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--packet-dir", required=True)
    p_verify.add_argument("--staleness-hours", type=int, default=72)
    p_verify.set_defaults(func=cmd_verify)

    p_apply = sub.add_parser("apply")
    p_apply.add_argument("--packet-dir", required=True)
    p_apply.add_argument("--attestation", required=True)
    p_apply.add_argument("--staleness-hours", type=int, default=72)
    p_apply.set_defaults(func=cmd_apply)

    p_record = sub.add_parser("record")
    p_record.add_argument("--packet-dir", required=True)
    p_record.add_argument("--attestation", default="")
    p_record.set_defaults(func=cmd_record)

    return parser



def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
