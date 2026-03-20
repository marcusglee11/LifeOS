# Review Packet — Gate A-P0.6 v1.0

## Summary
- Implemented deterministic, fail-closed OpenClaw backup/restore for operator-critical state with redacted config and policy-guarded memory corpus.
- Backup default path is runtime-only (outside repo), with explicit optional repo export path under ignored evidence tree.
- Restore defaults to dry-run; apply mode restores memory corpus with rollback snapshot and stages config for manual review only.

## Design Decisions
- Transcripts/sessions are excluded by default for privacy minimization and to keep portability scope operator-critical only.
- Redacted config is validated post-write for token-like leakage; any leak blocks backup.
- Manifest verification is mandatory before restore; restore aborts on mismatch.

## Acceptance Evidence
- Evidence directory: `artifacts/evidence/openclaw/p0_6/20260211T124848Z`
- `verify_backup_portability_output.txt`: PASS
- `acceptance_verify_backup_1.txt`, `_2.txt`, `_3.txt`: all PASS with `rc=0`
- `pytest_backup_portability.txt`: 3/3 tests passing

## Changed Files
- `runtime/tools/openclaw_backup_lib.py`
- `runtime/tools/openclaw_backup.sh`
- `runtime/tools/openclaw_restore.sh`
- `runtime/tools/openclaw_verify_backup_portability.sh`
- `runtime/tests/test_openclaw_backup_redaction.py`
- `runtime/tests/test_openclaw_backup_determinism.py`
- `runtime/tests/test_openclaw_restore_manifest_verify.py`

## Appendix A — Flattened Code

### File: runtime/tools/openclaw_backup_lib.py
```python
#!/usr/bin/env python3
from __future__ import annotations

import gzip
import hashlib
import json
import re
import tarfile
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

SECRET_KEY_RE = re.compile(r"(api[_-]?key|token|authorization|password|secret|botToken|signingSecret)", re.I)
SECRET_VALUE_PATTERNS = [
    re.compile(r"Authorization\s*:\s*Bearer\s+\S+", re.I),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{8,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"[A-Za-z0-9+/_=-]{80,}"),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _redact_string(value: str, key: str) -> Tuple[str, int]:
    count = 0
    if SECRET_KEY_RE.search(key):
        return "[REDACTED]", 1

    out = value
    for pattern in SECRET_VALUE_PATTERNS:
        out, n = pattern.subn("[REDACTED]", out)
        count += n
    return out, count


def redact_config_obj(value, key: str = "") -> Tuple[object, int]:
    if isinstance(value, dict):
        redacted: Dict[str, object] = {}
        total = 0
        for k in sorted(value.keys()):
            v, c = redact_config_obj(value[k], k)
            redacted[k] = v
            total += c
        return redacted, total
    if isinstance(value, list):
        out: List[object] = []
        total = 0
        for item in value:
            v, c = redact_config_obj(item, key)
            out.append(v)
            total += c
        return out, total
    if isinstance(value, str):
        return _redact_string(value, key)
    return value, 0


def contains_secret_like_text(text: str) -> bool:
    return any(p.search(text) for p in SECRET_VALUE_PATTERNS)


def create_redacted_config_snapshot(config_path: Path, output_path: Path) -> Dict[str, object]:
    raw = config_path.read_text(encoding="utf-8")
    cfg = json.loads(raw)
    redacted_cfg, redaction_count = redact_config_obj(cfg)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(redacted_cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    written = output_path.read_text(encoding="utf-8")
    if contains_secret_like_text(written):
        raise RuntimeError("redaction leak detected in openclaw_config_redacted.json")

    return {
        "redaction_count": int(redaction_count),
        "bytes": output_path.stat().st_size,
    }


def _memory_relpaths(workspace: Path) -> List[Path]:
    relpaths: List[Path] = []
    memory_md = workspace / "MEMORY.md"
    if memory_md.is_file():
        relpaths.append(Path("MEMORY.md"))
    memory_dir = workspace / "memory"
    if memory_dir.exists():
        for path in sorted(memory_dir.rglob("*")):
            if path.is_file():
                relpaths.append(path.relative_to(workspace))
    return relpaths


def create_deterministic_memory_tar(workspace: Path, output_path: Path) -> List[str]:
    relpaths = _memory_relpaths(workspace)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar:
                for rel in relpaths:
                    src = workspace / rel
                    info = tar.gettarinfo(str(src), arcname=str(rel))
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    with src.open("rb") as f:
                        tar.addfile(info, f)
    return [str(p) for p in relpaths]


def scan_memory_tar_for_secret_patterns(memory_tar_path: Path) -> List[str]:
    findings: List[str] = []
    with tarfile.open(memory_tar_path, mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            data = extracted.read()
            try:
                text = data.decode("utf-8", errors="replace")
            except Exception:
                text = ""
            if contains_secret_like_text(text):
                findings.append(member.name)
    return sorted(findings)


def build_manifest(
    backup_dir: Path,
    created_utc: str,
    host: str,
    openclaw_version: str,
    coo_wrapper_version: str,
    guard_summary: Dict[str, object],
    rel_paths: Iterable[str],
) -> Dict[str, object]:
    files = []
    for rel in sorted(rel_paths):
        path = backup_dir / rel
        files.append(
            {
                "rel_path": rel,
                "sha256": sha256_file(path),
                "bytes": int(path.stat().st_size),
            }
        )
    return {
        "schema_version": "0.6",
        "created_utc": created_utc,
        "host": host,
        "openclaw_version": openclaw_version,
        "coo_wrapper_version": coo_wrapper_version,
        "guard_summary": {
            "ok": bool(guard_summary.get("ok", False)),
            "violations_count": int(guard_summary.get("violations_count", 0)),
        },
        "files": files,
    }


def write_manifest(manifest_path: Path, manifest: Dict[str, object]) -> None:
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n", encoding="utf-8")


def verify_manifest(backup_dir: Path, manifest_path: Path) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(manifest.get("schema_version")) != "0.6":
        errors.append("invalid schema_version")

    for item in manifest.get("files", []):
        rel = str(item.get("rel_path", ""))
        expected_sha = str(item.get("sha256", ""))
        expected_bytes = int(item.get("bytes", -1))
        path = backup_dir / rel
        if not path.exists():
            errors.append(f"missing file: {rel}")
            continue
        actual_sha = sha256_file(path)
        actual_bytes = int(path.stat().st_size)
        if actual_sha != expected_sha:
            errors.append(f"sha mismatch: {rel}")
        if actual_bytes != expected_bytes:
            errors.append(f"bytes mismatch: {rel}")

    return len(errors) == 0, errors
```

