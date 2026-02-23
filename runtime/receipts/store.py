"""
Append-only receipt store for LifeOS build pipeline.

Strictly append-only per v2.4 §9.1 — no rename, overwrite, or delete.
Each receipt is stored with a ULID-named file.
Active receipt resolved by JSONL index + supersession chain traversal.

Store layout:
  <store_root>/
    receipts/
      acceptance/<ulid>.json       # each acceptance receipt (never renamed)
      blocked/<ulid>.json          # each blocked report
    artefacts/
      <workspace_sha>/<plan_core_sha256>/
        plan_core.json
        meta.json
        gate_results.json
        runlog.jsonl
        evidence_manifest.json
        review_summary.json
        review_summary.md
    index.jsonl                    # append-only query index
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runtime.util.atomic_write import atomic_write_text, atomic_write_json, atomic_write_bytes
from runtime.util.canonical import canonical_json_str


class ReceiptStore:
    """
    Append-only receipt store backed by filesystem + JSONL index.

    All writes are atomic (write-temp-rename pattern via atomic_write utilities).
    The index is append-only — entries are never removed or modified.
    Active receipt is resolved by JSONL index + supersession chain traversal.
    """

    def __init__(self, store_root: Path | str) -> None:
        """
        Args:
            store_root: Root directory for the store.
        """
        self.root = Path(store_root)
        self._receipts_dir = self.root / "receipts"
        self._acceptance_dir = self._receipts_dir / "acceptance"
        self._blocked_dir = self._receipts_dir / "blocked"
        self._artefacts_dir = self.root / "artefacts"
        self._index_path = self.root / "index.jsonl"

        # Ensure directories exist
        self._land_dir = self._receipts_dir / "land"
        self._acceptance_dir.mkdir(parents=True, exist_ok=True)
        self._blocked_dir.mkdir(parents=True, exist_ok=True)
        self._land_dir.mkdir(parents=True, exist_ok=True)
        self._artefacts_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Write methods (all append-only / atomic)
    # -------------------------------------------------------------------------

    def write_run_artefacts(
        self,
        workspace_sha: str,
        plan_core_sha256: str,
        artefacts: dict[str, Any],
    ) -> dict[str, Path]:
        """
        Store run artefacts under artefacts/<workspace_sha>/<plan_sha>/.

        Args:
            workspace_sha: Workspace commit SHA.
            plan_core_sha256: Plan core SHA-256.
            artefacts: Dict mapping filename -> content (str, dict, or bytes).
                       Special key "runlog.jsonl" is written as-is (str/bytes).

        Returns:
            Dict mapping filename -> absolute Path on disk.
        """
        run_dir = self._artefacts_dir / workspace_sha / plan_core_sha256
        run_dir.mkdir(parents=True, exist_ok=True)

        written: dict[str, Path] = {}
        for filename, content in artefacts.items():
            safe_name = self._sanitize_artefact_filename(filename)
            path = run_dir / safe_name
            self._ensure_append_only_target(path)
            if isinstance(content, bytes):
                atomic_write_bytes(path, content)
            elif isinstance(content, str):
                atomic_write_text(path, content)
            else:
                # dict/list → JSON
                atomic_write_json(path, content)
            written[safe_name] = path.resolve()
        return written

    def write_acceptance_receipt(self, receipt: dict) -> Path:
        """
        Store an acceptance receipt as receipts/acceptance/<ulid>.json.

        Appends an entry to index.jsonl.

        Args:
            receipt: Acceptance receipt dict (must have receipt_id, workspace_sha,
                     plan_core_sha256).

        Returns:
            Absolute Path to the stored receipt file.
        """
        receipt_id = self._sanitize_store_id(receipt["receipt_id"], "receipt_id")
        path = self._json_record_path(self._acceptance_dir, receipt_id)
        self._ensure_append_only_target(path)
        # Write receipt file (atomic)
        atomic_write_text(path, canonical_json_str(receipt))

        # Append to index (append-only)
        entry: dict[str, Any] = {
            "type": "acceptance",
            "receipt_id": receipt_id,
            "workspace_sha": receipt.get("workspace_sha", ""),
            "plan_core_sha256": receipt.get("plan_core_sha256", ""),
            "path": f"receipts/acceptance/{receipt_id}.json",
        }
        if receipt.get("supersedes"):
            entry["supersedes"] = receipt["supersedes"]
        self._append_index(entry)
        return path.resolve()

    def write_land_receipt(self, receipt: dict) -> Path:
        """
        Store a land receipt as receipts/land/<ulid>.json.

        Args:
            receipt: Land receipt dict (must have receipt_id, landed_sha, land_target).

        Returns:
            Absolute Path to the stored receipt file.
        """
        receipt_id = self._sanitize_store_id(receipt["receipt_id"], "receipt_id")
        path = self._json_record_path(self._land_dir, receipt_id)
        self._ensure_append_only_target(path)
        atomic_write_text(path, canonical_json_str(receipt))

        entry: dict[str, Any] = {
            "type": "land",
            "receipt_id": receipt_id,
            "landed_sha": receipt.get("landed_sha", ""),
            "land_target": receipt.get("land_target", ""),
            "path": f"receipts/land/{receipt_id}.json",
        }
        self._append_index(entry)
        return path.resolve()

    def write_blocked_report(self, report: dict) -> Path:
        """
        Store a blocked report as receipts/blocked/<ulid>.json.

        Args:
            report: Blocked report dict (must have report_id, workspace_sha,
                    plan_core_sha256).

        Returns:
            Absolute Path to the stored report file.
        """
        report_id = self._sanitize_store_id(report["report_id"], "report_id")
        path = self._json_record_path(self._blocked_dir, report_id)
        self._ensure_append_only_target(path)
        atomic_write_text(path, canonical_json_str(report))

        entry: dict[str, Any] = {
            "type": "blocked",
            "report_id": report_id,
            "workspace_sha": report.get("workspace_sha", ""),
            "plan_core_sha256": report.get("plan_core_sha256", ""),
            "path": f"receipts/blocked/{report_id}.json",
        }
        self._append_index(entry)
        return path.resolve()

    # -------------------------------------------------------------------------
    # Query methods
    # -------------------------------------------------------------------------

    def query_active_acceptance(
        self,
        workspace_sha: str,
        plan_core_sha256: str,
    ) -> dict | None:
        """
        Query the active acceptance receipt for a workspace+plan combination.

        Resolution algorithm:
        1. Read all index entries for matching (workspace_sha, plan_core_sha256)
        2. Build supersession chain: find terminal node (not superseded by any other)
        3. Tie-break: lexicographically greatest receipt_id (ULID = time-sortable)

        Args:
            workspace_sha: Workspace commit SHA.
            plan_core_sha256: Plan core SHA-256.

        Returns:
            Active acceptance receipt dict, or None if not found.
        """
        entries = self._read_index_entries(
            workspace_sha=workspace_sha,
            plan_core_sha256=plan_core_sha256,
            entry_type="acceptance",
        )
        if not entries:
            return None

        # Build set of superseded receipt IDs
        superseded_ids: set[str] = set()
        for entry in entries:
            if entry.get("supersedes"):
                superseded_ids.add(entry["supersedes"])

        # Find terminal nodes (not superseded by anyone)
        terminal = [e for e in entries if e["receipt_id"] not in superseded_ids]
        if not terminal:
            # Fallback: return latest by receipt_id
            terminal = entries

        # Tie-break: greatest ULID (latest time)
        active_entry = max(terminal, key=lambda e: e["receipt_id"])
        return self._load_receipt(active_entry["path"])

    def query_acceptance_by_id(self, receipt_id: str) -> dict | None:
        """
        Direct lookup of an acceptance receipt by its ID.

        Args:
            receipt_id: ULID receipt identifier.

        Returns:
            Acceptance receipt dict, or None if not found.
        """
        try:
            receipt_id = self._sanitize_store_id(receipt_id, "receipt_id")
            path = self._json_record_path(self._acceptance_dir, receipt_id)
        except ValueError:
            return None
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def query_all_receipts_for_workspace(
        self,
        workspace_sha: str,
    ) -> list[dict]:
        """
        Return all receipts (acceptance + blocked) for a given workspace SHA.

        Args:
            workspace_sha: Workspace commit SHA.

        Returns:
            List of receipt/report dicts.
        """
        entries = self._read_index_entries(workspace_sha=workspace_sha)
        receipts = []
        for entry in entries:
            data = self._load_receipt(entry["path"])
            if data is not None:
                receipts.append(data)
        return receipts

    def query_land_receipt_by_landed_sha(self, landed_sha: str) -> dict | None:
        """
        Return the land receipt for a given landed_sha, or None.

        Args:
            landed_sha: The merge commit SHA that was landed.

        Returns:
            Land receipt dict, or None if not found.
        """
        entries = [
            e for e in self._read_index_entries(entry_type="land")
            if e.get("landed_sha") == landed_sha
        ]
        if not entries:
            return None
        # Tie-break: most recent (lexicographically greatest ULID receipt_id)
        latest = max(entries, key=lambda e: e["receipt_id"])
        return self._load_receipt(latest["path"])

    def query_land_receipts_for_workspace(
        self,
        workspace_sha: str,
        plan_core_sha256: str | None = None,
    ) -> list[dict]:
        """
        Query land receipts linked to a workspace SHA via acceptance_lineage.

        Args:
            workspace_sha: Workspace commit SHA.
            plan_core_sha256: Optional plan core SHA-256 filter (unused currently).

        Returns:
            List of land receipt dicts for the workspace.
        """
        entries = self._read_index_entries(entry_type="land")
        results = []
        for entry in entries:
            data = self._load_receipt(entry["path"])
            if data is None:
                continue
            lineage = data.get("acceptance_lineage", {})
            if lineage.get("workspace_sha") == workspace_sha:
                results.append(data)
        return results

    # -------------------------------------------------------------------------
    # Recovery
    # -------------------------------------------------------------------------

    def rebuild_index(self) -> None:
        """
        Rebuild index.jsonl by scanning all receipt files on disk.

        Used for crash recovery. Rewrites the index from scratch.
        Preserves append-only semantics: new index replaces old one atomically.
        """
        entries: list[dict] = []

        # Scan acceptance receipts
        if self._acceptance_dir.exists():
            for path in sorted(self._acceptance_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    entry: dict[str, Any] = {
                        "type": "acceptance",
                        "receipt_id": data.get("receipt_id", path.stem),
                        "workspace_sha": data.get("workspace_sha", ""),
                        "plan_core_sha256": data.get("plan_core_sha256", ""),
                        "path": f"receipts/acceptance/{path.name}",
                    }
                    if data.get("supersedes"):
                        entry["supersedes"] = data["supersedes"]
                    entries.append(entry)
                except (json.JSONDecodeError, OSError):
                    pass

        # Scan blocked reports
        if self._blocked_dir.exists():
            for path in sorted(self._blocked_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    entry = {
                        "type": "blocked",
                        "report_id": data.get("report_id", path.stem),
                        "workspace_sha": data.get("workspace_sha", ""),
                        "plan_core_sha256": data.get("plan_core_sha256", ""),
                        "path": f"receipts/blocked/{path.name}",
                    }
                    entries.append(entry)
                except (json.JSONDecodeError, OSError):
                    pass

        # Write new index atomically
        lines = "\n".join(json.dumps(e, sort_keys=True) for e in entries)
        if lines:
            lines += "\n"
        atomic_write_text(self._index_path, lines)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _append_index(self, entry: dict) -> None:
        """Append a single entry to index.jsonl (append-only)."""
        line = json.dumps(entry, sort_keys=True) + "\n"
        with self._index_path.open("a", encoding="utf-8") as f:
            f.write(line)

    def _read_index_entries(
        self,
        workspace_sha: str | None = None,
        plan_core_sha256: str | None = None,
        entry_type: str | None = None,
    ) -> list[dict]:
        """Read and optionally filter index entries."""
        if not self._index_path.exists():
            return []
        entries = []
        for line in self._index_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if workspace_sha and entry.get("workspace_sha") != workspace_sha:
                continue
            if plan_core_sha256 and entry.get("plan_core_sha256") != plan_core_sha256:
                continue
            if entry_type and entry.get("type") != entry_type:
                continue
            entries.append(entry)
        return entries

    def _load_receipt(self, relative_path: str) -> dict | None:
        """Load a receipt/report JSON file by relative path from store root."""
        path = (self.root / relative_path).resolve()
        root = self.root.resolve()
        if path != root and root not in path.parents:
            return None
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _sanitize_artefact_filename(self, filename: str) -> str:
        """
        Validate artefact filename for safe append-only writes.

        Only basename-like filenames are allowed (no path separators, no traversal).
        """
        if not filename:
            raise ValueError("Artefact filename must be non-empty")
        if "/" in filename or "\\" in filename:
            raise ValueError(f"Artefact filename must not contain path separators: {filename!r}")
        if filename in {".", ".."}:
            raise ValueError(f"Artefact filename is invalid: {filename!r}")
        if Path(filename).is_absolute():
            raise ValueError(f"Artefact filename must be relative: {filename!r}")
        return filename

    def _sanitize_store_id(self, value: object, field_name: str) -> str:
        """Validate receipt/report IDs before deriving filesystem paths."""
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field_name} must be a non-empty string")
        if "/" in value or "\\" in value:
            raise ValueError(f"{field_name} must not contain path separators: {value!r}")
        if value in {".", ".."}:
            raise ValueError(f"{field_name} is invalid: {value!r}")
        if Path(value).is_absolute():
            raise ValueError(f"{field_name} must be relative: {value!r}")
        return value

    def _json_record_path(self, directory: Path, identifier: str) -> Path:
        """Resolve and validate a <directory>/<identifier>.json path."""
        path = (directory / f"{identifier}.json").resolve()
        directory_resolved = directory.resolve()
        if path != directory_resolved and directory_resolved not in path.parents:
            raise ValueError(f"Refusing path outside store directory: {path}")
        return path

    def _ensure_append_only_target(self, path: Path) -> None:
        """Fail if write target already exists to preserve append-only semantics."""
        if path.exists():
            raise ValueError(f"Append-only store refuses overwrite: {path}")
