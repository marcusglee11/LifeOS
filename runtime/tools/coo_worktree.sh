#!/usr/bin/env bash
set -euo pipefail

BUILD_REPO="$(git rev-parse --show-toplevel)"
TRAIN_WT="$(dirname "$BUILD_REPO")/LifeOS__wt_coo_training"
TRAIN_BRANCH="coo/training"
OPENCLAW_PROFILE="lifeos-coo-training"

print_header() {
  echo "BUILD_REPO=$BUILD_REPO"
  echo "TRAIN_WT=$TRAIN_WT"
  echo "TRAIN_BRANCH=$TRAIN_BRANCH"
  echo "OPENCLAW_PROFILE=$OPENCLAW_PROFILE"
}

ensure_worktree() {
  if [ ! -d "$TRAIN_WT" ]; then
    git -C "$BUILD_REPO" worktree add -B "$TRAIN_BRANCH" "$TRAIN_WT" HEAD
  fi

  local wt_top
  wt_top="$(git -C "$TRAIN_WT" rev-parse --show-toplevel 2>/dev/null || true)"
  if [ -z "$wt_top" ] || [ "$wt_top" != "$TRAIN_WT" ]; then
    echo "ERROR: $TRAIN_WT is not a valid git worktree top-level." >&2
    exit 2
  fi
}

enter_training_dir() {
  ensure_worktree
  # Guardrail: never run tooling inside the main build workspace.
  if [[ "$PWD" == "$BUILD_REPO"* ]] && [[ "$PWD" != "$TRAIN_WT"* ]]; then
    cd "$TRAIN_WT"
    return
  fi
  cd "$TRAIN_WT"
}

build_repo_clean() {
  local s d
  s="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
  d="$(git -C "$BUILD_REPO" diff --name-only || true)"
  if [ -n "$s" ] || [ -n "$d" ]; then
    return 1
  fi
  return 0
}

job_evidence_dir() {
  local ts
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  printf '%s\n' "$BUILD_REPO/artifacts/evidence/openclaw/jobs/$ts"
}

write_clean_marker() {
  local out_file="$1"
  local porcelain diffnames
  porcelain="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
  diffnames="$(git -C "$BUILD_REPO" diff --name-only || true)"
  if [ -z "$porcelain" ] && [ -z "$diffnames" ]; then
    printf '(empty)\n' >"$out_file"
    return
  fi
  {
    [ -n "$porcelain" ] && printf '%s\n' "$porcelain"
    [ -n "$diffnames" ] && printf '%s\n' "$diffnames"
  } >"$out_file"
}

print_clean_block() {
  local label="$1" status_text="$2" diff_text="$3"
  echo "${label}_STATUS_BEGIN"
  if [ -n "$status_text" ]; then
    printf '%s\n' "$status_text"
  else
    echo "(empty)"
  fi
  echo "${label}_STATUS_END"
  echo "${label}_DIFF_BEGIN"
  if [ -n "$diff_text" ]; then
    printf '%s\n' "$diff_text"
  else
    echo "(empty)"
  fi
  echo "${label}_DIFF_END"
}

safe_redact_file_head() {
  local file="$1"
  local lines="${2:-20}"
  if [ -f "$file" ]; then
    sed -n "1,${lines}p" "$file" | sed -E 's/[A-Za-z0-9_-]{24,}/[REDACTED]/g'
  fi
}

write_hashes() {
  local evid_dir="$1"
  (
    cd "$evid_dir"
    find . -maxdepth 1 -type f -printf '%P\n' | LC_ALL=C sort | while IFS= read -r f; do
      [ -n "$f" ] && sha256sum "$f"
    done
  ) > "$evid_dir/hashes.sha256"
}

render_capsule_marker() {
  local capsule_file="$1"
  local err_file="$2"
  python3 "$BUILD_REPO/runtime/tools/coo_capsule_render.py" \
    --capsule "$capsule_file" \
    --key HEAD \
    --key EVID \
    --key RESULT_PRETTY_ERR_BYTES \
    --key RC \
    --key DURATION_S \
    --key PYTEST_SUMMARY \
    2>"$err_file"
}