### File: runtime/tools/openclaw_backup.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  runtime/tools/openclaw_backup.sh [--export-repo] [--timestamp <UTC_TS>]

Default:
  Writes backup bundle under $OPENCLAW_STATE_DIR/backups/openclaw_backup_<UTC_TS>/

Optional:
  --export-repo  Copy the backup bundle into artifacts/evidence/openclaw/backups/openclaw_backup_<UTC_TS>/
USAGE
}

ROOT="$(git rev-parse --show-toplevel)"
STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
CFG_PATH="${OPENCLAW_CONFIG_PATH:-$STATE_DIR/openclaw.json}"
WORKSPACE="${OPENCLAW_WORKSPACE_DIR:-$STATE_DIR/workspace}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
EXPORT_REPO=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --export-repo)
      EXPORT_REPO=1
      shift
      ;;
    --timestamp)
      TS_UTC="${2:?missing timestamp}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

backup_root="$STATE_DIR/backups"
if ! mkdir -p "$backup_root" 2>/dev/null; then
  backup_root="/tmp/openclaw-runtime/backups"
  mkdir -p "$backup_root"
fi
backup_dir="$backup_root/openclaw_backup_${TS_UTC}"
mkdir -p "$backup_dir"

manifest_path="$backup_dir/MANIFEST.json"
redacted_cfg_path="$backup_dir/openclaw_config_redacted.json"
memory_tar_path="$backup_dir/memory_corpus.tar.gz"
pointers_path="$backup_dir/pointers.txt"
guard_summary_path="$backup_dir/guard_summary.json"

python3 runtime/tools/openclaw_memory_policy_guard.py \
  --workspace "$WORKSPACE" \
  --json-summary \
  --summary-out "$guard_summary_path" > "$backup_dir/guard_output.txt"

python3 - "$guard_summary_path" <<'PY'
import json
import sys
from pathlib import Path
summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if not summary.get("policy_ok", False):
    print("BLOCKED: memory policy guard failed", file=sys.stderr)
    raise SystemExit(1)
PY

openclaw_version="$(openclaw --version 2>/dev/null || echo unknown)"
host_info="$(uname -a | tr -s ' ' | sed -E 's/[[:space:]]+$//')"
coo_wrapper_version="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

python3 - "$CFG_PATH" "$redacted_cfg_path" <<'PY'
import json
import sys
from pathlib import Path
from runtime.tools.openclaw_backup_lib import create_redacted_config_snapshot

