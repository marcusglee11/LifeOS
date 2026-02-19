#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PROVIDER_RE = re.compile(r"\bprovider\s+([a-z0-9._-]+)\b", re.IGNORECASE)
PROVIDER_COOLDOWN_RE = re.compile(r"\bprovider\s+([a-z0-9._-]+)\s+is\s+in\s+cooldown\b", re.IGNORECASE)
COOLDOWN_RE = re.compile(r"(in cooldown|all profiles unavailable|profiles are unavailable)", re.IGNORECASE)
INVALID_MISSING_RE = re.compile(
    r"(expired|missing|invalid|unauthorized|not authenticated|authentication required|token has been invalidated)",
    re.IGNORECASE,
)
EXPIRING_RE = re.compile(r"(expiring soon|expires in\s*[0-9]+(?:m|h))", re.IGNORECASE)


@dataclass(frozen=True)
class CommandResult:
    rc: int
    out: str
    err: str


@dataclass(frozen=True)
class MigCandidate:
    name: str
    scope: str
    location: str
    target_size: int
    score: int


def _json_loads_safe(raw: str) -> Any:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _basename_from_uri(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.rstrip("/").split("/")[-1]


def _zone_from_instance_uri(value: str) -> str:
    text = str(value or "")
    marker = "/zones/"
    if marker not in text:
        return ""
    suffix = text.split(marker, 1)[1]
    return suffix.split("/", 1)[0].strip()


def _run(
    cmd: list[str],
    *,
    timeout_s: int,
    env: dict[str, str] | None = None,
    stdin_text: str | None = None,
) -> CommandResult:
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_text,
            text=True,
            capture_output=True,
            timeout=max(1, int(timeout_s)),
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            rc=124,
            out=str(getattr(exc, "stdout", "") or "").strip(),
            err=f"timeout_after_{int(timeout_s)}s",
        )
    except Exception as exc:
        return CommandResult(rc=1, out="", err=f"subprocess_error:{type(exc).__name__}:{exc}")
    return CommandResult(rc=int(proc.returncode), out=(proc.stdout or "").strip(), err=(proc.stderr or "").strip())


def _gcloud_env() -> dict[str, str]:
    env = os.environ.copy()
    config_dir = env.get("CLOUDSDK_CONFIG") or str(Path("/tmp/gcloud-codex"))
    env["CLOUDSDK_CONFIG"] = config_dir
    env["CLOUDSDK_CORE_DISABLE_PROMPTS"] = "1"
    Path(config_dir).mkdir(parents=True, exist_ok=True)
    return env


def detect_provider(output_text: str) -> str:
    text = str(output_text or "")
    match = PROVIDER_COOLDOWN_RE.search(text) or PROVIDER_RE.search(text)
    if not match:
        return "multi-provider"
    provider = str(match.group(1) or "").strip().lower()
    return provider or "multi-provider"


def classify_auth_health(exit_code: int, output_text: str) -> dict[str, str]:
    text = str(output_text or "")
    low = text.lower()
    provider = detect_provider(text)

    if exit_code == 0:
        if EXPIRING_RE.search(text):
            return {
                "state": "expiring",
                "reason_code": "expiring_warning",
                "provider": provider,
            }
        return {"state": "ok", "reason_code": "ok", "provider": provider}

    if COOLDOWN_RE.search(text):
        return {
            "state": "cooldown",
            "reason_code": "provider_cooldown",
            "provider": provider,
        }

    if exit_code == 2 or EXPIRING_RE.search(text):
        return {
            "state": "expiring",
            "reason_code": "expiring_nonzero",
            "provider": provider,
        }

    if exit_code == 1 or INVALID_MISSING_RE.search(low):
        return {
            "state": "invalid_missing",
            "reason_code": "expired_or_missing",
            "provider": provider,
        }

    return {
        "state": "invalid_missing",
        "reason_code": f"check_failed_rc_{exit_code}",
        "provider": provider,
    }