usage() {
  cat <<'EOF'
Usage:
  runtime/tools/coo_worktree.sh ensure
  runtime/tools/coo_worktree.sh path
  runtime/tools/coo_worktree.sh cd
  runtime/tools/coo_worktree.sh shell
  runtime/tools/coo_worktree.sh brief
  runtime/tools/coo_worktree.sh job e2e
  runtime/tools/coo_worktree.sh run-job <job.json>
  runtime/tools/coo_worktree.sh e2e
  runtime/tools/coo_worktree.sh tui -- <tui-args...>
  runtime/tools/coo_worktree.sh run -- <command...>
  runtime/tools/coo_worktree.sh openclaw -- <openclaw-args...>
EOF
}

cmd="${1:-}"
case "$cmd" in
  -h|--help|help)
    usage
    ;;
  ensure)
    ensure_worktree
    print_header
    ;;
  path)
    echo "$TRAIN_WT"
    ;;
  cd)
    ensure_worktree
    echo "$TRAIN_WT"
    ;;
  shell)
    enter_training_dir
    print_header
    echo "PWD=$PWD"
    exec "${SHELL:-/bin/bash}"
    ;;
  brief)
    enter_training_dir
    prompt="$(cat <<'EOF'
Read docs/11_admin/LIFEOS_STATE.md and docs/11_admin/BACKLOG.md from the repo.
Return exactly these headings:
TOP_3_ACTIONS:
- ...
- ...
- ...
TOP_BLOCKERS:
- ...
- ...
CEO_QUESTION:
- ...
Do not propose edits or patches.
EOF
)"

    raw_json="$(mktemp)"
    raw_err="$(mktemp)"
    cleanup() {
      rm -f "$raw_json" "$raw_err"
    }
    trap cleanup EXIT

    if ! openclaw --profile "$OPENCLAW_PROFILE" agent --local --agent main --message "$prompt" --json >"$raw_json" 2>"$raw_err"; then
      echo "ERROR: coo brief failed to run local agent turn." >&2
      sed -n '1,20p' "$raw_err" | sed -E 's/[A-Za-z0-9_-]{24,}/[REDACTED]/g' >&2
      exit 1
    fi

    text="$(python3 - "$raw_json" <<'PY'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
try:
    data = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
payloads = data.get("payloads") or []
parts = []
for item in payloads:
    t = item.get("text")
    if isinstance(t, str) and t.strip():
        parts.append(t.strip())
print("\n\n".join(parts))
PY
)"

    if [ -z "$text" ]; then
      echo "ERROR: coo brief returned no assistant text." >&2
      exit 1
    fi

    if printf '%s\n' "$text" | rg -q '^TOP_3_ACTIONS:' && \
      printf '%s\n' "$text" | rg -q '^TOP_BLOCKERS:' && \
      printf '%s\n' "$text" | rg -q '^CEO_QUESTION:'; then
      printf '%s\n' "$text"
    else
      echo "TOP_3_ACTIONS:"
      echo "- unavailable"
      echo "- unavailable"
      echo "- unavailable"
      echo "TOP_BLOCKERS:"
      echo "- unavailable"
      echo "- unavailable"
      echo "CEO_QUESTION:"
      echo "- unavailable"
      echo
      printf '%s\n' "$text"
    fi
    ;;
  job)
    shift || true
    sub="${1:-}"
    if [ "$sub" != "e2e" ]; then
      usage
      exit 2
    fi

    enter_training_dir
    evid_dir="$(job_evidence_dir)"
    mkdir -p "$evid_dir"
    git -C "$BUILD_REPO" check-ignore -v "$evid_dir" > "$evid_dir/git_check_ignore.txt" 2>&1 || true
    raw_json="$evid_dir/agent_raw.json"
    raw_err="$evid_dir/agent_raw.stderr"
    job_json="$evid_dir/job.json"
    blocked_reason="$evid_dir/blocked_reason.txt"

    prompt="$(cat <<'EOF'
You are preparing a LifeOS test execution job.
Choose ONE representative E2E-style pytest command for this repository.
Discovered candidates include:
- pytest -q tests_recursive/test_e2e_smoke_timeout.py
- pytest -q -k e2e
- pytest -q runtime/tests/orchestration/missions/test_autonomous_loop.py

Return STRICT JSON ONLY (no markdown, no prose), matching exactly:
{
  "kind": "lifeos.job.v0.1",
  "job_type": "e2e_test",
  "objective": "Run a representative E2E test in the LifeOS repo",
  "scope": ["run tests only", "no code edits"],
  "non_goals": ["no installs", "no network", "no git operations"],
  "workdir": ".",
  "command": ["pytest", "-q", "..."],
  "timeout_s": 1800,
  "expected_artifacts": ["stdout.txt","stderr.txt","rc.txt","duration_s.txt"],
  "clean_repo_required": true
}