cfg = Path(sys.argv[1]).expanduser()
out = Path(sys.argv[2])
if not cfg.exists():
    print(f"BLOCKED: config not found: {cfg}", file=sys.stderr)
    raise SystemExit(1)
create_redacted_config_snapshot(cfg, out)
PY

python3 - "$WORKSPACE" "$memory_tar_path" <<'PY'
import sys
from pathlib import Path
from runtime.tools.openclaw_backup_lib import create_deterministic_memory_tar, scan_memory_tar_for_secret_patterns

workspace = Path(sys.argv[1]).expanduser()
output = Path(sys.argv[2])
if not workspace.exists():
    print(f"BLOCKED: workspace not found: {workspace}", file=sys.stderr)
    raise SystemExit(1)
create_deterministic_memory_tar(workspace, output)
findings = scan_memory_tar_for_secret_patterns(output)
if findings:
    print("BLOCKED: token-like content found in memory_corpus.tar.gz", file=sys.stderr)
    for item in findings:
        print(f"- {item}", file=sys.stderr)
    raise SystemExit(1)
PY

python3 - "$backup_dir" "$manifest_path" "$TS_UTC" "$host_info" "$openclaw_version" "$coo_wrapper_version" "$guard_summary_path" <<'PY'
import json
import sys
from pathlib import Path
from runtime.tools.openclaw_backup_lib import build_manifest, write_manifest, sha256_file

backup_dir = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
created_utc = sys.argv[3]
host = sys.argv[4]
openclaw_version = sys.argv[5]
coo_wrapper_version = sys.argv[6]
guard_summary_path = Path(sys.argv[7])

guard = json.loads(guard_summary_path.read_text(encoding="utf-8"))
manifest = build_manifest(
    backup_dir=backup_dir,
    created_utc=created_utc,
    host=host,
    openclaw_version=openclaw_version,
    coo_wrapper_version=coo_wrapper_version,
    guard_summary={
        "ok": bool(guard.get("policy_ok", False)),
        "violations_count": int(guard.get("violations_count", 0) or 0),
    },
    rel_paths=["openclaw_config_redacted.json", "memory_corpus.tar.gz", "guard_summary.json"],
)
write_manifest(manifest_path, manifest)

sha = sha256_file(manifest_path)
ptr = backup_dir / "pointers.txt"
lines = [
    f"backup_dir={backup_dir}",
    f"manifest={manifest_path}",
    f"manifest_sha256={sha}",
    f"openclaw_config_redacted={backup_dir / 'openclaw_config_redacted.json'}",
    f"memory_corpus_tar={backup_dir / 'memory_corpus.tar.gz'}",
    f"guard_summary={backup_dir / 'guard_summary.json'}",
]
ptr.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

if [ "$EXPORT_REPO" -eq 1 ]; then
  export_dir="$ROOT/artifacts/evidence/openclaw/backups/openclaw_backup_${TS_UTC}"
  mkdir -p "$export_dir"
  cp -a "$backup_dir/." "$export_dir/"
  printf '%s\n' "$backup_dir"
  printf '%s\n' "$manifest_path"
  printf '%s\n' "$pointers_path"
  printf '%s\n' "$export_dir"
  exit 0
fi

printf '%s\n' "$backup_dir"
printf '%s\n' "$manifest_path"
printf '%s\n' "$pointers_path"