def _parse_mig_candidates(raw: str, preferred_name: str | None = None) -> list[MigCandidate]:
    obj = _json_loads_safe(raw)
    if not isinstance(obj, list):
        return []
    preferred = (preferred_name or "").strip()
    out: list[MigCandidate] = []
    for row in obj:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        zone = _basename_from_uri(str(row.get("zone") or ""))
        region = _basename_from_uri(str(row.get("region") or ""))
        if zone:
            scope = "zone"
            location = zone
        elif region:
            scope = "region"
            location = region
        else:
            continue
        target_size = int(row.get("targetSize") or 0)
        score = 0
        if preferred and name == preferred:
            score += 1000
        if target_size > 0:
            score += 50
        lowered = name.lower()
        if "openclaw" in lowered:
            score += 30
        if "coo" in lowered:
            score += 10
        out.append(
            MigCandidate(
                name=name,
                scope=scope,
                location=location,
                target_size=target_size,
                score=score,
            )
        )
    out.sort(key=lambda c: (c.score, c.target_size, c.name), reverse=True)
    return out


def _pick_running_instance(raw: str, fallback_zone: str) -> tuple[str, str]:
    obj = _json_loads_safe(raw)
    if not isinstance(obj, list):
        return ("", "")
    ranked: list[tuple[int, str, str]] = []
    for row in obj:
        if not isinstance(row, dict):
            continue
        instance_uri = str(row.get("instance") or "").strip()
        if not instance_uri:
            continue
        name = _basename_from_uri(instance_uri)
        if not name:
            continue
        zone = _zone_from_instance_uri(instance_uri) or fallback_zone
        status = str(row.get("instanceStatus") or "").upper()
        action = str(row.get("currentAction") or "NONE").upper()
        score = 0
        if status == "RUNNING":
            score += 100
        if action in {"NONE", ""}:
            score += 20
        if action in {"CREATING", "RECREATING"}:
            score -= 10
        ranked.append((score, name, zone))
    ranked.sort(reverse=True)
    if not ranked:
        return ("", "")
    _, name, zone = ranked[0]
    return name, zone


def _discover_project(gcloud_bin: str, timeout_s: int, env: dict[str, str]) -> tuple[str, str]:
    cmd = [gcloud_bin, "config", "get-value", "project"]
    res = _run(cmd, timeout_s=timeout_s, env=env)
    if res.rc != 0:
        detail = (res.err or res.out or "project_lookup_failed").splitlines()[0]
        return "", detail
    project = (res.out or "").strip()
    if not project:
        return "", "project_not_set"
    return project, ""


def _discover_instance_from_mig(
    *,
    gcloud_bin: str,
    project: str,
    preferred_mig: str | None,
    timeout_s: int,
    env: dict[str, str],
) -> tuple[dict[str, str], str]:
    mig_list_cmd = [
        gcloud_bin,
        "compute",
        "instance-groups",
        "managed",
        "list",
        "--project",
        project,
        "--format=json",
    ]
    mig_res = _run(mig_list_cmd, timeout_s=timeout_s, env=env)
    if mig_res.rc != 0:
        detail = (mig_res.err or mig_res.out or "mig_list_failed").splitlines()[0]
        return {}, detail
    candidates = _parse_mig_candidates(mig_res.out, preferred_name=preferred_mig)
    if preferred_mig:
        candidates = [c for c in candidates if c.name == preferred_mig]
    if not candidates:
        return {}, "no_mig_candidates"

    for mig in candidates:
        list_cmd: list[str] = [
            gcloud_bin,
            "compute",
            "instance-groups",
            "managed",
            "list-instances",
            mig.name,
            "--project",
            project,
            "--format=json",
        ]
        if mig.scope == "zone":
            list_cmd.extend(["--zone", mig.location])
        else:
            list_cmd.extend(["--region", mig.location])
        list_res = _run(list_cmd, timeout_s=timeout_s, env=env)
        if list_res.rc != 0:
            continue
        instance_name, instance_zone = _pick_running_instance(list_res.out, fallback_zone=mig.location)
        if not instance_name or not instance_zone:
            continue
        return (
            {
                "mig_name": mig.name,
                "mig_scope": mig.scope,
                "mig_location": mig.location,
                "instance_name": instance_name,
                "instance_zone": instance_zone,
            },
            "",
        )
    return {}, "no_running_managed_instance"


