#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTANCE_ID=""
JOB_TYPE=""
MODE="${MODE:-raw}"
WORKSPACE_DIR="${WORKSPACE_DIR:-$HOME/.openclaw/workspace}"
AGENT_ID="${AGENT_ID:-main}"
HOST_ID="${HOST_ID:-$(hostname -s)}"
GCP_PROJECT="${GCP_PROJECT:-openclawhost}"
SECRET_NAME="${SECRET_NAME:-}"
STATE_DIR="${STATE_DIR:-$HOME/.openclaw/shared-memory-sync}"
API_URL="${API_URL:-https://api.supermemory.ai/v3/documents}"
ROOTS_FILE="${ROOTS_FILE:-}"
FAIL_ON_PII=0
DRY_RUN=0
VERBOSE=0

usage() {
  cat <<'EOF'
Usage: openclaw_shared_memory_sync.sh [options]

Sync local OpenClaw memory documents to Supermemory using deterministic customIds.

Options:
  --instance <id>      Instance id (for secret default: supermemory-api-key-<id>)
  --job-type <type>    Job type label (accepted for wrapper compatibility)
  --mode <raw|curated> Sync mode (default: raw)
  --workspace <path>   Workspace root (default: ~/.openclaw/workspace)
  --agent-id <id>      Agent id tag (default: main)
  --host-id <id>       Host id tag (default: hostname -s)
  --project <id>       GCP project for secret fetch (default: openclawhost)
  --secret <name>      Secret name for API key
  --state-dir <path>   State directory (default: ~/.openclaw/shared-memory-sync)
  --roots-file <path>  Curated roots policy JSON for curated mode
  --fail-on-pii        Fail closed on PII detection (forced in curated mode)
  --dry-run            Print planned uploads without API calls
  --verbose            Print per-file details
  -h, --help           Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --instance) INSTANCE_ID="$2"; shift 2 ;;
    --job-type) JOB_TYPE="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --workspace) WORKSPACE_DIR="$2"; shift 2 ;;
    --agent-id) AGENT_ID="$2"; shift 2 ;;
    --host-id) HOST_ID="$2"; shift 2 ;;
    --project) GCP_PROJECT="$2"; shift 2 ;;
    --secret) SECRET_NAME="$2"; shift 2 ;;
    --state-dir) STATE_DIR="$2"; shift 2 ;;
    --roots-file) ROOTS_FILE="$2"; shift 2 ;;
    --fail-on-pii) FAIL_ON_PII=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --verbose) VERBOSE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [ "$MODE" != "raw" ] && [ "$MODE" != "curated" ]; then
  echo "unsupported mode: $MODE (expected raw|curated)" >&2
  exit 2
fi

if [ -n "$INSTANCE_ID" ]; then
  if [ -z "${SECRET_NAME}" ]; then
    SECRET_NAME="supermemory-api-key-${INSTANCE_ID}"
  fi
  if [ "${HOST_ID}" = "$(hostname -s)" ]; then
    HOST_ID="${INSTANCE_ID}"
  fi
fi

if [ -z "$SECRET_NAME" ]; then
  SECRET_NAME="supermemory-api-key"
fi

if [ "$MODE" = "curated" ]; then
  FAIL_ON_PII=1
fi

if [ ! -d "$WORKSPACE_DIR" ]; then
  echo "workspace missing: $WORKSPACE_DIR" >&2
  exit 1
fi

for cmd in jq curl gcloud python3 sha256sum; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "missing required command: $cmd" >&2
    exit 1
  fi
done

mkdir -p "$STATE_DIR/state" "$STATE_DIR/runs"
RUN_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_KEY="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_JSON="$STATE_DIR/runs/$RUN_KEY.json"
TMP_DIR="$(mktemp -d "$STATE_DIR/.tmp.XXXXXX")"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if [ "$MODE" = "curated" ] && [ -z "$ROOTS_FILE" ]; then
  auto_roots="$TMP_DIR/curated_roots.json"
  candidate_roots=()
  if [ -d "$WORKSPACE_DIR/memory_curated" ]; then
    candidate_roots+=("$WORKSPACE_DIR/memory_curated")
  fi
  if [ -d "$WORKSPACE_DIR/memory_shared_curated" ]; then
    candidate_roots+=("$WORKSPACE_DIR/memory_shared_curated")
  fi
  if [ "${#candidate_roots[@]}" -eq 0 ]; then
    echo "curated mode requires --roots-file or curated root dirs under workspace" >&2
    exit 2
  fi
  jq -n \
    --argjson roots "$(printf '%s\n' "${candidate_roots[@]}" | jq -R . | jq -s .)" \
    --argjson globs '["**/*.md","**/*.txt","**/*.json","**/*.yaml","**/*.yml"]' \
    '{roots:$roots,include_globs:$globs}' > "$auto_roots"
  ROOTS_FILE="$auto_roots"
