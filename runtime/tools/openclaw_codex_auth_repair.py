#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROVIDER = "openai-codex"
DEFAULT_AGENT_ID = "main"
DEFAULT_RECEIPT_ROOT = (
    REPO_ROOT / "artifacts" / "evidence" / "openclaw" / "codex_auth_repair"
)


@dataclass(frozen=True)
class CodexProfile:
    profile_id: str
    provider: str
    profile_type: str
    expires_ms: int | None
    email: str | None
    account_id: str | None
    managed_by: str | None
    refresh_present: bool
    access_present: bool
    valid: bool

    @property
    def kind_rank(self) -> int:
        if self.email and ":" in self.profile_id:
            suffix = self.profile_id.split(":", 1)[1]
            if suffix and suffix not in {"default", "codex-cli"}:
                return 0
        if self.profile_id.endswith(":default"):
            return 1
        if self.profile_id.endswith(":codex-cli"):
            return 2
        return 3

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["expires_utc"] = format_epoch_ms(self.expires_ms)
        return payload


@dataclass(frozen=True)
class CodexRepairAnalysis:
    provider: str
    current_order: list[str]
    proposed_order: list[str]
    chosen_profile_id: str | None
    stale_order: bool
    profiles: list[CodexProfile]
    codex_cli_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "current_order": self.current_order,
            "proposed_order": self.proposed_order,
            "chosen_profile_id": self.chosen_profile_id,
            "stale_order": self.stale_order,
            "profiles": [profile.to_dict() for profile in self.profiles],
            "codex_cli_summary": self.codex_cli_summary,
        }


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ts_utc() -> str:
    return now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def compact_ts_utc() -> str:
    return now_utc().strftime("%Y%m%dT%H%M%SZ")