def _describe_instance(
    *,
    gcloud_bin: str,
    project: str,
    instance: str,
    zone: str,
    timeout_s: int,
    env: dict[str, str],
) -> tuple[dict[str, str], str]:
    cmd = [
        gcloud_bin,
        "compute",
        "instances",
        "describe",
        instance,
        "--project",
        project,
        "--zone",
        zone,
        "--format=json",
    ]
    res = _run(cmd, timeout_s=timeout_s, env=env)
    if res.rc != 0:
        detail = (res.err or res.out or "instance_describe_failed").splitlines()[0]
        return {}, detail
    obj = _json_loads_safe(res.out)
    if not isinstance(obj, dict):
        return {}, "instance_describe_parse_failed"
    nics = obj.get("networkInterfaces")
    internal_ip = ""
    external_ip = ""
    if isinstance(nics, list) and nics and isinstance(nics[0], dict):
        nic0 = nics[0]
        internal_ip = str(nic0.get("networkIP") or "").strip()
        access = nic0.get("accessConfigs")
        if isinstance(access, list) and access and isinstance(access[0], dict):
            external_ip = str(access[0].get("natIP") or "").strip()
    return (
        {
            "status": str(obj.get("status") or "").strip(),
            "internal_ip": internal_ip,
            "external_ip": external_ip,
        },
        "",
    )