Rules:
- command must be read-only.
- Do not include git/rm/sudo/curl/wget/pip/npm/brew/apt/sh/bash/powershell.
- output must be a single JSON object.
EOF
)"

    if ! openclaw --profile "$OPENCLAW_PROFILE" agent --local --agent main --message "$prompt" --json >"$raw_json" 2>"$raw_err"; then
      echo "ERROR: coo job e2e failed to generate job request." >&2
      sed -n '1,20p' "$raw_err" | sed -E 's/[A-Za-z0-9_-]{24,}/[REDACTED]/g' >&2
      exit 1
    fi

    if ! python3 - "$raw_json" "$job_json" <<'PY'
import json
import re
import sys
from pathlib import Path

raw_path = Path(sys.argv[1])
job_path = Path(sys.argv[2])
raw = json.loads(raw_path.read_text(encoding="utf-8"))
payloads = raw.get("payloads") or []
texts = []
for item in payloads:
    if isinstance(item, dict):
        text = item.get("text")
        if isinstance(text, str):
            texts.append(text.strip())

def parse_obj(text: str):
    text = text.strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None

obj = None
for t in texts:
    obj = parse_obj(t)
    if obj and obj.get("kind") == "lifeos.job.v0.1":
        break

if not obj or obj.get("kind") != "lifeos.job.v0.1":
    raise SystemExit(1)

job_path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
PY
    then
      strict_prompt="$(cat <<'EOF'
Output ONLY this JSON object type, no markdown:
{
  "kind": "lifeos.job.v0.1",
  "job_type": "e2e_test",
  "objective": "Run a representative E2E test in the LifeOS repo",
  "scope": ["run tests only", "no code edits"],
  "non_goals": ["no installs", "no network", "no git operations"],
  "workdir": ".",
  "command": ["pytest", "-q", "tests_recursive/test_e2e_smoke_timeout.py"],
  "timeout_s": 1800,
  "expected_artifacts": ["stdout.txt","stderr.txt","rc.txt","duration_s.txt"],
  "clean_repo_required": true
}
EOF
)"
      if ! openclaw --profile "$OPENCLAW_PROFILE" agent --local --agent main --message "$strict_prompt" --json >"$raw_json" 2>"$raw_err"; then
        echo "ERROR: coo job e2e retry failed." >&2
        sed -n '1,20p' "$raw_err" | sed -E 's/[A-Za-z0-9_-]{24,}/[REDACTED]/g' >&2
        exit 1
      fi
      python3 - "$raw_json" "$job_json" <<'PY'
import json
import re
import sys
from pathlib import Path

raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
job_path = Path(sys.argv[2])
payloads = raw.get("payloads") or []
text = ""
for item in payloads:
    if isinstance(item, dict) and isinstance(item.get("text"), str):
        text = item["text"].strip()
        if text:
            break
match = re.search(r"\{.*\}", text, flags=re.S)
if not match:
    raise SystemExit(1)
obj = json.loads(match.group(0))
if obj.get("kind") != "lifeos.job.v0.1":
    raise SystemExit(1)
job_path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
PY
    fi

    if ! python3 - "$job_json" "$blocked_reason" <<'PY'
import json
import os
import sys
from pathlib import Path

job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
blocked = Path(sys.argv[2])
required = {
    "kind": str,
    "job_type": str,
    "objective": str,
    "scope": list,
    "non_goals": list,
    "workdir": str,
    "command": list,
    "timeout_s": int,
    "expected_artifacts": list,
    "clean_repo_required": bool,
}
for k, t in required.items():
    if k not in job:
        blocked.write_text(f"missing required field: {k}\n", encoding="utf-8")
        raise SystemExit(1)
    if not isinstance(job[k], t):
        blocked.write_text(f"invalid type for field: {k}\n", encoding="utf-8")
        raise SystemExit(1)

cmd = job["command"]
if not cmd or not all(isinstance(x, str) for x in cmd):
    blocked.write_text("invalid command array\n", encoding="utf-8")
    raise SystemExit(1)

cmd0 = os.path.basename(cmd[0])
if cmd0 not in {"pytest", "python", "python3"}:
    blocked.write_text(f"command not allowlisted: {cmd0}\n", encoding="utf-8")
    raise SystemExit(1)

