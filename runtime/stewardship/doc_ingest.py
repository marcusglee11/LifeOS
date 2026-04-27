"""
doc_ingest: Deterministic document ingestion stage for the Stewardship Runner.

Invoked exclusively via:
    python scripts/steward_runner.py --run-id <ID> --ingest <manifest_path>

Never run standalone. All invariants in Issue #56 are enforced here.
"""

import fcntl
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Enums pulled from live repo (docs/01_governance/ARTEFACT_INDEX.json meta.binding_classes)
VALID_BINDING_CLASSES = frozenset({"FOUNDATIONAL", "GOVERNANCE", "PROTOCOL", "RUNTIME"})

# Canonicality values from live repo audit (docs/audit/LIFEOS_AUTHORITY_AUDIT_RESULT_2026-04-27.md)
VALID_CANONICALITY_VALUES = frozenset(
    {"canonical", "derived", "proposal", "draft", "stale", "archive", "external"}
)

SCHEMA_ID = "doc_steward.protocol_v1_1.ingest_manifest.v1"
SCHEMA_VERSION = "1.0"

# DAP M-3 + Document Steward Protocol Section 7 naming pattern
_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]*_v\d+\.\d+(\.\d+)?\.md$")

# Required metadata headers per Document Steward Protocol Section 3.1 ("Status, Authority, Date")
_REQUIRED_HEADERS = ["**Status**:", "**Authority**:"]

# Fields excluded from fingerprint computation (invariant 16)
_FINGERPRINT_EXCLUDE = {"commit"}

# Fields excluded from forbidden-fields check
_FORBIDDEN_MANIFEST_FIELDS = {
    "regenerate_strategic_corpus",
    "index_section",
}

_REQUIRED_MANIFEST_FIELDS = {
    "schema",
    "schema_version",
    "source_path",
    "dest_path",
    "title",
    "description",
    "artefact_key",
    "target_index_path",
    "binding_class",
    "canonicality",
    "supersedes",
    "related",
    "commit",
}


@dataclass
class DocIngestResult:
    success: bool
    failure_reason: str | None = None
    failure_invariant: str | None = None
    manifest_fingerprint: str | None = None
    is_idempotent_noop: bool = False
    staged_files: list[str] = field(default_factory=list)
    dest_path_written: str | None = None
    commit_enabled_for_runner: bool = False
    log_dir: Path | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "failure_reason": self.failure_reason,
            "failure_invariant": self.failure_invariant,
            "manifest_fingerprint": self.manifest_fingerprint,
            "is_idempotent_noop": self.is_idempotent_noop,
            "staged_files": self.staged_files,
            "dest_path_written": self.dest_path_written,
        }