def _remote_probe_script() -> str:
    # Script intentionally emits only sanitized JSON summary.
    return r"""#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import json
import os
import pwd
import re
import shutil
import subprocess

PROVIDER_RE = re.compile(r"\bprovider\s+([a-z0-9._-]+)\b", re.IGNORECASE)
PROVIDER_COOLDOWN_RE = re.compile(r"\bprovider\s+([a-z0-9._-]+)\s+is\s+in\s+cooldown\b", re.IGNORECASE)
COOLDOWN_RE = re.compile(r"(in cooldown|all profiles unavailable|profiles are unavailable)", re.IGNORECASE)
INVALID_MISSING_RE = re.compile(
    r"(expired|missing|invalid|unauthorized|not authenticated|authentication required|token has been invalidated)",
    re.IGNORECASE,
)
EXPIRING_RE = re.compile(r"(expiring soon|expires in\s*[0-9]+(?:m|h))", re.IGNORECASE)

SERVICE_USER = str(os.environ.get("OPENCLAW_SERVICE_USER", "garfieldlee11"))
GATEWAY_PORT = int(os.environ.get("OPENCLAW_GATEWAY_PORT", "18789"))


def user_exists(name: str) -> bool:
    try:
        pwd.getpwnam(name)
        return True
    except KeyError:
        return False


def _run(cmd, timeout_s=20, as_service=False):
    effective = list(cmd)
    executed_as = pwd.getpwuid(os.geteuid()).pw_name
    if as_service and user_exists(SERVICE_USER) and executed_as != SERVICE_USER:
        sudo = shutil.which("sudo")
        if sudo:
            can_sudo = subprocess.run(
                [sudo, "-n", "-u", SERVICE_USER, "true"],
                capture_output=True,
                text=True,
                check=False,
            )
            if can_sudo.returncode == 0:
                effective = [sudo, "-n", "-u", SERVICE_USER] + list(cmd)
                executed_as = SERVICE_USER
    try:
        proc = subprocess.run(
            effective,
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout_s)),
            check=False,
        )
    except Exception as exc:
        return {
            "rc": 1,
            "out": "",
            "err": f"subprocess_error:{type(exc).__name__}:{exc}",
            "executed_as": executed_as,
        }
    return {
        "rc": int(proc.returncode),
        "out": (proc.stdout or "").strip(),
        "err": (proc.stderr or "").strip(),
        "executed_as": executed_as,
    }


def _load_json(raw):
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _first_line(raw):
    text = str(raw or "").strip()
    if not text:
        return ""
    return text.splitlines()[0]


def detect_provider(output_text):
    text = str(output_text or "")
    match = PROVIDER_COOLDOWN_RE.search(text) or PROVIDER_RE.search(text)
    if not match:
        return "multi-provider"
    provider = str(match.group(1) or "").strip().lower()
    return provider or "multi-provider"


def classify_auth_health(exit_code, output_text):
    text = str(output_text or "")
    low = text.lower()
    provider = detect_provider(text)
    if exit_code == 0:
        if EXPIRING_RE.search(text):
            return {"state": "expiring", "reason_code": "expiring_warning", "provider": provider}
        return {"state": "ok", "reason_code": "ok", "provider": provider}
    if COOLDOWN_RE.search(text):
        return {"state": "cooldown", "reason_code": "provider_cooldown", "provider": provider}
    if exit_code == 2 or EXPIRING_RE.search(text):
        return {"state": "expiring", "reason_code": "expiring_nonzero", "provider": provider}
    if exit_code == 1 or INVALID_MISSING_RE.search(low):
        return {"state": "invalid_missing", "reason_code": "expired_or_missing", "provider": provider}
    return {"state": "invalid_missing", "reason_code": f"check_failed_rc_{exit_code}", "provider": provider}


host = _run(["hostname"], timeout_s=5)
uptime = _run(["uptime", "-p"], timeout_s=5)
instance_id = _run(
    [
        "curl",
        "-fsS",
        "-H",
        "Metadata-Flavor: Google",
        "http://metadata.google.internal/computeMetadata/v1/instance/id",
    ],
    timeout_s=5,
)
openclaw_path = _run(["bash", "-lc", "command -v openclaw || true"], timeout_s=5, as_service=True)
openclaw_version = _run(["openclaw", "--version"], timeout_s=8, as_service=True)
ports = _run(["ss", "-ltnp"], timeout_s=8)
health = _run(["openclaw", "health", "--json", "--timeout", "8000"], timeout_s=12, as_service=True)
probe = _run(["openclaw", "gateway", "probe", "--json"], timeout_s=12, as_service=True)
channels = _run(["openclaw", "channels", "status", "--json"], timeout_s=12, as_service=True)
models = _run(["openclaw", "models", "status", "--check", "--json"], timeout_s=16, as_service=True)

auth_text = "\n".join([models.get("out", ""), models.get("err", "")]).strip()
if models.get("rc", 1) != 0 and not models.get("out"):
    models_alt = _run(["openclaw", "models", "status", "--check"], timeout_s=16, as_service=True)
    auth_text = "\n".join([models_alt.get("out", ""), models_alt.get("err", "")]).strip()
    models_rc = int(models_alt.get("rc", 1))
else:
    models_rc = int(models.get("rc", 1))
auth = classify_auth_health(models_rc, auth_text)

health_obj = _load_json(health.get("out"))
probe_obj = _load_json(probe.get("out"))
channels_obj = _load_json(channels.get("out"))

listening = False
for line in str(ports.get("out", "")).splitlines():
    if f":{GATEWAY_PORT}" in line:
        listening = True
        break

probe_ok = bool(isinstance(probe_obj, dict) and probe_obj.get("ok") is True)
health_ok = bool(isinstance(health_obj, dict) and health_obj.get("ok") is True)

telegram = {}
if isinstance(channels_obj, dict):
    channels_map = channels_obj.get("channels")
    if isinstance(channels_map, dict):
        telegram = channels_map.get("telegram") or {}

tg_running = bool(telegram.get("running") is True)
tg_mode = str(telegram.get("mode") or "unknown")
tg_last_error = telegram.get("lastError")
tg_last_error_present = tg_last_error not in (None, "", "null")
tg_probe_ok = False
if isinstance(probe_obj, dict):
    targets = probe_obj.get("targets")
    if isinstance(targets, list):
        for target in targets:
            if not isinstance(target, dict):
                continue
            health_map = target.get("health")
            if not isinstance(health_map, dict):
                continue
            h_channels = health_map.get("channels")
            if not isinstance(h_channels, dict):
                continue
            tg_health = h_channels.get("telegram")
            if not isinstance(tg_health, dict):
                continue
            tg_probe = tg_health.get("probe")
            if isinstance(tg_probe, dict) and tg_probe.get("ok") is True:
                tg_probe_ok = True
                break

tg_alive = bool((tg_running and tg_mode in {"polling", "webhook"} and not tg_last_error_present) or tg_probe_ok)

summary = {
    "vm": {
        "hostname": _first_line(host.get("out")),
        "uptime": _first_line(uptime.get("out")),
        "instance_id": _first_line(instance_id.get("out")),
    },
    "openclaw": {
        "service_user": SERVICE_USER,
        "executed_as": str(openclaw_version.get("executed_as") or openclaw_path.get("executed_as") or ""),
        "path": _first_line(openclaw_path.get("out")),
        "version": _first_line(openclaw_version.get("out")),
    },
    "gateway": {
        "port": GATEWAY_PORT,
        "listening": listening,
        "health_ok": health_ok,
        "probe_ok": probe_ok,
        "status_ok": bool((health_ok and listening) or probe_ok),
        "health_rc": int(health.get("rc", 1)),
        "probe_rc": int(probe.get("rc", 1)),
    },
    "telegram": {
        "configured": bool(telegram.get("configured") is True),
        "running": tg_running,
        "mode": tg_mode,
        "last_error_present": tg_last_error_present,
        "probe_ok": tg_probe_ok,
        "alive": tg_alive,
        "status_rc": int(channels.get("rc", 1)),
    },
    "auth": {
        "state": auth["state"],
        "reason_code": auth["reason_code"],
        "provider": auth["provider"],
        "status_rc": models_rc,
    },
}

print(json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
PY
"""