deny = ["git", "rm", "sudo", "curl", "wget", "pip", "npm", "brew", "apt", "sh", "bash", "powershell"]
for token in cmd:
    low = token.lower()
    if any(d in low for d in deny):
        blocked.write_text(f"denylisted token found: {token}\n", encoding="utf-8")
        raise SystemExit(1)

timeout_s = job["timeout_s"]
if timeout_s > 3600:
    blocked.write_text("timeout_s too large\n", encoding="utf-8")
    raise SystemExit(1)
PY
    then
      echo "ERROR: generated job.json failed validation." >&2
      safe_redact_file_head "$blocked_reason" 20 >&2
      exit 1
    fi

    if ! python3 -m json.tool "$job_json" > "$evid_dir/job.pretty.json" 2>"$evid_dir/job.pretty.err"; then
      printf 'invalid JSON in job.json\n' > "$blocked_reason"
      echo "ERROR: job.json is not strict JSON." >&2
      safe_redact_file_head "$evid_dir/job.pretty.err" 20 >&2
      exit 1
    fi
    if [ -s "$evid_dir/job.pretty.err" ]; then
      {
        echo "BLOCKED: job.pretty.err non-empty"
        safe_redact_file_head "$evid_dir/job.pretty.err" 40
      } > "$blocked_reason"
      echo "ERROR: job.pretty.err non-empty." >&2
      exit 22
    fi
    if [ ! -s "$evid_dir/job.pretty.json" ] || [ "$(wc -c <"$evid_dir/job.pretty.json" | tr -d ' ')" -lt 50 ]; then
      printf 'BLOCKED: job.pretty.json missing or too small\n' > "$blocked_reason"
      echo "ERROR: job.pretty.json missing or too small." >&2
      exit 22
    fi

    write_hashes "$evid_dir"
    echo "JOB_EVID_DIR=$evid_dir"
    echo "JOB_JSON_PATH=$job_json"
    ;;
  run-job)
    shift || true
    if [ "$#" -ne 1 ]; then
      usage
      exit 2
    fi
    job_path="$1"
    if [ ! -f "$job_path" ]; then
      echo "ERROR: job file not found: $job_path" >&2
      exit 2
    fi

    job_dir="$(cd "$(dirname "$job_path")" && pwd)"
    blocked_reason="$job_dir/blocked_reason.txt"

    if ! build_repo_clean; then
      echo "ERROR: BUILD_REPO not clean before run-job." >&2
      mkdir -p "$job_dir"
      write_clean_marker "$job_dir/clean_pre.txt"
      printf 'BUILD_REPO not clean before run-job\n' > "$blocked_reason"
      git -C "$BUILD_REPO" status --porcelain=v1 || true
      git -C "$BUILD_REPO" diff --name-only || true
      exit 10
    fi

    meta_file="$(mktemp)"
    cleanup_meta() {
      rm -f "$meta_file"
    }
    trap cleanup_meta EXIT

    if ! python3 - "$job_path" "$meta_file" <<'PY'
import json
import os
import sys
from pathlib import Path

job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
meta_path = Path(sys.argv[2])

if job.get("kind") != "lifeos.job.v0.1":
    raise SystemExit("invalid kind")
cmd = job.get("command")
if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) for x in cmd):
    raise SystemExit("invalid command")

cmd0 = os.path.basename(cmd[0])
if cmd0 not in {"pytest", "python", "python3"}:
    raise SystemExit("command not in allowlist")

banned = ["git", "rm", "sudo", "curl", "wget", "pip", "npm", "brew", "apt", "sh", "bash", "powershell"]
for token in cmd:
    low = token.lower()
    if any(b in low for b in banned):
        raise SystemExit(f"banned token in command: {token}")

timeout_s = job.get("timeout_s")
if not isinstance(timeout_s, int) or timeout_s <= 0 or timeout_s > 3600:
    raise SystemExit("invalid timeout_s")

workdir = job.get("workdir", ".")
if not isinstance(workdir, str) or not workdir:
    raise SystemExit("invalid workdir")

meta = {
    "timeout_s": timeout_s,
    "workdir": workdir,
    "command": cmd,
}
meta_path.write_text(json.dumps(meta), encoding="utf-8")
PY
    then
      printf 'job validation failed for run-job\n' > "$blocked_reason"
      exit 3
    fi

    timeout_s="$(python3 - "$meta_file" <<'PY'
import json
import sys
print(json.loads(open(sys.argv[1], encoding="utf-8").read())["timeout_s"])
PY
)"
    job_workdir="$(python3 - "$meta_file" <<'PY'
