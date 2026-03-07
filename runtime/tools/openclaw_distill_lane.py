#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence


REASON_CODES = {
    "recursive_call_blocked",
    "protected_path",
    "forbidden_command",
    "forbidden_class",
    "unclassified_or_below_threshold",
    "payload_over_cap",
    "distill_lane_unavailable",
    "schema_failure",
    "distill_call_failed",
    "duplicate_raw_hash",
    "health_state_invalid",
}
ALLOWED_STATUS = {"ok", "bypass", "insufficient"}
HEALTHY_PREFLIGHT_STATUS = "ok"
ALLOWED_TEMPLATE_IDS = {"actionable_faults", "exact_question"}
FORBIDDEN_CLASSES = {
    "diffs",
    "receipts",
    "hashes",
    "manifests",
    "governance_packets",
    "acceptance_evidence",
}
PROTECTED_ROOTS = (
    "docs/00_foundations/",
    "docs/01_governance/",
    "config/governance/",
    "artifacts/review_packets/",
    "artifacts/terminal/",
    "artifacts/checkpoints/",
    "artifacts/evidence/",
    "artifacts/receipts/",
)
MIN_ELIGIBLE_BYTES = 8 * 1024
MAX_PAYLOAD_BYTES = 64 * 1024
WRAPPER_SCHEMA_VERSION = "2"
UNKNOWN_SENTINEL = "unknown"
HEALTH_EVENT_CAUSE_HEALTHY = "healthy_requested_mode"
HEALTH_EVENT_CAUSE_REQUESTED_OFF = "requested_off"
HEALTH_EVENT_CAUSE_HEALTH_INVALID = "health_state_invalid"
HEALTH_FILENAME = "health.json"
PAYLOAD_DIRNAME = "payloads"
AUDIT_FILENAME = "audit.jsonl"
SEEN_HASHES_FILENAME = "seen_raw_hashes.json"
CHEAP_LANE_ID = os.environ.get("LIFEOS_DISTILL_CHEAP_LANE", "quick")
CHEAP_MODEL_TARGET = os.environ.get("LIFEOS_DISTILL_CHEAP_MODEL", UNKNOWN_SENTINEL)
HEALTH_CHECK_CADENCE_S = int(os.environ.get("LIFEOS_DISTILL_HEALTH_CADENCE_S", "900"))
CHEAP_LANE_PROBE_TIMEOUT_S = int(os.environ.get("LIFEOS_DISTILL_CHEAP_LANE_PROBE_TIMEOUT_S", "5"))
PREFLIGHT_DISTILL_TIMEOUT_S = int(os.environ.get("LIFEOS_DISTILL_PREFLIGHT_TIMEOUT_S", "15"))
LIVE_DISTILL_TIMEOUT_S = int(os.environ.get("LIFEOS_DISTILL_LIVE_TIMEOUT_S", "20"))
CANONICAL_PREFLIGHT_FIXTURE_NAME = "openclaw_models_status_v1"
CANONICAL_PREFLIGHT_TEMPLATE_ID = "actionable_faults"
CANONICAL_PREFLIGHT_REQUIRED_ENTITY = "preflight_fixture.py::test_smoke"
CANONICAL_PREFLIGHT_PAYLOAD = "\n".join(
    [
        "FAILED preflight_fixture.py::test_smoke - AssertionError: expected auth token",
        "providers:",
        "  github-copilot/gpt-5-mini: unavailable",
        "  openai-codex/gpt-5.3-codex: configured",
    ]
)
JSON_OBJECT_RE = re.compile(r"\{.*\}", re.S)


@dataclass(frozen=True)
class MatchRule:
    executable: str
    argv_prefix: tuple[str, ...]
    wrapper_commands: tuple[str, ...] = ()


