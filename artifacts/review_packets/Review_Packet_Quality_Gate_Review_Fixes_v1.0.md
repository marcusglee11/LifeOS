# Review Packet — Quality Gate Review Fixes (v1.0)

## Scope Envelope
- **Allowed:** [runtime/tools/workflow_pack.py](/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/quality-standard-v1/runtime/tools/workflow_pack.py), [runtime/tests/test_quality_gate.py](/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/quality-standard-v1/runtime/tests/test_quality_gate.py), this review packet, and the companion Claude context pack.
- **Forbidden:** `docs/00_foundations/`, `docs/01_governance/`, `config/governance/protected_artefacts.json`, and unrelated runtime/orchestration behavior outside the quality-gate review findings.
- **Authority Notes:** Work stayed inside the existing quality-gate rollout branch and used the shared closure-oriented enforcement model already established in the prior implementation.

## Summary
- Fixed the three concrete review findings on the quality gate: config-only Markdown/YAML policy changes now lint the tracked corpus, manifest waivers now affect runner classification, and missing local tool binaries are downgraded to advisory only for changed-scope local runs.
- Added targeted tests so the changed-scope vs repo-scope binary behavior and waiver/config-trigger paths are covered directly.

## Issue Catalogue
| Issue | Severity | Status | Notes |
| --- | --- | --- | --- |
| Missing local binaries blocked closure despite repo-side policy intent | P1 | Closed | Changed-scope local runs now downgrade missing executables to advisory; repo-scope remains blocking. |
| Config-only Markdown/YAML lint policy edits did not execute the real corpus checks | P1 | Closed | Router now expands to tracked Markdown/YAML files when only lint config changes. |
| Manifest waivers were declared but never applied by the runner | P1 | Closed | Runner now evaluates active waivers by tool, failure class, path, and expiry. |

## Acceptance Criteria
| Criterion | Status | Evidence Pointer | SHA-256 |
| --- | --- | --- | --- |
| Config-only `.markdownlint.json` change routes tracked docs Markdown to `markdownlint`. | Pass | [test_quality_gate.py](/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/quality-standard-v1/runtime/tests/test_quality_gate.py) | N/A |
| Config-only `.yamllint.yml` change routes tracked YAML files to `yamllint`. | Pass | [test_quality_gate.py](/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/quality-standard-v1/runtime/tests/test_quality_gate.py) | N/A |
| Manifest waivers can downgrade a blocking quality failure to advisory. | Pass | [workflow_pack.py](/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/quality-standard-v1/runtime/tools/workflow_pack.py) and [test_quality_gate.py](/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/quality-standard-v1/runtime/tests/test_quality_gate.py) | N/A |
| Missing local quality binaries do not block changed-scope local runs, but still block repo-scope runs. | Pass | [workflow_pack.py](/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/quality-standard-v1/runtime/tools/workflow_pack.py) and [test_quality_gate.py](/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/quality-standard-v1/runtime/tests/test_quality_gate.py) | N/A |
| Focused verification remains green after the fixes. | Pass | `pytest -q runtime/tests/test_quality_gate.py runtime/tests/test_closure_gate.py runtime/tests/test_workflow_pack.py` | N/A |

## Closure Evidence Checklist
| Category | Requirement | Verified |
| --- | --- | --- |
| **Provenance** | Code commit hash + message | `32b6522f620f187e8ab58d9d1cee9f902e52d88b` — `fix: address quality gate review findings` |
|  | Docs commit hash + message | N/A |
|  | Changed file list (paths) | `runtime/tools/workflow_pack.py`; `runtime/tests/test_quality_gate.py`; `artifacts/review_packets/Review_Packet_Quality_Gate_Review_Fixes_v1.0.md`; `artifacts/context_packs/CCP_Quality_Gate_Review_Fixes_Claude_v1.0.md` |
| **Artifacts** | `attempt_ledger.jsonl` | N/A |
|  | `CEO_Terminal_Packet.md` | N/A |
|  | `Review_Packet_attempt_XXXX.md` | N/A |
|  | Closure Bundle + Validator Output | N/A |
|  | Docs touched (each path) | N/A |
| **Repro** | Test command(s) exact cmdline | `pytest -q runtime/tests/test_quality_gate.py runtime/tests/test_closure_gate.py runtime/tests/test_workflow_pack.py`; `pytest runtime/tests -q -x`; `python3 scripts/workflow/quality_gate.py check --scope changed --changed-file runtime/tools/workflow_pack.py --changed-file runtime/tests/test_quality_gate.py --json` |
|  | Run command(s) to reproduce artifact | `git show 32b6522f620f187e8ab58d9d1cee9f902e52d88b -- runtime/tools/workflow_pack.py runtime/tests/test_quality_gate.py`; review this packet and the companion Claude context pack |
| **Governance** | Doc-Steward routing proof | N/A (no `docs/` paths touched) |
|  | Policy/Ruling refs invoked | `AGENTS.md`; `CLAUDE.md`; `config/quality/manifest.yaml` |
| **Outcome** | Terminal outcome proof | PASS for the targeted review-fix scope; repo-wide fast-fail still stops on the pre-existing unrelated `runtime/tests/orchestration/coo/test_promotion_fixtures.py::test_all_promotion_fixtures` failure |