import json
import sys
print(json.loads(open(sys.argv[1], encoding="utf-8").read())["workdir"])
PY
)"
    mapfile -d '' job_cmd < <(python3 - "$meta_file" <<'PY'
import json
import sys
cmd = json.loads(open(sys.argv[1], encoding="utf-8").read())["command"]
for part in cmd:
    sys.stdout.write(part)
    sys.stdout.write("\0")
PY
)

    enter_training_dir
    evid_dir="$(cd "$(dirname "$job_path")" && pwd)"
    mkdir -p "$evid_dir"
    stdout_file="$evid_dir/stdout.txt"
    stderr_file="$evid_dir/stderr.txt"
    rc_file="$evid_dir/rc.txt"
    dur_file="$evid_dir/duration_s.txt"
    result_file="$evid_dir/result.json"
    blocked_reason="$evid_dir/blocked_reason.txt"
    clean_pre_file="$evid_dir/clean_pre.txt"
    clean_post_file="$evid_dir/clean_post.txt"
    echo "EVID=$evid_dir"
    write_clean_marker "$clean_pre_file"

    start_s="$(date +%s)"
    set +e
    (
      cd "$TRAIN_WT/$job_workdir"
      timeout "$timeout_s" "${job_cmd[@]}"
    ) >"$stdout_file" 2>"$stderr_file"
    rc="$?"
    set -e
    end_s="$(date +%s)"
    duration_s="$((end_s - start_s))"

    printf '%s\n' "$rc" >"$rc_file"
    printf '%s\n' "$duration_s" >"$dur_file"

    clean_post=true
    if ! build_repo_clean; then
      clean_post=false
    fi
    write_clean_marker "$clean_post_file"

    python3 - "$job_path" "$result_file" "$rc" "$duration_s" "$evid_dir" "$clean_post" "$meta_file" <<'PY'
import json
import sys
from pathlib import Path