fi

guard_args=(
  "--workspace" "$WORKSPACE_DIR"
  "--mode" "$MODE"
  "--json-summary"
  "--summary-out" "$TMP_DIR/guard_summary.json"
)
if [ "$MODE" = "curated" ]; then
  guard_args+=("--roots-file" "$ROOTS_FILE")
fi
if [ "$FAIL_ON_PII" -eq 1 ]; then
  guard_args+=("--fail-on-pii")
fi

guard_out="$TMP_DIR/guard_stdout.json"
if ! python3 "$SCRIPT_DIR/openclaw_memory_policy_guard.py" "${guard_args[@]}" >"$guard_out" 2>"$TMP_DIR/guard_stderr.log"; then
  echo "memory policy guard failed" >&2
  cat "$guard_out" >&2 || true
  cat "$TMP_DIR/guard_stderr.log" >&2 || true
  exit 1
fi

mapfile -t SOURCE_FILES < <(
  python3 - "$MODE" "$WORKSPACE_DIR" "$ROOTS_FILE" <<'PY'
import json
import sys
from pathlib import Path

mode = sys.argv[1]
workspace = Path(sys.argv[2]).expanduser().resolve()
roots_file = sys.argv[3]

def emit(path: Path) -> None:
    print(str(path.resolve()))

if mode == "raw":
    memory_md = workspace / "MEMORY.md"
    if memory_md.exists() and memory_md.is_file():
        emit(memory_md)
    memory_dir = workspace / "memory"
    if memory_dir.exists():
        for path in sorted(memory_dir.rglob("*.md")):
            if path.is_file():
                emit(path)
else:
    payload = json.loads(Path(roots_file).read_text(encoding="utf-8"))
    roots = [Path(p).expanduser().resolve() for p in payload.get("roots", [])]
    globs = payload.get("include_globs") or ["**/*.md", "**/*.txt", "**/*.json", "**/*.yaml", "**/*.yml"]
    seen = set()
    for root in roots:
        for pattern in globs:
            for path in sorted(root.glob(pattern)):
                if not path.is_file():
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                emit(resolved)
PY
)

if [ "${#SOURCE_FILES[@]}" -eq 0 ]; then
  echo "No source files found for mode=$MODE under workspace=$WORKSPACE_DIR"
  jq -n \
    --arg ts "$RUN_TS" \
    --arg mode "$MODE" \
    '{runAt:$ts,mode:$mode,filesTotal:0,uploaded:0,skipped:0,failed:0,dryRun:true,items:[]}' > "$RUN_JSON"
  exit 0
fi

SUPERMEMORY_API_KEY="$(gcloud --project "$GCP_PROJECT" secrets versions access latest --secret "$SECRET_NAME")"
if [ -z "$SUPERMEMORY_API_KEY" ]; then
  echo "failed to resolve SUPERMEMORY_API_KEY from secret=$SECRET_NAME project=$GCP_PROJECT" >&2
  exit 1
fi

sanitize_tag() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9_-' '-' | sed 's/^-*//; s/-*$//' | cut -c1-60
}

total=0
uploaded=0
skipped=0
failed=0
items_jsonl="$TMP_DIR/items.jsonl"