```

### File: runtime/tools/openclaw_restore.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  runtime/tools/openclaw_restore.sh --from <backup_dir> [--apply]

Default:
  Dry-run verification only (manifest + integrity + intended actions).

Apply mode:
  Restores memory corpus into ~/.openclaw/workspace after rollback snapshot.
  Stages config snapshot to ~/.openclaw/restore_staging/openclaw_config_redacted.json.
USAGE
}

FROM_DIR=""
APPLY=0
STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
WORKSPACE="${OPENCLAW_WORKSPACE_DIR:-$STATE_DIR/workspace}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --from)
      FROM_DIR="${2:-}"
      shift 2
      ;;
    --apply)
      APPLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$FROM_DIR" ]; then
  echo "ERROR: --from is required" >&2
  exit 2
fi

backup_dir="$(cd "$FROM_DIR" && pwd)"
manifest_path="$backup_dir/MANIFEST.json"
memory_tar="$backup_dir/memory_corpus.tar.gz"
redacted_cfg="$backup_dir/openclaw_config_redacted.json"

if [ ! -f "$manifest_path" ] || [ ! -f "$memory_tar" ] || [ ! -f "$redacted_cfg" ]; then
  echo "BLOCKED: backup bundle incomplete in $backup_dir" >&2
  exit 1
fi

python3 - "$backup_dir" "$manifest_path" <<'PY'
import sys
from pathlib import Path
from runtime.tools.openclaw_backup_lib import verify_manifest

ok, errors = verify_manifest(Path(sys.argv[1]), Path(sys.argv[2]))
if not ok:
    print("BLOCKED: manifest verification failed", file=sys.stderr)
    for err in errors:
        print(f"- {err}", file=sys.stderr)
    raise SystemExit(1)
PY

if [ "$APPLY" -ne 1 ]; then
  echo "RESTORE_DRY_RUN_OK backup_dir=$backup_dir workspace=$WORKSPACE"
  echo "Would restore memory corpus from $memory_tar"
  echo "Would stage config to $STATE_DIR/restore_staging/openclaw_config_redacted.json"
  exit 0
fi

rollback_dir="$STATE_DIR/rollback"
staging_dir="$STATE_DIR/restore_staging"
mkdir -p "$rollback_dir" "$staging_dir" "$WORKSPACE"
rollback_tar="$rollback_dir/workspace_${TS_UTC}.tar.gz"

python3 - "$WORKSPACE" "$rollback_tar" "$memory_tar" <<'PY'
import shutil
import sys
import tarfile
from pathlib import Path
from runtime.tools.openclaw_backup_lib import create_deterministic_memory_tar

workspace = Path(sys.argv[1]).expanduser()
rollback_tar = Path(sys.argv[2]).expanduser()
restore_tar = Path(sys.argv[3]).expanduser()
tmp_restore = workspace.parent / f".restore_tmp_{workspace.name}"

# Snapshot current workspace memory subset for rollback.
create_deterministic_memory_tar(workspace, rollback_tar)

if tmp_restore.exists():
    shutil.rmtree(tmp_restore)
tmp_restore.mkdir(parents=True, exist_ok=True)

try:
    with tarfile.open(restore_tar, mode="r:gz") as tar:
        tar.extractall(tmp_restore)

    memory_dir = workspace / "memory"
    memory_md = workspace / "MEMORY.md"
    if memory_dir.exists():
        shutil.rmtree(memory_dir)
    if memory_md.exists():
        memory_md.unlink()

    restored_memory_dir = tmp_restore / "memory"
    restored_memory_md = tmp_restore / "MEMORY.md"
    if restored_memory_dir.exists():
        shutil.copytree(restored_memory_dir, memory_dir)
    if restored_memory_md.exists():
        memory_md.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(restored_memory_md, memory_md)
except Exception:
    # Roll back from snapshot on any restore failure.
    if memory_dir.exists():
        shutil.rmtree(memory_dir)
    if memory_md.exists():
        memory_md.unlink()
    with tarfile.open(rollback_tar, mode="r:gz") as tar:
        tar.extractall(workspace)
    raise
finally:
    if tmp_restore.exists():
        shutil.rmtree(tmp_restore)
PY

cp "$redacted_cfg" "$staging_dir/openclaw_config_redacted.json"

echo "RESTORE_APPLY_OK backup_dir=$backup_dir"
echo "rollback_snapshot=$rollback_tar"
echo "memory_restored_to=$WORKSPACE"
echo "config_staged=$staging_dir/openclaw_config_redacted.json"
echo "Manual action required: review staged redacted config and apply manually if desired."

```

### File: runtime/tools/openclaw_verify_backup_portability.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_VERIFY_BACKUP_OUT_DIR:-${OPENCLAW_STATE_DIR:-$HOME/.openclaw}/verify-backup/$TS_UTC}"
CMD_TIMEOUT_SEC="${OPENCLAW_VERIFY_BACKUP_TIMEOUT_SEC:-25}"
mkdir -p "$OUT_DIR" 2>/dev/null || { OUT_DIR="/tmp/openclaw-verify-backup/$TS_UTC"; mkdir -p "$OUT_DIR"; }

status_before="$OUT_DIR/git_status_before.txt"
status_after="$OUT_DIR/git_status_after.txt"
backup_out="$OUT_DIR/backup_output.txt"
restore_out="$OUT_DIR/restore_dry_run.txt"
manifest_verify_out="$OUT_DIR/manifest_verify.txt"

git -C "$ROOT" status --porcelain=v1 > "$status_before"