job_path, result_path, rc, duration_s, evid_dir, clean_post, meta_path = sys.argv[1:]
meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
result = {
    "kind": "lifeos.result.v0.1",
    "job_path": str(Path(job_path).resolve()),
    "command": meta["command"],
    "rc": int(rc),
    "duration_s": int(duration_s),
    "evid_dir": str(Path(evid_dir).resolve()),
    "clean_pre": True,
    "clean_post": clean_post.lower() == "true",
}
Path(result_path).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
PY

    if ! python3 -m json.tool "$result_file" > "$evid_dir/result.pretty.json" 2>"$evid_dir/result.pretty.err"; then
      printf 'invalid JSON in result.json\n' > "$blocked_reason"
      echo "ERROR: result.json failed strict JSON validation." >&2
      safe_redact_file_head "$evid_dir/result.pretty.err" 20 >&2
      exit 12
    fi
    if [ -s "$evid_dir/result.pretty.err" ]; then
      {
        echo "BLOCKED: result.pretty.err non-empty"
        safe_redact_file_head "$evid_dir/result.pretty.err" 40
      } > "$blocked_reason"
      echo "ERROR: result.pretty.err non-empty." >&2
      exit 23
    fi
    if [ ! -s "$evid_dir/result.pretty.json" ] || [ "$(wc -c <"$evid_dir/result.pretty.json" | tr -d ' ')" -lt 50 ]; then
      printf 'BLOCKED: result.pretty.json missing or too small\n' > "$blocked_reason"
      echo "ERROR: result.pretty.json missing or too small." >&2
      exit 23
    fi

    if [ "$clean_post" != "true" ]; then
      printf 'BUILD_REPO dirtied by run-job\n' > "$blocked_reason"
      echo "ERROR: BUILD_REPO dirtied by run-job." >&2
      git -C "$BUILD_REPO" status --porcelain=v1 || true
      git -C "$BUILD_REPO" diff --name-only || true
      exit 11
    fi

    write_hashes "$evid_dir"
    echo "RESULT_JSON_PATH=$result_file"
    echo "EVID_DIR=$evid_dir"
    echo "RC=$rc"
    echo "DURATION_S=$duration_s"
    ;;
  e2e)
    enter_training_dir
    e2e_tmp="$(mktemp)"
    e2e_tmp_run="$e2e_tmp.run"
    capsule_tmp="$(mktemp)"
    capsule_file=""
    capsule_missing="$(mktemp)"
    rc_e2e=0
    job_path=""
    result_path=""
    evid_dir=""
    rc_val=""
    dur_val=""
    summary_line=""
    job_err_size="0"
    result_err_size="0"
    cleanup_e2e() {
      rm -f "$e2e_tmp" "$e2e_tmp_run" "$capsule_tmp" "$capsule_missing"
    }
    trap cleanup_e2e EXIT
    append_capsule_line() {
      local line="$1"
      printf '%s\n' "$line" >> "$capsule_tmp"
    }

    emit_clean_block() {
      local label="$1" status_text="$2" diff_text="$3" line
      while IFS= read -r line; do
        append_capsule_line "$line"
      done < <(print_clean_block "$label" "$status_text" "$diff_text")
    }

    pre_status="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
    pre_diff="$(git -C "$BUILD_REPO" diff --name-only || true)"
    emit_clean_block PRE "$pre_status" "$pre_diff"

    set +e
    (
      cd "$BUILD_REPO"
      "$0" job e2e
    ) >"$e2e_tmp"
    rc_e2e=$?
    set -e
    if [ "$rc_e2e" -ne 0 ]; then
      echo "ERROR: coo e2e failed during job generation." >&2
      cat "$e2e_tmp" >&2
      exit "$rc_e2e"
    fi

    mid_status="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
    mid_diff="$(git -C "$BUILD_REPO" diff --name-only || true)"
    emit_clean_block MID "$mid_status" "$mid_diff"

    job_path="$(rg '^JOB_JSON_PATH=' "$e2e_tmp" | sed 's/^JOB_JSON_PATH=//')"
    if [ -z "$job_path" ] || [ ! -f "$job_path" ]; then
      echo "ERROR: coo e2e could not resolve job path." >&2
      exit 1
    fi

    set +e
    (
      cd "$BUILD_REPO"
      "$0" run-job "$job_path"
    ) | tee "$e2e_tmp_run"
    rc_e2e=$?
    set -e
    result_path="$(rg '^RESULT_JSON_PATH=' "$e2e_tmp_run" | sed 's/^RESULT_JSON_PATH=//')"
    evid_dir="$(rg '^EVID_DIR=' "$e2e_tmp_run" | sed 's/^EVID_DIR=//')"
    rc_val="$(rg '^RC=' "$e2e_tmp_run" | sed 's/^RC=//')"
    dur_val="$(rg '^DURATION_S=' "$e2e_tmp_run" | sed 's/^DURATION_S=//')"
    if [ -n "$evid_dir" ] && [ -f "$evid_dir/stdout.txt" ]; then
      summary_line="$(grep -E 'passed,.*deselected' "$evid_dir/stdout.txt" | tail -n 1 || true)"
    fi
    if [ -n "$evid_dir" ] && [ -f "$evid_dir/job.pretty.err" ]; then
      job_err_size="$(wc -c <"$evid_dir/job.pretty.err" | tr -d ' ')"
    fi
    if [ -n "$evid_dir" ] && [ -f "$evid_dir/result.pretty.err" ]; then
      result_err_size="$(wc -c <"$evid_dir/result.pretty.err" | tr -d ' ')"
    fi

    post_status="$(git -C "$BUILD_REPO" status --porcelain=v1 || true)"
    post_diff="$(git -C "$BUILD_REPO" diff --name-only || true)"
    emit_clean_block POST "$post_status" "$post_diff"

    append_capsule_line "COO_E2E_MINI_CAPSULE_BEGIN"
    append_capsule_line "HEAD=$(git -C "$BUILD_REPO" rev-parse --short HEAD)"
    append_capsule_line "EVID=${evid_dir:-unknown}"
    append_capsule_line "JOB_PRETTY_ERR_BYTES=$job_err_size"
    append_capsule_line "RESULT_PRETTY_ERR_BYTES=$result_err_size"
    append_capsule_line "RC=${rc_val:-unknown}"
    append_capsule_line "DURATION_S=${dur_val:-unknown}"
    if [ -n "$summary_line" ]; then
      append_capsule_line "PYTEST_SUMMARY=$summary_line"
    else
      append_capsule_line "PYTEST_SUMMARY=(summary not found)"
    fi
    append_capsule_line "EVID_FILES_BEGIN"
    if [ -n "$evid_dir" ] && [ -d "$evid_dir" ]; then
      while IFS= read -r evid_file; do
        append_capsule_line "$evid_file"
      done < <(find "$evid_dir" -maxdepth 1 -type f -printf '%f\n' | sort)
    fi
    append_capsule_line "EVID_FILES_END"
    append_capsule_line "COO_E2E_MINI_CAPSULE_END"

    if [ -z "$evid_dir" ] || [ ! -d "$evid_dir" ]; then
      echo "INTERNAL_ERROR: CAPSULE_FORMAT" >&2
      echo "EVID_DIR_MISSING" >&2
      exit 24
    fi
    capsule_file="$evid_dir/capsule.txt"
    cp "$capsule_tmp" "$capsule_file"

    missing_evidence=""
    for required_file in clean_pre.txt clean_post.txt git_check_ignore.txt hashes.sha256 stdout.txt stderr.txt; do
      if [ ! -f "$evid_dir/$required_file" ]; then
        missing_evidence="${missing_evidence}${required_file}"$'\n'
      fi
    done
    if [ -n "$missing_evidence" ]; then
      echo "INTERNAL_ERROR: EVIDENCE_INCOMPLETE" >&2
      printf '%s' "$missing_evidence" | sed '/^$/d' >&2
      exit 25
    fi

    if ! python3 - "$capsule_file" "$capsule_missing" <<'PY'