def _compute_fingerprint(manifest: dict) -> str:
    """SHA256 over canonicalized manifest excluding commit block (invariant 16)."""
    filtered = {k: v for k, v in manifest.items() if k not in _FINGERPRINT_EXCLUDE}
    canonical = json.dumps(filtered, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _detect_index_shape(index_data: Any) -> str:
    """Returns 'dict', 'array', or 'unknown'."""
    artefacts = index_data.get("artefacts") if isinstance(index_data, dict) else None
    if isinstance(artefacts, dict):
        return "dict"
    if isinstance(artefacts, list):
        return "array"
    return "unknown"


def _has_artefact_key_collision(
    index_data: dict, shape: str, artefact_key: str, dest_rel: str
) -> bool:
    artefacts = index_data.get("artefacts")
    if shape == "dict" and isinstance(artefacts, dict):
        return artefact_key in artefacts and not artefact_key.startswith("_comment_")
    if shape == "array" and isinstance(artefacts, list):
        for entry in artefacts:
            if isinstance(entry, dict) and entry.get("path") == dest_rel:
                return True
    return False


def _update_index(
    index_data: dict,
    shape: str,
    artefact_key: str,
    dest_rel: str,
    supersedes: list[str],
) -> list[str]:
    """
    Mutate index_data in-place. Returns list of suggested-patch lines for
    dict-shape superseded_by (which cannot be stored inline).
    """
    suggested_patches: list[str] = []

    if shape == "dict":
        artefacts = index_data["artefacts"]
        artefacts[artefact_key] = dest_rel
        # Dict shape stores only string paths — cannot add superseded_by inline.
        # Emit suggested patch per invariant 15.
        for sup in supersedes:
            suggested_patches.append(
                f"# Suggested: annotate superseded doc {sup} -> superseded_by: {dest_rel}"
            )

    elif shape == "array":
        artefacts = index_data["artefacts"]
        # Add new entry
        new_entry: dict[str, Any] = {"path": dest_rel}
        artefacts.append(new_entry)
        # Update superseded entries with superseded_by (invariant 15)
        for entry in artefacts:
            if isinstance(entry, dict) and entry.get("path") in supersedes:
                entry["superseded_by"] = dest_rel

    return suggested_patches


def _emit_index_diff(
    log_dir: Path,
    manifest: dict,
    index_data: dict,
    shape: str,
    dest_rel: str,
    artefact_key: str,
    suggested_patches: list[str],
) -> None:
    """Write index_diff.md with suggested INDEX.md entry and any patch suggestions."""
    title = manifest.get("title", "")
    description = manifest.get("description", "")
    binding_class = manifest.get("binding_class", "")
    target_index = manifest.get("target_index_path", "")

    lines = [
        "# Suggested INDEX.md diff",
        "",
        f"**Title**: {title}",
        f"**Path**: {dest_rel}",
        f"**Description**: {description}",
        f"**Binding class**: {binding_class}",
        f"**Target index**: {target_index}",
        "",
        "Add to `docs/INDEX.md` under the appropriate section:",
        "",
        "```",
        f"- [{title}]({dest_rel}) — {description}",
        "```",
    ]

    if suggested_patches:
        lines += ["", "## Suggested superseded_by patches (dict-shaped index)", ""]
        lines += suggested_patches

    lines += [
        "",
        "INDEX.md auto-edit is deferred in v1. Apply the above manually.",
    ]

    (log_dir / "index_diff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _check_dl_doc_idempotency(repo_root: Path, fingerprint: str) -> bool:
    """Scan dl_doc for a successful DOC_STEWARD_RESULT packet matching this fingerprint."""
    dl_doc_dir = repo_root / "artifacts" / "ledger" / "dl_doc"
    if not dl_doc_dir.exists():
        return False
    for result_file in dl_doc_dir.glob("**/doc_steward_result.json"):
        try:
            data = json.loads(result_file.read_bytes())
            if data.get("manifest_fingerprint") == fingerprint and data.get("status") == "SUCCESS":
                return True
        except (json.JSONDecodeError, OSError):
            continue
    return False


def _load_completed_ledger(ledger_path: Path) -> set[str]:
    if not ledger_path.exists():
        return set()
    try:
        data = json.loads(ledger_path.read_bytes())
        return set(data.get("completed", []))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_completed_ledger(ledger_path: Path, fingerprints: set[str]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps({"completed": sorted(fingerprints)}, indent=2) + "\n",
        encoding="utf-8",
    )


def run(manifest_path: Path, runner_ctx: dict) -> DocIngestResult:
    """
    Execute the doc_ingest stage.

    runner_ctx keys:
        run_id:           str   — externally provided run identifier
        repo_root:        Path  — canonical repo root
        actually_commit:  bool  — True if CLI --commit was given
        config:           dict  — full steward_runner config (mutable)
    """
    run_id: str = runner_ctx["run_id"]
    repo_root: Path = runner_ctx["repo_root"]
    actually_commit: bool = runner_ctx["actually_commit"]
    config: dict = runner_ctx["config"]

    ingest_config = config.get("doc_ingest", {})
    allowed_dest_roots: list[str] = ingest_config.get("allowed_dest_roots", [])
    permitted_index_paths: list[str] = ingest_config.get("permitted_target_index_paths", [])

    log_dir = repo_root / "logs" / "steward_runner" / "doc_ingest" / run_id
    log_dir.mkdir(parents=True, exist_ok=True)
    trace_path = log_dir / "trace.jsonl"
    ledger_path = repo_root / "logs" / "steward_runner" / "doc_ingest" / "completed.json"

    def _trace(event: str, **kwargs: Any) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        record: dict[str, Any] = {"event": event, "run_id": run_id, "timestamp": ts}
        record.update(kwargs)
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    def _fail(reason: str, invariant: str, fingerprint: str | None = None) -> DocIngestResult:
        _trace("fail", failure_reason=reason, failure_invariant=invariant)
        return DocIngestResult(
            success=False,
            failure_reason=reason,
            failure_invariant=invariant,
            manifest_fingerprint=fingerprint,
            log_dir=log_dir,
        )

    # Workspace lock (invariant 20)
    lock_path = repo_root / "logs" / "steward_runner" / "doc_ingest.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, "w")  # noqa: WPS515
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        return _fail("workspace_lock_conflict", "INV-20")

    try:
        return _run_locked(
            manifest_path=manifest_path,
            run_id=run_id,
            repo_root=repo_root,
            actually_commit=actually_commit,
            config=config,
            allowed_dest_roots=allowed_dest_roots,
            permitted_index_paths=permitted_index_paths,
            log_dir=log_dir,
            ledger_path=ledger_path,
            trace=_trace,
            fail=_fail,
        )
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()


def _run_locked(
    manifest_path: Path,
    run_id: str,
    repo_root: Path,
    actually_commit: bool,
    config: dict,
    allowed_dest_roots: list[str],
    permitted_index_paths: list[str],
    log_dir: Path,
    ledger_path: Path,
    trace: Any,
    fail: Any,
) -> DocIngestResult:
    # Load manifest
    try:
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw)
    except (json.JSONDecodeError, OSError) as exc:
        return fail(f"manifest_load_failed:{exc}", "INV-manifest-load")

    if not isinstance(manifest, dict):
        return fail("manifest_not_a_dict", "INV-manifest-load")

    # Forbidden fields check
    for bad_field in _FORBIDDEN_MANIFEST_FIELDS:
        if bad_field in manifest:
            return fail(f"forbidden_field:{bad_field}", "INV-forbidden-field")

    # Required fields
    missing = _REQUIRED_MANIFEST_FIELDS - set(manifest.keys())
    if missing:
        return fail(f"missing_required_fields:{sorted(missing)}", "INV-required-fields")

    # Schema identity
    if manifest.get("schema") != SCHEMA_ID:
        return fail(f"wrong_schema:{manifest.get('schema')}", "INV-schema")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        return fail(f"wrong_schema_version:{manifest.get('schema_version')}", "INV-schema-version")

    # Enum validation
    if manifest["binding_class"] not in VALID_BINDING_CLASSES:
        return fail(f"invalid_binding_class:{manifest['binding_class']}", "INV-binding-class")
    if manifest["canonicality"] not in VALID_CANONICALITY_VALUES:
        return fail(f"invalid_canonicality:{manifest['canonicality']}", "INV-canonicality")

    # commit block
    commit_block = manifest.get("commit", {})
    if not isinstance(commit_block, dict) or not isinstance(commit_block.get("enabled"), bool):
        return fail("invalid_commit_block", "INV-commit-block")

    manifest_commit_enabled: bool = commit_block["enabled"]

    # Compute fingerprint (invariant 16)
    fingerprint = _compute_fingerprint(manifest)
    trace("fingerprint_computed", fingerprint=fingerprint)

    # Idempotent check (invariant 17)
    # Authoritative source: existing DOC_STEWARD_RESULT packets in dl_doc
    if _check_dl_doc_idempotency(repo_root, fingerprint):
        trace("idempotent_noop", fingerprint=fingerprint, source="dl_doc")
        return DocIngestResult(
            success=True,
            manifest_fingerprint=fingerprint,
            is_idempotent_noop=True,
            log_dir=log_dir,
        )
    # Local cache: completed.json in logs/ (optimization, not authoritative)
    completed = _load_completed_ledger(ledger_path)
    if fingerprint in completed:
        trace("idempotent_noop", fingerprint=fingerprint, source="local_cache")
        return DocIngestResult(
            success=True,
            manifest_fingerprint=fingerprint,
            is_idempotent_noop=True,
            log_dir=log_dir,
        )

    # Write normalized manifest for audit
    (log_dir / "manifest.normalized.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    # Resolve source_path (invariant 5)
    raw_source = manifest["source_path"]
    source_path = Path(raw_source) if os.path.isabs(raw_source) else repo_root / raw_source
    if not source_path.exists():
        return fail(f"source_not_found:{raw_source}", "INV-5", fingerprint)

    # Resolve dest_path (invariant 6: normalize to repo-relative)
    raw_dest = manifest["dest_path"]
    if os.path.isabs(raw_dest):
        try:
            dest_rel = Path(raw_dest).relative_to(repo_root)
        except ValueError:
            return fail(f"dest_not_under_repo_root:{raw_dest}", "INV-6", fingerprint)
    else:
        dest_rel = Path(raw_dest)
    dest_path = repo_root / dest_rel
    dest_rel_str = dest_rel.as_posix()

    # Invariant 7: allowed_dest_roots
    if not _is_dest_allowed(dest_rel_str, allowed_dest_roots):
        return fail(f"dest_outside_allowed_roots:{dest_rel_str}", "INV-7", fingerprint)

    # Invariant 8: dest must not already exist (no replace in v1)
    if dest_path.exists():
        return fail(f"dest_already_exists:{dest_rel_str}", "INV-8", fingerprint)

    # Invariant 9: filename naming convention
    filename = dest_path.name
    if not _FILENAME_PATTERN.match(filename):
        return fail(f"filename_convention_violation:{filename}", "INV-9", fingerprint)

    # Invariant 10: required metadata headers
    try:
        source_text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        return fail(f"source_read_failed:{exc}", "INV-10", fingerprint)
    for header in _REQUIRED_HEADERS:
        if header not in source_text:
            return fail(f"missing_required_header:{header}", "INV-10", fingerprint)

    # Invariant 11: target_index_path must exist
    raw_index = manifest["target_index_path"]
    if os.path.isabs(raw_index):
        target_index_path = Path(raw_index)
    else:
        target_index_path = repo_root / raw_index
    if not target_index_path.exists():
        return fail(f"target_index_not_found:{raw_index}", "INV-11", fingerprint)

    # Invariant 11-perm: permitted_target_index_paths whitelist — empty = fail closed
    raw_index_norm = raw_index.lstrip("/")
    if not any(raw_index_norm == p.lstrip("/") for p in permitted_index_paths):
        return fail(f"target_index_not_permitted:{raw_index}", "INV-11-perm", fingerprint)

    # Invariant 12: detect index shape
    try:
        index_data = json.loads(target_index_path.read_bytes())
    except (json.JSONDecodeError, OSError) as exc:
        return fail(f"target_index_parse_failed:{exc}", "INV-12", fingerprint)

    shape = _detect_index_shape(index_data)
    if shape == "unknown":
        return fail(f"unknown_index_shape:{raw_index}", "INV-12", fingerprint)

    # Invariant 13: artefact_key uniqueness
    artefact_key = manifest["artefact_key"]
    if _has_artefact_key_collision(index_data, shape, artefact_key, dest_rel_str):
        return fail(f"artefact_key_collision:{artefact_key}", "INV-13", fingerprint)

    # Invariants 14 & 15: supersedes targets must exist
    supersedes: list[str] = manifest.get("supersedes", [])
    for sup_raw in supersedes:
        sup_path = Path(sup_raw) if os.path.isabs(sup_raw) else repo_root / sup_raw
        if not sup_path.exists():
            return fail(f"supersedes_target_missing:{sup_raw}", "INV-14", fingerprint)

    # Dual-key commit gate (invariant 4 / AT-DI-03)
    if actually_commit and not manifest_commit_enabled:
        return fail("cli_commit_but_manifest_commit_disabled", "INV-4", fingerprint)

    source_sha256 = _file_sha256(source_path)
    trace(
        "validation_complete",
        source_sha256=source_sha256,
        shape=shape,
        dest=dest_rel_str,
        fingerprint=fingerprint,
    )

    # === Dry-run path (invariant 2, 3) ===
    if not actually_commit:
        # No repo-tree mutation — emit preview only
        _emit_index_diff(
            log_dir=log_dir,
            manifest=manifest,
            index_data=index_data,
            shape=shape,
            dest_rel=dest_rel_str,
            artefact_key=artefact_key,
            suggested_patches=[],
        )
        trace("dry_run_complete", dest=dest_rel_str, fingerprint=fingerprint)
        return DocIngestResult(
            success=True,
            manifest_fingerprint=fingerprint,
            log_dir=log_dir,
            commit_enabled_for_runner=False,
        )

    # === Commit path (invariant 4): actually_commit=True AND manifest_commit_enabled=True ===

    # Copy source to dest atomically (write to tmp then rename)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dest = dest_path.with_suffix(".tmp_ingest")
    shutil.copy2(str(source_path), str(tmp_dest))
    tmp_dest.rename(dest_path)
    dest_sha256 = _file_sha256(dest_path)
    trace(
        "file_copied",
        source=str(source_path),
        dest=dest_rel_str,
        source_sha256=source_sha256,
        dest_sha256=dest_sha256,
    )

    # Update ARTEFACT_INDEX
    suggested_patches = _update_index(
        index_data=index_data,
        shape=shape,
        artefact_key=artefact_key,
        dest_rel=dest_rel_str,
        supersedes=supersedes,
    )
    # Write updated index atomically
    tmp_index = target_index_path.with_suffix(".tmp_ingest")
    tmp_index.write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp_index.rename(target_index_path)
    trace("index_updated", target_index=raw_index, shape=shape, artefact_key=artefact_key)

    # Emit index diff and suggested patches
    _emit_index_diff(
        log_dir=log_dir,
        manifest=manifest,
        index_data=index_data,
        shape=shape,
        dest_rel=dest_rel_str,
        artefact_key=artefact_key,
        suggested_patches=suggested_patches,
    )

    # Update idempotency ledger (gitignored, local only)
    completed.add(fingerprint)
    _save_completed_ledger(ledger_path, completed)

    staged = sorted({dest_rel_str, raw_index.lstrip("/")})
    trace("ingest_complete", staged_files=staged, fingerprint=fingerprint)

    return DocIngestResult(
        success=True,
        manifest_fingerprint=fingerprint,
        staged_files=staged,
        dest_path_written=dest_rel_str,
        commit_enabled_for_runner=True,
        log_dir=log_dir,
    )


def emit_result_packet(
    run_id: str,
    repo_root: Path,
    ingest_result: DocIngestResult,
    commit_sha: str | None,
    manifest: dict,
) -> Path:
    """
    Write DOC_STEWARD_RESULT packet per Document_Steward_Protocol_v1.1 Section 10.1.
    Returns the written packet path.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    packet = {
        "packet_type": "DOC_STEWARD_RESULT",
        "ledger": "DL_DOC",
        "run_id": run_id,
        "completed_at": ts,
        "status": "SUCCESS" if ingest_result.success else "FAILURE",
        "manifest_fingerprint": ingest_result.manifest_fingerprint,
        "dest_path": ingest_result.dest_path_written,
        "staged_files": ingest_result.staged_files,
        "commit_sha": commit_sha,
        "is_idempotent_noop": ingest_result.is_idempotent_noop,
        "failure_reason": ingest_result.failure_reason,
        "failure_invariant": ingest_result.failure_invariant,
        "schema": "doc_steward.protocol_v1_1.result_packet.v1",
    }

    out_dir = repo_root / "artifacts" / "ledger" / "dl_doc" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "doc_steward_result.json"
    out_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return out_path


def _is_dest_allowed(dest_rel_str: str, allowed_dest_roots: list[str]) -> bool:
    for root in allowed_dest_roots:
        prefix = root.rstrip("/") + "/"
        if dest_rel_str.startswith(prefix):
            return True
    return False