for abs in "${SOURCE_FILES[@]}"; do
  total=$((total+1))
  if [ ! -f "$abs" ]; then
    continue
  fi

  rel="$abs"
  case "$abs" in
    "$WORKSPACE_DIR"/*) rel="${abs#"$WORKSPACE_DIR/"}" ;;
  esac

  sha="$(sha256sum "$abs" | awk '{print $1}')"
  key="$(printf '%s|%s' "$MODE" "$rel" | sha256sum | awk '{print $1}')"
  state_file="$STATE_DIR/state/$key.json"
  prev_sha=""
  if [ -f "$state_file" ]; then
    prev_sha="$(jq -r '.sha // empty' "$state_file" 2>/dev/null || true)"
  fi

  if [ "$prev_sha" = "$sha" ]; then
    skipped=$((skipped+1))
    [ "$VERBOSE" -eq 1 ] && echo "skip unchanged: $rel"
    jq -cn --arg rel "$rel" --arg sha "$sha" '{file:$rel,sha:$sha,status:"skipped"}' >> "$items_jsonl"
    continue
  fi

  host_tag="$(sanitize_tag "$HOST_ID")"
  agent_tag="$(sanitize_tag "$AGENT_ID")"
  mode_tag="$(sanitize_tag "$MODE")"
  custom_id="oc-${host_tag}-${agent_tag}-${mode_tag}-$(printf '%s' "$rel" | sha256sum | cut -c1-20)"

  staged="$TMP_DIR/$(basename "$rel").staged.md"
  {
    echo "# OpenClaw Shared Memory"
    echo "mode: $MODE"
    echo "source_host: $HOST_ID"
    echo "source_agent: $AGENT_ID"
    echo "source_file: $rel"
    echo "source_sha256: $sha"
    echo "synced_at: $RUN_TS"
    [ -n "$INSTANCE_ID" ] && echo "instance_id: $INSTANCE_ID"
    [ -n "$JOB_TYPE" ] && echo "job_type: $JOB_TYPE"
    echo
    echo "---"
    echo
    cat "$abs"
  } > "$staged"

  if [ "$DRY_RUN" -eq 1 ]; then
    uploaded=$((uploaded+1))
    [ "$VERBOSE" -eq 1 ] && echo "dry-run upload: $rel"
    jq -cn --arg rel "$rel" --arg sha "$sha" --arg customId "$custom_id" '{file:$rel,sha:$sha,customId:$customId,status:"dry-run"}' >> "$items_jsonl"
    continue
  fi

  payload="$TMP_DIR/payload.json"
  jq -n \
    --rawfile content "$staged" \
    --arg customId "$custom_id" \
    --arg mode "$MODE" \
    --arg instance "$INSTANCE_ID" \
    '{content:$content,customId:$customId,metadata:{mode:$mode,instance:$instance}}' > "$payload"

  resp_file="$TMP_DIR/resp.json"
  http_code="$(curl -sS -o "$resp_file" -w '%{http_code}' -X POST "$API_URL" \
    -H "Authorization: Bearer $SUPERMEMORY_API_KEY" \
    -H 'Content-Type: application/json' \
    --data-binary @"$payload")"

  if [ "$http_code" != "200" ] && [ "$http_code" != "201" ] && [ "$http_code" != "202" ]; then
    failed=$((failed+1))
    short_err="$(jq -c . "$resp_file" 2>/dev/null || sed -n '1,2p' "$resp_file")"
    echo "upload failed ($http_code): $rel" >&2
    jq -cn --arg rel "$rel" --arg sha "$sha" --arg http "$http_code" --arg err "$short_err" '{file:$rel,sha:$sha,status:"failed",http:$http,error:$err}' >> "$items_jsonl"
    continue
  fi

  doc_id="$(jq -r '.id // empty' "$resp_file" 2>/dev/null || true)"
  uploaded=$((uploaded+1))
  [ "$VERBOSE" -eq 1 ] && echo "uploaded: $rel${doc_id:+ (id: $doc_id)}"

  jq -n \
    --arg rel "$rel" \
    --arg sha "$sha" \
    --arg customId "$custom_id" \
    --arg docId "$doc_id" \
    --arg syncedAt "$RUN_TS" \
    '{file:$rel,sha:$sha,customId:$customId,docId:$docId,syncedAt:$syncedAt}' > "$state_file"

  jq -cn --arg rel "$rel" --arg sha "$sha" --arg customId "$custom_id" --arg docId "$doc_id" '{file:$rel,sha:$sha,customId:$customId,docId:$docId,status:"uploaded"}' >> "$items_jsonl"
done

jq -cs \
  --arg ts "$RUN_TS" \
  --arg workspace "$WORKSPACE_DIR" \
  --arg host "$HOST_ID" \
  --arg agent "$AGENT_ID" \
  --arg mode "$MODE" \
  --arg instance "$INSTANCE_ID" \
  --arg jobType "$JOB_TYPE" \
  --arg secret "$SECRET_NAME" \
  --argjson total "$total" \
  --argjson uploaded "$uploaded" \
  --argjson skipped "$skipped" \
  --argjson failed "$failed" \
  --argjson dryRun "$DRY_RUN" \
  '{runAt:$ts,workspace:$workspace,host:$host,agent:$agent,mode:$mode,instance:$instance,jobType:$jobType,secretRef:$secret,filesTotal:$total,uploaded:$uploaded,skipped:$skipped,failed:$failed,dryRun:($dryRun==1),items:.}' "$items_jsonl" > "$RUN_JSON"

unset SUPERMEMORY_API_KEY

echo "shared-memory sync complete: mode=$MODE total=$total uploaded=$uploaded skipped=$skipped failed=$failed"
echo "run receipt: $RUN_JSON"

[ "$failed" -eq 0 ]