import sys
from pathlib import Path

lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
missing_out = Path(sys.argv[2])

def count_exact(s):
    return sum(1 for l in lines if l == s)

def count_prefix(p):
    return sum(1 for l in lines if l.startswith(p))

required_exact = [
    "PRE_STATUS_BEGIN", "PRE_STATUS_END", "PRE_DIFF_BEGIN", "PRE_DIFF_END",
    "MID_STATUS_BEGIN", "MID_STATUS_END", "MID_DIFF_BEGIN", "MID_DIFF_END",
    "POST_STATUS_BEGIN", "POST_STATUS_END", "POST_DIFF_BEGIN", "POST_DIFF_END",
    "COO_E2E_MINI_CAPSULE_BEGIN", "EVID_FILES_BEGIN", "EVID_FILES_END",
    "COO_E2E_MINI_CAPSULE_END",
]
required_prefix = [
    "HEAD=", "EVID=", "JOB_PRETTY_ERR_BYTES=", "RESULT_PRETTY_ERR_BYTES=",
    "RC=", "PYTEST_SUMMARY=",
]

missing = []
for token in required_exact:
    if count_exact(token) != 1:
        missing.append(token)
for token in required_prefix:
    if count_prefix(token) != 1:
        missing.append(token)

# Explicit hard requirements requested for capsule format conformance.
if count_exact("EVID_FILES_BEGIN") != 1:
    missing.append("EVID_FILES_BEGIN")
if count_exact("EVID_FILES_END") != 1:
    missing.append("EVID_FILES_END")
if count_prefix("RESULT_PRETTY_ERR_BYTES=") != 1:
    missing.append("RESULT_PRETTY_ERR_BYTES=")

result_err_lines = [l for l in lines if l.startswith("RESULT_PRETTY_ERR_BYTES=")]
if len(result_err_lines) == 1:
    value = result_err_lines[0].split("=", 1)[1].strip()
    if not value.isdigit():
        missing.append("RESULT_PRETTY_ERR_BYTES_NOT_INT")
    elif int(value) < 0:
        missing.append("RESULT_PRETTY_ERR_BYTES_NEGATIVE")

job_err_lines = [l for l in lines if l.startswith("JOB_PRETTY_ERR_BYTES=")]
if len(job_err_lines) == 1:
    value = job_err_lines[0].split("=", 1)[1].strip()
    if not value.isdigit():
        missing.append("JOB_PRETTY_ERR_BYTES_NOT_INT")
    elif int(value) < 0:
        missing.append("JOB_PRETTY_ERR_BYTES_NEGATIVE")

rc_lines = [l for l in lines if l.startswith("RC=")]
if len(rc_lines) == 1:
    value = rc_lines[0].split("=", 1)[1].strip()
    if not value.isdigit():
        missing.append("RC_NOT_INT")
    elif int(value) < 0:
        missing.append("RC_NEGATIVE")

order_tokens = [
    "PRE_STATUS_BEGIN", "PRE_STATUS_END", "PRE_DIFF_BEGIN", "PRE_DIFF_END",
    "MID_STATUS_BEGIN", "MID_STATUS_END", "MID_DIFF_BEGIN", "MID_DIFF_END",
    "POST_STATUS_BEGIN", "POST_STATUS_END", "POST_DIFF_BEGIN", "POST_DIFF_END",
    "COO_E2E_MINI_CAPSULE_BEGIN",
    "HEAD=", "EVID=", "JOB_PRETTY_ERR_BYTES=", "RESULT_PRETTY_ERR_BYTES=",
    "RC=", "PYTEST_SUMMARY=",
    "EVID_FILES_BEGIN", "EVID_FILES_END", "COO_E2E_MINI_CAPSULE_END",
]