DENY_RULES = (
    MatchRule("git", ("git", "diff")),
    MatchRule("git", ("git", "show")),
    MatchRule("git", ("git", "log")),
)
ACTIVE_ALLOW_RULES = (
    MatchRule(
        "openclaw",
        ("openclaw", "models", "status"),
        ("coo openclaw -- models status",),
    ),
    MatchRule("pytest", ("pytest",)),
    MatchRule("python", ("python", "-m", "pytest")),
    MatchRule("python3", ("python3", "-m", "pytest")),
    MatchRule("rg", ("rg",)),
)
SHADOW_ONLY_RULES = (
    MatchRule(
        "openclaw",
        ("openclaw", "status", "--all", "--usage"),
        ("coo openclaw -- status --all --usage",),
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_token(value: str) -> str:
    return str(value or "").strip().lower()


def _normalize_fingerprint_field(value: str | None) -> str:
    normalized = _norm_token(value or "")
    return normalized if normalized else UNKNOWN_SENTINEL


def _compute_sha256(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        handle.write("\n")


def _load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _is_text_like(payload: str) -> bool:
    return "\x00" not in payload


def _normalize_argv(argv: Sequence[str]) -> tuple[str, ...]:
    return tuple(_norm_token(item) for item in argv if str(item).strip())


def _rule_matches(rule: MatchRule, executable: str, argv: tuple[str, ...], wrapper_command: str) -> bool:
    if executable != rule.executable:
        return False
    if len(argv) < len(rule.argv_prefix):
        return False
    if argv[: len(rule.argv_prefix)] == rule.argv_prefix:
        return True
    return wrapper_command in rule.wrapper_commands


def _match_rules(rules: Iterable[MatchRule], executable: str, argv: tuple[str, ...], wrapper_command: str) -> bool:
    return any(_rule_matches(rule, executable, argv, wrapper_command) for rule in rules)


def _path_is_protected(source_path: str) -> bool:
    normalized = source_path.replace("\\", "/").lstrip("./")
    return any(normalized.startswith(root) for root in PROTECTED_ROOTS)


def _validate_output_schema(payload: Any, *, template_id: str, raw_payload_sha256: str) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "schema_failure"
    if payload.get("status") not in ALLOWED_STATUS:
        return False, "schema_failure"
    if payload.get("template_id") != template_id:
        return False, "schema_failure"
    summary = payload.get("summary")
    entities = payload.get("key_entities")
    if not isinstance(summary, list) or len(summary) > 5 or not all(isinstance(item, str) for item in summary):
        return False, "schema_failure"
    if not isinstance(entities, list) or len(entities) > 12 or not all(isinstance(item, str) for item in entities):
        return False, "schema_failure"
    if payload.get("raw_payload_sha256") != raw_payload_sha256:
        return False, "schema_failure"
    bypass_reason = payload.get("bypass_reason")
    if bypass_reason is not None and bypass_reason not in REASON_CODES:
        return False, "schema_failure"
    return True, ""


def build_prompt(*, template_id: str, payload: str, question: str, raw_payload_sha256: str, traffic_class: str, source_command: str) -> str:
    if template_id == "actionable_faults":
        instruction = (
            "Summarise only the actionable faults from this artefact in at most 5 bullets. "
            "Include exact file, function, test, command, or provider names when present. "
            "Do not infer beyond the text."
        )
    else:
        instruction = (
            f"Answer this exact question from the artefact only: {question}. "
            "Return only grounded points from the text. Include exact file, function, test, command, "
            "or provider names when present. If the artefact is insufficient, say insufficient evidence."
        )
    return "\n".join(
        [
            "Return STRICT JSON only with keys: status, template_id, summary, key_entities, raw_payload_sha256, traffic_class, source_command, bypass_reason.",
            f"template_id={template_id}",
            f"raw_payload_sha256={raw_payload_sha256}",
            f"traffic_class={traffic_class}",
            f"source_command={source_command}",
            instruction,
            "Artefact follows:",
            payload,
        ]
    )


def _extract_text_from_openclaw_response(raw_text: str) -> str:
    try:
        payload = json.loads(raw_text)
    except Exception:
        return ""
    items = payload.get("payloads") or []
    parts: list[str] = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    return "\n".join(parts).strip()


def _extract_json_object(raw_text: str) -> Optional[dict[str, Any]]:
    text = _extract_text_from_openclaw_response(raw_text) or raw_text.strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    match = JSON_OBJECT_RE.search(text)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _run(cmd: Sequence[str], *, env: dict[str, str], timeout_s: int = 30) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout_s, check=False, env=env)
        return int(proc.returncode), proc.stdout or "", proc.stderr or ""
    except Exception as exc:
        return 1, "", f"{type(exc).__name__}:{exc}"


def _run_openclaw(cmd_tail: Sequence[str], *, openclaw_bin: str, profile: str, env: dict[str, str], timeout_s: int) -> tuple[int, str, str]:
    cmd: list[str] = [openclaw_bin]
    if profile:
        cmd.extend(["--profile", profile])
    cmd.extend(cmd_tail)
    return _run(cmd, env=env, timeout_s=timeout_s)


def _probe_openclaw_version(*, openclaw_bin: str, profile: str, env: dict[str, str]) -> str:
    rc, stdout, _stderr = _run_openclaw(["--version"], openclaw_bin=openclaw_bin, profile=profile, env=env, timeout_s=CHEAP_LANE_PROBE_TIMEOUT_S)
    if rc != 0:
        return UNKNOWN_SENTINEL
    first = (stdout.strip().splitlines() or [UNKNOWN_SENTINEL])[0]
    return _normalize_fingerprint_field(first)


def build_runtime_context(*, openclaw_bin: str, profile: str, env: dict[str, str]) -> dict[str, str]:
    return {
        "openclaw_version": _probe_openclaw_version(openclaw_bin=openclaw_bin, profile=profile, env=env),
        "channel_if_known": _normalize_fingerprint_field(env.get("OPENCLAW_CHANNEL") or env.get("OPENCLAW_UPDATE_CHANNEL")),
        "cheap_lane_id": _normalize_fingerprint_field(env.get("LIFEOS_DISTILL_CHEAP_LANE") or CHEAP_LANE_ID),
        "cheap_model_target": _normalize_fingerprint_field(env.get("LIFEOS_DISTILL_CHEAP_MODEL") or CHEAP_MODEL_TARGET),
        "wrapper_schema_version": WRAPPER_SCHEMA_VERSION,
    }


def build_compatibility_fingerprint(context: dict[str, str]) -> tuple[str, dict[str, str]]:
    payload = {
        "openclaw_version": _normalize_fingerprint_field(context.get("openclaw_version")),
        "channel_if_known": _normalize_fingerprint_field(context.get("channel_if_known")),
        "cheap_lane_id": _normalize_fingerprint_field(context.get("cheap_lane_id")),
        "cheap_model_target": _normalize_fingerprint_field(context.get("cheap_model_target")),
        "wrapper_schema_version": _normalize_fingerprint_field(context.get("wrapper_schema_version")),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _compute_sha256(serialized), payload


def audit_root_for_state(state_dir: Path) -> Path:
    return state_dir / "runtime" / "gates" / "distill"


def health_path_for_state(state_dir: Path) -> Path:
    return audit_root_for_state(state_dir) / HEALTH_FILENAME


def _read_health_receipt(state_dir: Path) -> tuple[dict[str, Any] | None, bool]:
    health_path = health_path_for_state(state_dir)
    if not health_path.exists():
        return None, False
    try:
        payload = json.loads(health_path.read_text(encoding="utf-8"))
    except Exception:
        return None, False
    if not isinstance(payload, dict):
        return None, False
    return payload, True


def _emit_audit_event(state_dir: Path, payload: dict[str, Any]) -> None:
    _append_jsonl(audit_root_for_state(state_dir) / AUDIT_FILENAME, payload)


def _write_health_receipt(state_dir: Path, payload: dict[str, Any]) -> None:
    _write_json(health_path_for_state(state_dir), payload)


def preflight_quick_lane(*, openclaw_bin: str, profile: str, env: dict[str, str]) -> dict[str, Any]:
    rc, stdout, stderr = _run_openclaw(
        ["agent", "--local", "--agent", CHEAP_LANE_ID, "--message", "Reply READY", "--json"],
        openclaw_bin=openclaw_bin,
        profile=profile,
        env=env,
        timeout_s=CHEAP_LANE_PROBE_TIMEOUT_S,
    )
    text = _extract_text_from_openclaw_response(stdout)
    ok = rc == 0 and bool(text)
    return {
        "ok": ok,
        "rc": rc,
        "stderr": stderr.strip(),
        "stdout": stdout,
    }


def probe_usage_visibility(*, openclaw_bin: str, profile: str, env: dict[str, str]) -> dict[str, Any]:
    rc, stdout, stderr = _run_openclaw(
        ["status", "--usage"],
        openclaw_bin=openclaw_bin,
        profile=profile,
        env=env,
        timeout_s=CHEAP_LANE_PROBE_TIMEOUT_S,
    )
    return {
        "ok": rc == 0 and bool(stdout.strip()),
        "rc": rc,
        "stdout": stdout,
        "stderr": stderr.strip(),
    }


def run_distill(*, openclaw_bin: str, profile: str, env: dict[str, str], prompt: str, timeout_s: int) -> tuple[int, dict[str, Any] | None, str]:
    distill_env = dict(env)
    distill_env["DISTILL_LANE"] = "1"
    rc, stdout, stderr = _run_openclaw(
        ["agent", "--local", "--agent", CHEAP_LANE_ID, "--message", prompt, "--json"],
        openclaw_bin=openclaw_bin,
        profile=profile,
        env=distill_env,
        timeout_s=timeout_s,
    )
    if rc != 0:
        return rc, None, stderr.strip()
    return rc, _extract_json_object(stdout), ""


def _preflight_accepts(payload: dict[str, Any] | None, *, raw_payload_sha256: str) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("status") != HEALTHY_PREFLIGHT_STATUS:
        return False
    if payload.get("template_id") != CANONICAL_PREFLIGHT_TEMPLATE_ID:
        return False
    if payload.get("raw_payload_sha256") != raw_payload_sha256:
        return False
    summary = payload.get("summary")
    entities = payload.get("key_entities")
    if not isinstance(summary, list) or not summary or len(summary) > 5:
        return False
    if not isinstance(entities, list):
        return False
    if CANONICAL_PREFLIGHT_REQUIRED_ENTITY not in entities:
        return False
    return True


def run_health_preflight(*, state_dir: Path, openclaw_bin: str, profile: str, env: dict[str, str], requested_mode: str) -> dict[str, Any]:
    state_dir.mkdir(parents=True, exist_ok=True)
    context = build_runtime_context(openclaw_bin=openclaw_bin, profile=profile, env=env)
    fingerprint, fingerprint_payload = build_compatibility_fingerprint(context)
    cheap_lane_probe = preflight_quick_lane(openclaw_bin=openclaw_bin, profile=profile, env=env)
    usage_probe = probe_usage_visibility(openclaw_bin=openclaw_bin, profile=profile, env=env)
    preflight_payload = CANONICAL_PREFLIGHT_PAYLOAD
    preflight_hash = _compute_sha256(preflight_payload)
    prompt = build_prompt(
        template_id=CANONICAL_PREFLIGHT_TEMPLATE_ID,
        payload=preflight_payload,
        question="What are the actionable faults?",
        raw_payload_sha256=preflight_hash,
        traffic_class="repo_scans",
        source_command=CANONICAL_PREFLIGHT_FIXTURE_NAME,
    )
    distilled: dict[str, Any] | None = None
    distill_error = ""
    if cheap_lane_probe["ok"]:
        _rc, distilled, distill_error = run_distill(
            openclaw_bin=openclaw_bin,
            profile=profile,
            env=env,
            prompt=prompt,
            timeout_s=PREFLIGHT_DISTILL_TIMEOUT_S,
        )
    preflight_ok = cheap_lane_probe["ok"] and usage_probe["ok"] and _preflight_accepts(distilled, raw_payload_sha256=preflight_hash)
    receipt = {
        "ts_utc": _utc_now(),
        "requested_mode": requested_mode,
        "effective_mode": "shadow",
        "compatibility_fingerprint": fingerprint,
        "compatibility_fields": fingerprint_payload,
        "openclaw_version": context["openclaw_version"],
        "channel_if_known": context["channel_if_known"],
        "cheap_lane_id": context["cheap_lane_id"],
        "cheap_model_target": context["cheap_model_target"],
        "wrapper_schema_version": context["wrapper_schema_version"],
        "preflight_ok": preflight_ok,
        "last_successful_preflight_fingerprint": fingerprint if preflight_ok else "",
        "last_preflight_ts_utc": _utc_now(),
        "usage_visibility_ok": usage_probe["ok"],
        "cheap_lane_probe_ok": cheap_lane_probe["ok"],
        "health_check_cadence_s": HEALTH_CHECK_CADENCE_S,
        "last_bypass_reason": "" if preflight_ok else "health_state_invalid",
    }
    _write_health_receipt(state_dir, receipt)
    _emit_audit_event(
        state_dir,
        {
            "event_type": "health",
            "ts_utc": receipt["ts_utc"],
            "requested_mode": requested_mode,
            "effective_mode": "shadow",
            "cause": "explicit_preflight",
            "compatibility_fingerprint": fingerprint,
            "preflight_ok": preflight_ok,
            "usage_visibility_ok": usage_probe["ok"],
            "cheap_lane_selected": cheap_lane_probe["ok"],
            "bypass_reason": "" if preflight_ok else "health_state_invalid",
            "provider_hint": f"openclaw/{context['cheap_lane_id']}",
            "error_detail": distill_error,
        },
    )
    return {
        "ok": preflight_ok,
        "health_path": str(health_path_for_state(state_dir)),
        "compatibility_fingerprint": fingerprint,
        "usage_visibility_ok": usage_probe["ok"],
        "cheap_lane_probe_ok": cheap_lane_probe["ok"],
    }


def classify_payload(
    *,
    source_path: str,
    source_executable: str,
    argv: Sequence[str],
    wrapper_command: str,
    traffic_class: str,
    raw_payload_sha256: str,
    payload_bytes: int,
    text_like: bool,
    state_dir: Path,
) -> dict[str, Any]:
    executable = _norm_token(Path(source_executable or (argv[0] if argv else "")).name)
    normalized_argv = _normalize_argv(argv)
    normalized_wrapper = " ".join(_norm_token(part) for part in wrapper_command.split() if part.strip())
    seen_path = audit_root_for_state(state_dir) / SEEN_HASHES_FILENAME
    seen_hashes = _load_json(seen_path, {})
    if os.environ.get("DISTILL_LANE") == "1":
        return {"decision": "bypass", "reason": "recursive_call_blocked", "replacement_allowed": False}
    if isinstance(seen_hashes, dict) and raw_payload_sha256 in seen_hashes:
        return {"decision": "bypass", "reason": "duplicate_raw_hash", "replacement_allowed": False}
    if source_path and _path_is_protected(source_path):
        return {"decision": "bypass", "reason": "protected_path", "replacement_allowed": False}
    if _match_rules(DENY_RULES, executable, normalized_argv, normalized_wrapper):
        return {"decision": "bypass", "reason": "forbidden_command", "replacement_allowed": False}
    if traffic_class in FORBIDDEN_CLASSES:
        return {"decision": "bypass", "reason": "forbidden_class", "replacement_allowed": False}
    if not text_like or payload_bytes < MIN_ELIGIBLE_BYTES:
        return {"decision": "bypass", "reason": "unclassified_or_below_threshold", "replacement_allowed": False}
    if payload_bytes > MAX_PAYLOAD_BYTES:
        return {"decision": "bypass", "reason": "payload_over_cap", "replacement_allowed": False}
    if _match_rules(ACTIVE_ALLOW_RULES, executable, normalized_argv, normalized_wrapper):
        return {"decision": "eligible_active", "reason": "", "replacement_allowed": True}
    if _match_rules(SHADOW_ONLY_RULES, executable, normalized_argv, normalized_wrapper):
        return {"decision": "eligible_shadow", "reason": "", "replacement_allowed": False}
    return {"decision": "bypass", "reason": "unclassified_or_below_threshold", "replacement_allowed": False}


def resolve_effective_mode(*, requested_mode: str, state_dir: Path, runtime_context: dict[str, str]) -> tuple[str, str, dict[str, Any] | None]:
    if requested_mode == "off":
        return "off", HEALTH_EVENT_CAUSE_REQUESTED_OFF, None
    health_receipt, health_valid = _read_health_receipt(state_dir)
    if not health_valid or health_receipt is None:
        return "shadow", HEALTH_EVENT_CAUSE_HEALTH_INVALID, None
    fingerprint, _payload = build_compatibility_fingerprint(runtime_context)
    if health_receipt.get("compatibility_fingerprint") != fingerprint:
        return "shadow", HEALTH_EVENT_CAUSE_HEALTH_INVALID, health_receipt
    if health_receipt.get("last_successful_preflight_fingerprint") != fingerprint:
        return "shadow", HEALTH_EVENT_CAUSE_HEALTH_INVALID, health_receipt
    if health_receipt.get("preflight_ok") is not True:
        return "shadow", HEALTH_EVENT_CAUSE_HEALTH_INVALID, health_receipt
    return requested_mode, HEALTH_EVENT_CAUSE_HEALTHY, health_receipt


def render_summary(payload: dict[str, Any]) -> str:
    lines = [f"DISTILL_STATUS={payload['status']}", f"TEMPLATE_ID={payload['template_id']}"]
    summary = payload.get("summary") or []
    entities = payload.get("key_entities") or []
    if summary:
        lines.append("SUMMARY_BEGIN")
        lines.extend(f"- {item}" for item in summary)
        lines.append("SUMMARY_END")
    if entities:
        lines.append(f"KEY_ENTITIES={', '.join(entities)}")
    lines.append(f"RAW_PAYLOAD_SHA256={payload['raw_payload_sha256']}")
    lines.append(f"TRAFFIC_CLASS={payload['traffic_class']}")
    lines.append(f"SOURCE_COMMAND={payload['source_command']}")
    return "\n".join(lines)


def process_payload(args: argparse.Namespace) -> dict[str, Any]:
    state_dir = Path(args.state_dir).expanduser()
    audit_root = audit_root_for_state(state_dir)
    audit_root.mkdir(parents=True, exist_ok=True)

    payload_text = _read_text(Path(args.payload_file))
    payload_bytes = len(payload_text.encode("utf-8"))
    raw_payload_sha256 = _compute_sha256(payload_text)
    text_like = _is_text_like(payload_text)
    requested_mode = "off" if not args.enabled else args.mode
    runtime_context = build_runtime_context(openclaw_bin=args.openclaw_bin, profile=args.openclaw_profile, env=os.environ.copy())
    classification = classify_payload(
        source_path=args.source_path,
        source_executable=args.source_executable,
        argv=json.loads(args.argv_json),
        wrapper_command=args.wrapper_command,
        traffic_class=args.traffic_class,
        raw_payload_sha256=raw_payload_sha256,
        payload_bytes=payload_bytes,
        text_like=text_like,
        state_dir=state_dir,
    )

    effective_mode, mode_cause, health_receipt = resolve_effective_mode(
        requested_mode=requested_mode,
        state_dir=state_dir,
        runtime_context=runtime_context,
    )
    cheap_lane_selected = False
    distilled: dict[str, Any] | None = None
    bypass_reason = classification.get("reason", "")
    latency_ms = 0
    mode_transition = health_receipt is None or health_receipt.get("effective_mode") != effective_mode

    should_force_raw_on_health = requested_mode == "active" and effective_mode == "shadow" and mode_cause == HEALTH_EVENT_CAUSE_HEALTH_INVALID

    if classification["decision"].startswith("eligible") and effective_mode in {"shadow", "active"} and not should_force_raw_on_health:
        cheap_lane_selected = True
        started = datetime.now(timezone.utc)
        prompt = build_prompt(
            template_id=args.template_id,
            payload=payload_text,
            question=args.question,
            raw_payload_sha256=raw_payload_sha256,
            traffic_class=args.traffic_class,
            source_command=args.source_command,
        )
        rc, distilled, _error_detail = run_distill(
            openclaw_bin=args.openclaw_bin,
            profile=args.openclaw_profile,
            env=os.environ.copy(),
            prompt=prompt,
            timeout_s=LIVE_DISTILL_TIMEOUT_S,
        )
        latency_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        if rc != 0 or distilled is None:
            bypass_reason = "distill_call_failed"
            distilled = None
        else:
            ok, schema_reason = _validate_output_schema(
                distilled,
                template_id=args.template_id,
                raw_payload_sha256=raw_payload_sha256,
            )
            if not ok:
                bypass_reason = schema_reason
                distilled = None
            else:
                bypass_reason = ""
    elif should_force_raw_on_health and classification["decision"].startswith("eligible"):
        bypass_reason = "health_state_invalid"

    result = {
        "raw_payload_sha256": raw_payload_sha256,
        "raw_payload_bytes": payload_bytes,
        "traffic_class": args.traffic_class,
        "source_command": args.source_command,
        "template_id": args.template_id,
        "classifier_decision": classification["decision"],
        "replacement_allowed": classification["replacement_allowed"] and effective_mode == "active" and distilled is not None,
        "requested_mode": requested_mode,
        "effective_mode": effective_mode,
        "bypass_reason": bypass_reason or classification.get("reason", ""),
        "rendered_text": render_summary(distilled) if distilled is not None else "",
        "cheap_lane_selected": cheap_lane_selected,
        "distilled_bytes": len(json.dumps(distilled, ensure_ascii=True).encode("utf-8")) if distilled is not None else 0,
        "status": "ok" if distilled is not None else "bypass",
        "health_check_cadence_s": HEALTH_CHECK_CADENCE_S,
        "cheap_lane_probe_timeout_s": CHEAP_LANE_PROBE_TIMEOUT_S,
        "preflight_distill_timeout_s": PREFLIGHT_DISTILL_TIMEOUT_S,
        "live_distill_timeout_s": LIVE_DISTILL_TIMEOUT_S,
    }
    payload_store = audit_root / PAYLOAD_DIRNAME / f"{raw_payload_sha256}.txt"
    if classification["decision"].startswith("eligible"):
        payload_store.parent.mkdir(parents=True, exist_ok=True)
        if not payload_store.exists():
            payload_store.write_text(payload_text, encoding="utf-8")
    audit_record = {
        "event_type": "attempt",
        "ts_utc": _utc_now(),
        "requested_mode": requested_mode,
        "effective_mode": effective_mode,
        "template_id": args.template_id,
        "source_executable": args.source_executable,
        "source_command": args.source_command,
        "wrapper_command": args.wrapper_command,
        "traffic_class": args.traffic_class,
        "classifier_decision": classification["decision"],
        "bypass_reason": result["bypass_reason"],
        "raw_payload_sha256": raw_payload_sha256,
        "raw_payload_bytes": payload_bytes,
        "distilled_bytes": result["distilled_bytes"],
        "cheap_lane_selected": cheap_lane_selected,
        "provider_hint": f"openclaw/{runtime_context['cheap_lane_id']}" if cheap_lane_selected else "",
        "latency_ms": latency_ms,
    }
    _emit_audit_event(state_dir, audit_record)
    if mode_transition:
        _emit_audit_event(
            state_dir,
            {
                "event_type": "mode_transition",
                "ts_utc": _utc_now(),
                "from_mode": health_receipt.get("effective_mode", UNKNOWN_SENTINEL) if isinstance(health_receipt, dict) else UNKNOWN_SENTINEL,
                "to_mode": effective_mode,
                "cause": mode_cause,
            },
        )
    should_refresh_health = (
        health_receipt is None
        or mode_transition
        or result["bypass_reason"] in {"distill_lane_unavailable", "distill_call_failed", "schema_failure", "health_state_invalid"}
    )
    if should_refresh_health:
        fingerprint, fingerprint_payload = build_compatibility_fingerprint(runtime_context)
        receipt_payload = dict(health_receipt or {})
        receipt_payload.update(
            {
                "ts_utc": _utc_now(),
                "requested_mode": requested_mode,
                "effective_mode": effective_mode,
                "compatibility_fingerprint": fingerprint,
                "compatibility_fields": fingerprint_payload,
                "openclaw_version": runtime_context["openclaw_version"],
                "channel_if_known": runtime_context["channel_if_known"],
                "cheap_lane_id": runtime_context["cheap_lane_id"],
                "cheap_model_target": runtime_context["cheap_model_target"],
                "wrapper_schema_version": runtime_context["wrapper_schema_version"],
                "health_check_cadence_s": HEALTH_CHECK_CADENCE_S,
                "last_bypass_reason": result["bypass_reason"],
            }
        )
        _write_health_receipt(state_dir, receipt_payload)
    if distilled is not None:
        seen_hashes = _load_json(audit_root / SEEN_HASHES_FILENAME, {})
        if not isinstance(seen_hashes, dict):
            seen_hashes = {}
        seen_hashes[raw_payload_sha256] = _utc_now()
        _write_json(audit_root / SEEN_HASHES_FILENAME, seen_hashes)
    result["audit_path"] = str(audit_root / AUDIT_FILENAME)
    result["health_path"] = str(health_path_for_state(state_dir))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic OpenClaw distillation helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    process = subparsers.add_parser("process")
    process.add_argument("--payload-file", required=True)
    process.add_argument("--source-path", default="")
    process.add_argument("--source-executable", required=True)
    process.add_argument("--argv-json", required=True)
    process.add_argument("--wrapper-command", default="")
    process.add_argument("--traffic-class", required=True)
    process.add_argument("--source-command", required=True)
    process.add_argument("--template-id", choices=sorted(ALLOWED_TEMPLATE_IDS), required=True)
    process.add_argument("--question", default="What are the actionable faults?")
    process.add_argument("--mode", choices=("off", "shadow", "active"), default="shadow")
    process.add_argument("--enabled", action="store_true")
    process.add_argument("--state-dir", required=True)
    process.add_argument("--openclaw-bin", default=os.environ.get("OPENCLAW_BIN", "openclaw"))
    process.add_argument("--openclaw-profile", default=os.environ.get("OPENCLAW_PROFILE", ""))

    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--state-dir", required=True)
    preflight.add_argument("--mode", choices=("off", "shadow", "active"), default="active")
    preflight.add_argument("--openclaw-bin", default=os.environ.get("OPENCLAW_BIN", "openclaw"))
    preflight.add_argument("--openclaw-profile", default=os.environ.get("OPENCLAW_PROFILE", ""))
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "preflight":
        result = run_health_preflight(
            state_dir=Path(args.state_dir).expanduser(),
            openclaw_bin=args.openclaw_bin,
            profile=args.openclaw_profile,
            env=os.environ.copy(),
            requested_mode=args.mode,
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        return 0 if result["ok"] else 1

    result = process_payload(args)
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