## Non-Goals
- No attempt was made to fix the unrelated OpenClaw/gateway failure in [test_promotion_fixtures.py](/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/quality-standard-v1/runtime/tests/orchestration/coo/test_promotion_fixtures.py#L57).
- No portable quality-pack extraction was added.
- No additional agent-specific enforcement seam was introduced beyond the existing closure path.
- No local tool installation was performed in this environment.

## Appendix A — Patch Set + File Manifest
#### Review Target
- Commit: `32b6522f620f187e8ab58d9d1cee9f902e52d88b`
- Subject: `fix: address quality gate review findings`

#### File Manifest
- `runtime/tools/workflow_pack.py`
- `runtime/tests/test_quality_gate.py`

#### Patch Set
```diff
commit 32b6522f620f187e8ab58d9d1cee9f902e52d88b
Author: OpenCode Robot <robot@lifeos.local>
Date:   Sat Mar 28 10:55:19 2026 +1100

    fix: address quality gate review findings
---
 runtime/tests/test_quality_gate.py | 83 ++++++++++++++++++++++++++++++++
 runtime/tools/workflow_pack.py     | 96 ++++++++++++++++++++++++++++++++++++--
 2 files changed, 174 insertions(+), 5 deletions(-)

diff --git a/runtime/tests/test_quality_gate.py b/runtime/tests/test_quality_gate.py
index 1e3c54ff..9f2cb23e 100644
--- a/runtime/tests/test_quality_gate.py
+++ b/runtime/tests/test_quality_gate.py
@@ -28,6 +28,24 @@ def test_route_quality_tools_markdown_is_style_only() -> None:
     assert routed["mypy"] == []
 
 
+def test_route_quality_tools_config_only_markdown_change_runs_docs(monkeypatch) -> None:
+    monkeypatch.setattr(
+        "runtime.tools.workflow_pack._git_tracked_files",
+        lambda repo_root: ["docs/02_protocols/example.md", "runtime/tools/workflow_pack.py"],
+    )
+    routed = route_quality_tools(Path("."), [".markdownlint.json"], scope="changed")
+    assert routed["markdownlint"] == ["docs/02_protocols/example.md"]
+
+
+def test_route_quality_tools_config_only_yaml_change_runs_yaml(monkeypatch) -> None:
+    monkeypatch.setattr(
+        "runtime.tools.workflow_pack._git_tracked_files",
+        lambda repo_root: [".github/workflows/ci.yml", "config/quality/manifest.yaml", "docs/02_protocols/example.md"],
+    )
+    routed = route_quality_tools(Path("."), [".yamllint.yml"], scope="changed")
+    assert routed["yamllint"] == [".github/workflows/ci.yml", "config/quality/manifest.yaml"]
+
+
 def test_run_quality_gates_blocks_on_blocking_failure(monkeypatch) -> None:
     def fake_run(*args, **kwargs):
         cmd = args[0]
@@ -54,6 +72,71 @@ def test_run_quality_gates_allows_advisory_failure(monkeypatch) -> None:
     assert any(row["tool"] == "yamllint" and row["mode"] == "advisory" and not row["passed"] for row in result["results"])
 
 
+def test_run_quality_gates_missing_blocking_tool_is_advisory(monkeypatch) -> None:
+    def fake_run(*args, **kwargs):
+        cmd = args[0]
+        if cmd[:2] == ["ruff", "check"] or cmd[:2] == ["ruff", "format"]:
+            raise FileNotFoundError("ruff")
+        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
+
+    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
+    result = run_quality_gates(Path("."), ["runtime/tools/workflow_pack.py"], scope="changed")
+    assert result["passed"] is True
+    assert any(
+        row["tool"] == "ruff_check" and row["mode"] == "advisory" and row["waiver_reason"] == "tool_unavailable_locally"
+        for row in result["results"]
+    )
+
+
+def test_run_quality_gates_missing_blocking_tool_stays_blocking_in_repo_scope(monkeypatch) -> None:
+    def fake_run(*args, **kwargs):
+        cmd = args[0]
+        if cmd[:2] == ["ruff", "check"] or cmd[:2] == ["ruff", "format"]:
+            raise FileNotFoundError("ruff")
+        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
+
+    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
+    result = run_quality_gates(Path("."), ["runtime/tools/workflow_pack.py"], scope="repo")
+    assert result["passed"] is False
+    assert any(row["tool"] == "ruff_check" and row["mode"] == "blocking" for row in result["results"])
+
+
+def test_run_quality_gates_waiver_downgrades_blocking_failure(monkeypatch) -> None:
+    manifest = {
+        "repo": {"python_targets": ["runtime"]},
+        "tools": {
+            "ruff_check": {
+                "enabled": True,
+                "mode": "blocking",
+                "scopes": ["changed"],
+                "autofix_allowed": True,
+                "failure_class": "ruff_error",
+            }
+        },
+        "waivers": [
+            {
+                "tool": "ruff_check",
+                "failure_class": "ruff_error",
+                "paths": ["runtime/tools/"],
+                "reason": "temporary waiver",
+            }
+        ],
+    }
+
+    def fake_run(*args, **kwargs):
+        cmd = args[0]
+        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="unused import")
+
+    monkeypatch.setattr("runtime.tools.workflow_pack.load_quality_manifest", lambda repo_root: manifest)
+    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
+    result = run_quality_gates(Path("."), ["runtime/tools/workflow_pack.py"], scope="changed")
+    assert result["passed"] is True
+    assert any(
+        row["tool"] == "ruff_check" and row["mode"] == "advisory" and row["waiver_reason"] == "temporary waiver"
+        for row in result["results"]
+    )
+
+
 def test_doctor_quality_tools_reports_presence(monkeypatch) -> None:
     def fake_which(name: str) -> str | None:
         return None if name in {"ruff", "mypy"} else f"/usr/bin/{name}"
diff --git a/runtime/tools/workflow_pack.py b/runtime/tools/workflow_pack.py
index 34e87196..609dbfea 100644
--- a/runtime/tools/workflow_pack.py
+++ b/runtime/tools/workflow_pack.py
@@ -9,7 +9,7 @@ import shlex
 import shutil
 import subprocess
 import sys
-from datetime import datetime
+from datetime import datetime, timezone
 from difflib import SequenceMatcher
 from pathlib import Path
 from typing import Iterable, Optional, Sequence
@@ -170,6 +170,10 @@ def _git_tracked_files(repo_root: Path) -> list[str]:
     return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
 
 
+def _tracked_files_matching(repo_root: Path, predicate) -> list[str]:
+    return [file_path for file_path in _git_tracked_files(repo_root) if predicate(file_path)]
+
+
 def _filter_quality_scope_files(files: Sequence[str], manifest: dict) -> list[str]:
     exclude_prefixes = manifest.get("repo", {}).get("exclude_prefixes", []) or []
     filtered = []
@@ -233,10 +237,10 @@ def route_quality_tools(repo_root: Path, changed_files: Sequence[str], scope: st
         elif name in QUALITY_MARKDOWN_CONFIG_FILES:
             markdown_trigger = True
 
-        if suffix in {".yml", ".yaml"}:
-            yaml_files.append(file_path)
+        if name in QUALITY_YAML_CONFIG_FILES:
             yaml_trigger = True
-        elif name in QUALITY_YAML_CONFIG_FILES:
+        elif suffix in {".yml", ".yaml"}:
+            yaml_files.append(file_path)
             yaml_trigger = True
 
         if suffix == ".sh":
@@ -249,8 +253,18 @@ def route_quality_tools(repo_root: Path, changed_files: Sequence[str], scope: st
     if biome_trigger:
         routed["biome"] = _unique_ordered(biome_files)
     if markdown_trigger:
+        if not markdown_files:
+            markdown_files = _tracked_files_matching(
+                repo_root,
+                lambda file_path: file_path.startswith("docs/") and file_path.endswith(".md"),
+            )
         routed["markdownlint"] = _unique_ordered(markdown_files)
     if yaml_trigger:
+        if not yaml_files:
+            yaml_files = _tracked_files_matching(
+                repo_root,
+                lambda file_path: file_path.endswith((".yml", ".yaml")),
+            )
         routed["yamllint"] = _unique_ordered(yaml_files)
     if shell_files:
         routed["shellcheck"] = _unique_ordered(shell_files)
@@ -267,6 +281,65 @@ def _quality_tool_enabled(manifest: dict, tool_name: str, scope: str) -> bool:
     return bool(tool_cfg.get("enabled")) and scope in (tool_cfg.get("scopes") or [])
 
 
+def _waiver_applies_to_files(paths: Sequence[str], files: Sequence[str]) -> bool:
+    if not paths:
+        return True
+    for file_path in files:
+        for candidate in paths:
+            if file_path == candidate or file_path.startswith(candidate.rstrip("/") + "/"):
+                return True
+    return False
+
+
+def _waiver_is_active(waiver: dict) -> bool:
+    expires_at = str(waiver.get("expires_at", "")).strip()
+    if not expires_at:
+        return True
+    try:
+        expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
+    except ValueError:
+        return False
+    if expires.tzinfo is None:
+        expires = expires.replace(tzinfo=timezone.utc)
+    return expires >= datetime.now(timezone.utc)
+
+
+def _resolve_quality_result_mode(
+    manifest: dict,
+    tool_name: str,
+    failure_class: str,
+    files: Sequence[str],
+    passed: bool,
+    details: str,
+    *,
+    scope: str,
+    missing_executable: bool,
+) -> tuple[str, bool, str | None]:
+    mode = _quality_tool_mode(manifest, tool_name)
+    if passed:
+        return mode, False, None
+
+    if missing_executable and scope == "changed":
+        return "advisory", False, "tool_unavailable_locally"
+
+    waivers = manifest.get("waivers") or []
+    for waiver in waivers:
+        if not isinstance(waiver, dict):
+            continue
+        if not _waiver_is_active(waiver):
+            continue
+        if waiver.get("tool") not in (None, "", tool_name):
+            continue
+        if waiver.get("failure_class") not in (None, "", failure_class):
+            continue
+        waiver_paths = waiver.get("paths") or []
+        if not _waiver_applies_to_files(waiver_paths, files):
+            continue
+        return "advisory", True, str(waiver.get("reason", "")).strip() or None
+
+    return mode, False, None
+
+
 def _build_quality_command(
     repo_root: Path,
     manifest: dict,
@@ -388,19 +461,32 @@ def run_quality_gates(
             )
             passed = proc.returncode == 0
             details = (proc.stderr or "").strip() or (proc.stdout or "").strip()
+            missing_executable = False
         except FileNotFoundError as exc:
             passed = False
             details = str(exc)
+            missing_executable = True
 
         result = {
             "tool": tool_name,
             "failure_class": str(tool_cfg.get("failure_class", "quality_error")),
-            "mode": _quality_tool_mode(manifest, tool_name),
             "passed": passed,
             "auto_fixed": bool(fix and tool_cfg.get("autofix_allowed") and passed),
             "files": list(files),
             "details": details,
         }
+        result["mode"], result["waived"], waiver_reason = _resolve_quality_result_mode(
+            manifest,
+            tool_name,
+            str(result["failure_class"]),
+            list(files),
+            passed,
+            details,
+            scope=scope,
+            missing_executable=missing_executable,
+        )
+        if waiver_reason:
+            result["waiver_reason"] = waiver_reason
         results.append(result)
         auto_fixed = auto_fixed or bool(result["auto_fixed"])
 ```