def format_epoch_ms(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def load_codex_profiles(
    auth_profiles_payload: dict[str, Any],
    *,
    provider: str = DEFAULT_PROVIDER,
    now_ms: int | None = None,
) -> list[CodexProfile]:
    profiles = auth_profiles_payload.get("profiles")
    if not isinstance(profiles, dict):
        return []

    if now_ms is None:
        now_ms = int(now_utc().timestamp() * 1000)

    rows: list[CodexProfile] = []
    for profile_id, payload in sorted(profiles.items()):
        if not isinstance(payload, dict):
            continue
        if str(payload.get("provider") or "").strip() != provider:
            continue
        profile_type = str(payload.get("type") or "").strip()
        expires_ms = _optional_int(payload.get("expires"))
        refresh_present = bool(payload.get("refresh"))
        access_present = bool(payload.get("access"))
        valid = (
            profile_type == "oauth"
            and refresh_present
            and expires_ms is not None
            and expires_ms > now_ms
        )
        rows.append(
            CodexProfile(
                profile_id=str(profile_id),
                provider=provider,
                profile_type=profile_type,
                expires_ms=expires_ms,
                email=_string_or_none(payload.get("email")),
                account_id=_string_or_none(payload.get("accountId")),
                managed_by=_string_or_none(payload.get("managedBy")),
                refresh_present=refresh_present,
                access_present=access_present,
                valid=valid,
            )
        )
    return rows


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def rank_profiles(profiles: Iterable[CodexProfile]) -> list[CodexProfile]:
    valid_profiles = [profile for profile in profiles if profile.valid]
    return sorted(
        valid_profiles,
        key=lambda profile: (
            -(profile.expires_ms or 0),
            profile.kind_rank,
            profile.profile_id,
        ),
    )


def build_proposed_order(
    current_order: Sequence[str],
    ranked_profiles: Sequence[CodexProfile],
    all_profile_ids: Sequence[str],
) -> list[str]:
    proposed: list[str] = []
    seen: set[str] = set()

    def add(profile_id: str) -> None:
        if profile_id not in seen:
            proposed.append(profile_id)
            seen.add(profile_id)

    for profile in ranked_profiles:
        add(profile.profile_id)
    for profile_id in current_order:
        add(profile_id)
    for profile_id in sorted(all_profile_ids):
        add(profile_id)
    return proposed


def read_auth_state_order(
    auth_state_payload: dict[str, Any],
    *,
    provider: str = DEFAULT_PROVIDER,
) -> list[str]:
    order = auth_state_payload.get("order")
    if not isinstance(order, dict):
        return []
    provider_order = order.get(provider)
    if not isinstance(provider_order, list):
        return []
    return [str(item) for item in provider_order if str(item).strip()]


def summarize_codex_cli_auth(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "auth_mode": None,
        "has_refresh_token": False,
        "has_access_token": False,
        "has_id_token": False,
    }
    if not path.exists():
        return summary
    try:
        payload = _load_json(path)
    except Exception as exc:
        summary["error"] = f"{type(exc).__name__}:{exc}"
        return summary

    tokens = payload.get("tokens")
    summary["auth_mode"] = _string_or_none(payload.get("auth_mode"))
    summary["has_refresh_token"] = bool(isinstance(tokens, dict) and tokens.get("refresh_token"))
    summary["has_access_token"] = bool(isinstance(tokens, dict) and tokens.get("access_token"))
    summary["has_id_token"] = bool(isinstance(tokens, dict) and tokens.get("id_token"))
    return summary


def analyze_codex_auth_setup(
    auth_state_payload: dict[str, Any],
    auth_profiles_payload: dict[str, Any],
    *,
    provider: str = DEFAULT_PROVIDER,
    now_ms: int | None = None,
    codex_auth_path: Path | None = None,
) -> CodexRepairAnalysis:
    profiles = load_codex_profiles(auth_profiles_payload, provider=provider, now_ms=now_ms)
    ranked_profiles = rank_profiles(profiles)
    current_order = read_auth_state_order(auth_state_payload, provider=provider)
    proposed_order = build_proposed_order(
        current_order,
        ranked_profiles,
        [profile.profile_id for profile in profiles],
    )
    chosen_profile_id = ranked_profiles[0].profile_id if ranked_profiles else None
    stale_order = bool(chosen_profile_id and current_order[:1] != [chosen_profile_id])
    codex_cli_summary = summarize_codex_cli_auth(codex_auth_path) if codex_auth_path else {}
    return CodexRepairAnalysis(
        provider=provider,
        current_order=current_order,
        proposed_order=proposed_order,
        chosen_profile_id=chosen_profile_id,
        stale_order=stale_order,
        profiles=profiles,
        codex_cli_summary=codex_cli_summary,
    )


def planned_apply_commands(
    *,
    openclaw_bin: str,
    provider: str,
    proposed_order: Sequence[str],
) -> list[list[str]]:
    if not proposed_order:
        return []
    return [
        [openclaw_bin, "models", "auth", "order", "set", "--provider", provider, *proposed_order],
        [openclaw_bin, "secrets", "reload", "--json"],
    ]


def _run_command(cmd: Sequence[str]) -> dict[str, Any]:
    proc = subprocess.run(list(cmd), capture_output=True, text=True, check=False)
    return {
        "cmd": list(cmd),
        "exit_code": int(proc.returncode),
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }


def write_rollback_receipt(
    receipt_root: Path,
    analysis: CodexRepairAnalysis,
    *,
    command_results: Sequence[dict[str, Any]],
    applied: bool,
) -> Path:
    receipt_dir = receipt_root / compact_ts_utc()
    receipt_dir.mkdir(parents=True, exist_ok=False)
    receipt_path = receipt_dir / "rollback_receipt.json"
    payload = {
        "ts_utc": ts_utc(),
        "provider": analysis.provider,
        "applied": applied,
        "current_order": analysis.current_order,
        "proposed_order": analysis.proposed_order,
        "chosen_profile_id": analysis.chosen_profile_id,
        "stale_order": analysis.stale_order,
        "profiles": [profile.to_dict() for profile in analysis.profiles],
        "codex_cli_summary": analysis.codex_cli_summary,
        "commands": list(command_results),
    }
    receipt_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return receipt_path


def apply_repair(
    analysis: CodexRepairAnalysis,
    *,
    provider: str,
    openclaw_bin: str,
    receipt_root: Path,
    runner: Callable[[Sequence[str]], dict[str, Any]] = _run_command,
) -> dict[str, Any]:
    commands = planned_apply_commands(
        openclaw_bin=openclaw_bin,
        provider=provider,
        proposed_order=analysis.proposed_order,
    )
    results = [runner(command) for command in commands]
    receipt_path = write_rollback_receipt(
        receipt_root,
        analysis,
        command_results=results,
        applied=True,
    )
    ok = all(int(result.get("exit_code", 1)) == 0 for result in results)
    return {
        "applied": True,
        "ok": ok,
        "commands": results,
        "receipt_path": str(receipt_path),
    }


def default_paths(state_dir: Path, agent_id: str) -> tuple[Path, Path]:
    agent_dir = state_dir / "agents" / agent_id / "agent"
    return agent_dir / "auth-state.json", agent_dir / "auth-profiles.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect and repair stale OpenClaw auth order for openai-codex."
    )
    parser.add_argument("--state-dir", default=str(Path.home() / ".openclaw"))
    parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--codex-auth-path", default=str(Path.home() / ".codex" / "auth.json"))
    parser.add_argument("--openclaw-bin", default=os.environ.get("OPENCLAW_BIN", "openclaw"))
    parser.add_argument("--receipt-root", default=str(DEFAULT_RECEIPT_ROOT))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    state_dir = Path(args.state_dir).expanduser()
    auth_state_path, auth_profiles_path = default_paths(state_dir, args.agent_id)
    codex_auth_path = Path(args.codex_auth_path).expanduser()

    auth_state_payload = _load_json(auth_state_path)
    auth_profiles_payload = _load_json(auth_profiles_path)
    analysis = analyze_codex_auth_setup(
        auth_state_payload,
        auth_profiles_payload,
        provider=args.provider,
        codex_auth_path=codex_auth_path,
    )

    payload: dict[str, Any] = {
        "ts_utc": ts_utc(),
        "agent_id": args.agent_id,
        "state_dir": str(state_dir),
        "auth_state_path": str(auth_state_path),
        "auth_profiles_path": str(auth_profiles_path),
        **analysis.to_dict(),
        "repair_needed": analysis.stale_order,
        "recommended_command": (
            "python3 runtime/tools/openclaw_codex_auth_repair.py --apply --json"
            if analysis.stale_order
            else "none"
        ),
    }

    if args.apply:
        if not analysis.chosen_profile_id:
            payload["applied"] = False
            payload["ok"] = False
            payload["error"] = "no_valid_oauth_profile"
        else:
            apply_result = apply_repair(
                analysis,
                provider=args.provider,
                openclaw_bin=args.openclaw_bin,
                receipt_root=Path(args.receipt_root),
            )
            payload.update(apply_result)
    else:
        payload["applied"] = False
        payload["ok"] = True

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(
            json.dumps(
                {
                    "provider": payload["provider"],
                    "repair_needed": payload["repair_needed"],
                    "chosen_profile_id": payload["chosen_profile_id"],
                    "recommended_command": payload["recommended_command"],
                },
                ensure_ascii=True,
            )
        )
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