def _run_remote_probe(
    *,
    gcloud_bin: str,
    project: str,
    instance: str,
    zone: str,
    service_user: str,
    gateway_port: int,
    timeout_s: int,
    env: dict[str, str],
    tunnel_through_iap: bool,
) -> tuple[dict[str, Any], str]:
    cmd = [
        gcloud_bin,
        "compute",
        "ssh",
        instance,
        "--project",
        project,
        "--zone",
        zone,
        "--quiet",
        "--command",
        "OPENCLAW_SERVICE_USER="
        + shlex.quote(service_user)
        + " OPENCLAW_GATEWAY_PORT="
        + str(gateway_port)
        + " bash -s",
        "--ssh-flag=-oBatchMode=yes",
        "--ssh-flag=-oStrictHostKeyChecking=accept-new",
    ]
    if tunnel_through_iap:
        cmd.append("--tunnel-through-iap")
    res = _run(cmd, timeout_s=timeout_s, env=env, stdin_text=_remote_probe_script())
    if res.rc != 0:
        detail = (res.err or res.out or "remote_probe_failed").splitlines()[0]
        return {}, detail
    obj = _json_loads_safe(res.out)
    if not isinstance(obj, dict):
        return {}, "remote_probe_parse_failed"
    return obj, ""


def _format_tunnel_cmd(project: str, instance: str, zone: str, local_port: int, gateway_port: int) -> str:
    return (
        f"gcloud compute ssh {shlex.quote(instance)} --project {shlex.quote(project)} "
        f"--zone {shlex.quote(zone)} -- -N -L {int(local_port)}:localhost:{int(gateway_port)}"
    )