set +e
timeout "$CMD_TIMEOUT_SEC" runtime/tools/openclaw_backup.sh > "$backup_out" 2>&1
rc_backup=$?
set -e
if [ "$rc_backup" -ne 0 ]; then
  echo "FAIL backup_portability=false stage=backup rc=$rc_backup out=$backup_out" >&2
  exit 1
fi

backup_dir="$(sed -n '1p' "$backup_out" | tr -d '\r')"
manifest_path="$(sed -n '2p' "$backup_out" | tr -d '\r')"

python3 - "$backup_dir" "$manifest_path" > "$manifest_verify_out" <<'PY'
import sys
from pathlib import Path
from runtime.tools.openclaw_backup_lib import verify_manifest

ok, errors = verify_manifest(Path(sys.argv[1]), Path(sys.argv[2]))
if not ok:
    print("manifest_verify=false")
    for err in errors:
        print(err)
    raise SystemExit(1)
print("manifest_verify=true")
PY

set +e
timeout "$CMD_TIMEOUT_SEC" runtime/tools/openclaw_restore.sh --from "$backup_dir" > "$restore_out" 2>&1
rc_restore=$?
set -e
if [ "$rc_restore" -ne 0 ]; then
  echo "FAIL backup_portability=false stage=restore_dry_run rc=$rc_restore out=$restore_out" >&2
  exit 1
fi

git -C "$ROOT" status --porcelain=v1 > "$status_after"
if ! cmp -s "$status_before" "$status_after"; then
  echo "FAIL backup_portability=false stage=git_cleanliness before=$status_before after=$status_after" >&2
  exit 1
fi

echo "PASS backup_portability=true backup_dir=$backup_dir manifest=$manifest_path restore_dry_run=$restore_out"

```

### File: runtime/tests/test_openclaw_backup_redaction.py
```python
import json
from pathlib import Path

from runtime.tools.openclaw_backup_lib import contains_secret_like_text, create_redacted_config_snapshot


def test_redaction_scrubs_known_secret_fields(tmp_path: Path):
    cfg = {
        "channels": {"telegram": {"botToken": "123:abcdef"}},
        "gateway": {"Authorization": "Bearer token-abc"},
        "apiKey": "sk-abcdefghijklmnopqrstuvwxyz",
    }
    cfg_path = tmp_path / "openclaw.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    out = tmp_path / "openclaw_config_redacted.json"

    stats = create_redacted_config_snapshot(cfg_path, out)
    assert stats["redaction_count"] >= 2

    text = out.read_text(encoding="utf-8")
    assert "123:abcdef" not in text
    assert "token-abc" not in text
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in text
    assert "[REDACTED]" in text
    assert contains_secret_like_text(text) is False

```

### File: runtime/tests/test_openclaw_backup_determinism.py
```python
from pathlib import Path

from runtime.tools.openclaw_backup_lib import create_deterministic_memory_tar, sha256_file


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_memory_tar_is_deterministic(tmp_path: Path):
    workspace = tmp_path / "workspace"
    _write(workspace / "MEMORY.md", "# Memory\n")
    _write(
        workspace / "memory" / "daily" / "2026-02-11.md",
        "---\nclassification: INTERNAL\nretention: 180d\n---\nseed\n",
    )

    tar1 = tmp_path / "a.tar.gz"
    tar2 = tmp_path / "b.tar.gz"
    create_deterministic_memory_tar(workspace, tar1)
    create_deterministic_memory_tar(workspace, tar2)

    assert sha256_file(tar1) == sha256_file(tar2)

```

### File: runtime/tests/test_openclaw_restore_manifest_verify.py
```python
from pathlib import Path

from runtime.tools.openclaw_backup_lib import build_manifest, verify_manifest, write_manifest


def test_restore_dry_run_manifest_check_detects_mismatch(tmp_path: Path):
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    f = backup_dir / "openclaw_config_redacted.json"
    f.write_text('{"ok":"true"}\n', encoding="utf-8")

    manifest = build_manifest(
        backup_dir=backup_dir,
        created_utc="20260211T000000Z",
        host="linux",
        openclaw_version="x",
        coo_wrapper_version="y",
        guard_summary={"ok": True, "violations_count": 0},
        rel_paths=["openclaw_config_redacted.json"],
    )
    manifest_path = backup_dir / "MANIFEST.json"
    write_manifest(manifest_path, manifest)

    # Tamper after manifest creation.
    f.write_text('{"ok":"tampered"}\n', encoding="utf-8")
    ok, errors = verify_manifest(backup_dir, manifest_path)
    assert ok is False
    assert any("sha mismatch" in e for e in errors)
```