def first_index(token):
    for i, line in enumerate(lines):
        if token.endswith("="):
            if line.startswith(token):
                return i
        elif line == token:
            return i
    return -1

indices = [first_index(t) for t in order_tokens]
if any(i < 0 for i in indices):
    pass
else:
    for i in range(len(indices) - 1):
        if indices[i] >= indices[i + 1]:
            missing.append(f"ORDER:{order_tokens[i]}->{order_tokens[i+1]}")

for label in ("PRE", "MID", "POST"):
    status_begin = first_index(f"{label}_STATUS_BEGIN")
    status_end = first_index(f"{label}_STATUS_END")
    diff_begin = first_index(f"{label}_DIFF_BEGIN")
    diff_end = first_index(f"{label}_DIFF_END")
    if status_begin < 0 or status_end < 0:
        missing.append(f"{label}:STATUS_MARKERS_MISSING")
    elif status_begin >= status_end:
        missing.append(f"{label}:STATUS_ORDER")
    elif (status_end - status_begin) < 2:
        missing.append(f"{label}:STATUS_EMPTY_BLOCK")
    if diff_begin < 0 or diff_end < 0:
        missing.append(f"{label}:DIFF_MARKERS_MISSING")
    elif diff_begin >= diff_end:
        missing.append(f"{label}:DIFF_ORDER")
    elif (diff_end - diff_begin) < 2:
        missing.append(f"{label}:DIFF_EMPTY_BLOCK")

evid_begin = first_index("EVID_FILES_BEGIN")
evid_end = first_index("EVID_FILES_END")
if evid_begin < 0 or evid_end < 0:
    missing.append("EVID_FILES_BLOCK_MISSING")
elif evid_begin >= evid_end:
    missing.append("EVID_FILES_BLOCK_ORDER")
elif (evid_end - evid_begin) < 2:
    missing.append("EVID_FILES_BLOCK_EMPTY")

if missing:
    missing_out.write_text("\n".join(missing) + "\n", encoding="utf-8")
    raise SystemExit(1)
missing_out.write_text("", encoding="utf-8")
PY
    then
      echo "INTERNAL_ERROR: CAPSULE_FORMAT" >&2
      safe_redact_file_head "$capsule_missing" 20 >&2
      exit 24
    fi
    if ! marker_block="$(render_capsule_marker "$capsule_file" "$capsule_missing")"; then
      echo "INTERNAL_ERROR: CAPSULE_FORMAT" >&2
      safe_redact_file_head "$capsule_missing" 20 >&2
      exit 24
    fi
    printf '%s\n' "$marker_block" > "$evid_dir/marker_receipt.txt"
    write_hashes "$evid_dir"
    printf '%s\n' "$marker_block"
    echo "COO_E2E_JOB_PATH=$job_path"
    echo "COO_E2E_RESULT_PATH=$result_path"
    echo "COO_E2E_RC=${rc_val:-unknown}"
    echo "COO_E2E_DURATION_S=${dur_val:-unknown}"
    if [ -n "$summary_line" ]; then
      echo "COO_E2E_PYTEST_SUMMARY=$summary_line"
    else
      echo "COO_E2E_PYTEST_SUMMARY=(not found)"
    fi
    if [ "$rc_e2e" -ne 0 ]; then
      exit "$rc_e2e"
    fi
    ;;
  tui)
    shift || true
    if [ "${1:-}" = "--" ]; then
      shift || true
    fi
    enter_training_dir
    print_header
    openclaw --profile "$OPENCLAW_PROFILE" tui "$@"
    ;;
  run)
    shift || true
    if [ "${1:-}" != "--" ]; then
      usage
      exit 2
    fi
    shift || true
    if [ "$#" -eq 0 ]; then
      usage
      exit 2
    fi
    print_header
    enter_training_dir
    "$@"
    ;;
  openclaw)
    shift || true
    if [ "${1:-}" != "--" ]; then
      usage
      exit 2
    fi
    shift || true
    print_header
    enter_training_dir
    openclaw --profile "$OPENCLAW_PROFILE" "$@"
    ;;
  *)
    usage
    exit 2
    ;;
esac