def _result_json(
    *,
    ok: bool,
    reason: str,
    discovery: dict[str, Any],
    vm: dict[str, Any],
    gateway: dict[str, Any],
    telegram: dict[str, Any],
    auth: dict[str, Any],
    ui_url: str,
    tunnel_cmd: str,
) -> dict[str, Any]:
    return {
        "ok": bool(ok),
        "reason": str(reason),
        "mig": {
            "name": str(discovery.get("mig_name") or ""),
            "scope": str(discovery.get("mig_scope") or ""),
            "location": str(discovery.get("mig_location") or ""),
            "instance": str(discovery.get("instance_name") or ""),
            "zone": str(discovery.get("instance_zone") or ""),
            "status": str(discovery.get("instance_status") or ""),
            "external_ip": str(discovery.get("external_ip") or ""),
            "internal_ip": str(discovery.get("internal_ip") or ""),
        },
        "vm": vm,
        "gateway": gateway,
        "telegram": telegram,
        "auth": auth,
        "ui": {"url": ui_url, "tunnel_cmd": tunnel_cmd},
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover active MIG instance and run OpenClaw gateway/Telegram/auth operator checks."
    )
    parser.add_argument("--project", help="GCP project ID (defaults to gcloud config project)")
    parser.add_argument("--mig", help="Managed instance group name override")
    parser.add_argument("--instance", help="Instance name override (skips MIG discovery when used with --zone)")
    parser.add_argument("--zone", help="Zone for --instance override")
    parser.add_argument("--service-user", default=os.environ.get("OPENCLAW_SERVICE_USER", "garfieldlee11"))
    parser.add_argument("--gateway-port", type=int, default=int(os.environ.get("OPENCLAW_GATEWAY_PORT", "18789")))
    parser.add_argument("--local-port", type=int, default=int(os.environ.get("OPENCLAW_LOCAL_FORWARD_PORT", "28789")))
    parser.add_argument("--gcloud-bin", default=os.environ.get("GCLOUD_BIN", "gcloud"))
    parser.add_argument("--gcloud-timeout-sec", type=int, default=20)
    parser.add_argument("--ssh-timeout-sec", type=int, default=90)
    parser.add_argument("--tunnel-through-iap", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    env = _gcloud_env()
    project = str(args.project or "").strip()
    if not project:
        project, project_reason = _discover_project(args.gcloud_bin, args.gcloud_timeout_sec, env)
        if not project:
            payload = _result_json(
                ok=False,
                reason=f"project_unavailable:{project_reason}",
                discovery={},
                vm={},
                gateway={},
                telegram={},
                auth={},
                ui_url=f"http://localhost:{args.local_port}",
                tunnel_cmd="",
            )
            if args.json:
                print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
            else:
                print(f"FAIL reason={payload['reason']} ui_url={payload['ui']['url']}")
            return 1

    if args.instance and args.zone:
        discovery = {
            "mig_name": args.mig or "",
            "mig_scope": "manual",
            "mig_location": args.zone,
            "instance_name": args.instance,
            "instance_zone": args.zone,
        }
    else:
        discovery, discover_reason = _discover_instance_from_mig(
            gcloud_bin=args.gcloud_bin,
            project=project,
            preferred_mig=args.mig,
            timeout_s=args.gcloud_timeout_sec,
            env=env,
        )
        if not discovery:
            payload = _result_json(
                ok=False,
                reason=f"discovery_failed:{discover_reason}",
                discovery={},
                vm={},
                gateway={},
                telegram={},
                auth={},
                ui_url=f"http://localhost:{args.local_port}",
                tunnel_cmd="",
            )
            if args.json:
                print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
            else:
                print(f"FAIL reason={payload['reason']} ui_url={payload['ui']['url']}")
            return 1

    describe, describe_reason = _describe_instance(
        gcloud_bin=args.gcloud_bin,
        project=project,
        instance=str(discovery.get("instance_name") or ""),
        zone=str(discovery.get("instance_zone") or ""),
        timeout_s=args.gcloud_timeout_sec,
        env=env,
    )
    if describe:
        discovery["instance_status"] = describe.get("status") or ""
        discovery["internal_ip"] = describe.get("internal_ip") or ""
        discovery["external_ip"] = describe.get("external_ip") or ""
    else:
        discovery["instance_status"] = ""
        discovery["internal_ip"] = ""
        discovery["external_ip"] = ""
        discovery["instance_describe_warning"] = describe_reason

    remote, remote_reason = _run_remote_probe(
        gcloud_bin=args.gcloud_bin,
        project=project,
        instance=str(discovery.get("instance_name") or ""),
        zone=str(discovery.get("instance_zone") or ""),
        service_user=args.service_user,
        gateway_port=args.gateway_port,
        timeout_s=args.ssh_timeout_sec,
        env=env,
        tunnel_through_iap=bool(args.tunnel_through_iap),
    )
    if not remote:
        tunnel_cmd = _format_tunnel_cmd(
            project=project,
            instance=str(discovery.get("instance_name") or ""),
            zone=str(discovery.get("instance_zone") or ""),
            local_port=args.local_port,
            gateway_port=args.gateway_port,
        )
        payload = _result_json(
            ok=False,
            reason=f"remote_probe_failed:{remote_reason}",
            discovery=discovery,
            vm={},
            gateway={},
            telegram={},
            auth={},
            ui_url=f"http://localhost:{args.local_port}",
            tunnel_cmd=tunnel_cmd,
        )
        if args.json:
            print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        else:
            print(
                "FAIL "
                f"reason={payload['reason']} "
                f"mig={payload['mig']['name']} instance={payload['mig']['instance']} zone={payload['mig']['zone']} "
                f"ui_url={payload['ui']['url']}"
            )
            print(f"FORWARD_CMD={payload['ui']['tunnel_cmd']}")
        return 1

    gateway = remote.get("gateway") if isinstance(remote.get("gateway"), dict) else {}
    telegram = remote.get("telegram") if isinstance(remote.get("telegram"), dict) else {}
    auth = remote.get("auth") if isinstance(remote.get("auth"), dict) else {}
    vm = remote.get("vm") if isinstance(remote.get("vm"), dict) else {}

    gateway_ok = bool(gateway.get("status_ok") is True)
    telegram_ok = bool(telegram.get("alive") is True)
    auth_state = str(auth.get("state") or "unknown")
    auth_ok = auth_state in {"ok", "expiring", "cooldown"}
    instance_status = str(discovery.get("instance_status") or "")
    instance_ok = instance_status.upper() in {"RUNNING", ""}
    ok = bool(gateway_ok and telegram_ok and auth_ok and instance_ok)

    reason = "ok"
    if not gateway_ok:
        reason = "gateway_unhealthy"
    elif not telegram_ok:
        reason = "telegram_not_alive"
    elif not auth_ok:
        reason = f"auth_{auth_state}"
    elif not instance_ok:
        reason = f"instance_status_{instance_status.lower()}"

    tunnel_cmd = _format_tunnel_cmd(
        project=project,
        instance=str(discovery.get("instance_name") or ""),
        zone=str(discovery.get("instance_zone") or ""),
        local_port=args.local_port,
        gateway_port=args.gateway_port,
    )
    payload = _result_json(
        ok=ok,
        reason=reason,
        discovery=discovery,
        vm=vm,
        gateway=gateway,
        telegram=telegram,
        auth=auth,
        ui_url=f"http://localhost:{args.local_port}",
        tunnel_cmd=tunnel_cmd,
    )

    if args.json:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        return 0 if ok else 1

    status = "PASS" if ok else "FAIL"
    print(
        f"{status} reason={reason} "
        f"mig={payload['mig']['name']} instance={payload['mig']['instance']} zone={payload['mig']['zone']} "
        f"gateway_ok={str(gateway_ok).lower()} telegram_alive={str(telegram_ok).lower()} auth_state={auth_state} "
        f"ui_url={payload['ui']['url']}"
    )
    print(f"FORWARD_CMD={payload['ui']['tunnel_cmd']}")
    if vm:
        host = str(vm.get("hostname") or "")
        upt = str(vm.get("uptime") or "")
        iid = str(vm.get("instance_id") or "")
        print(f"VM hostname={host} uptime={upt} instance_id={iid}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
