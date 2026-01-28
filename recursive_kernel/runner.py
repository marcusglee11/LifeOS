"""
Recursive Kernel Runner (Phase 4 P1)

Entry point for recursive builds. Supports:
- Legacy mode: YAML-based backlog with Planner/Builder/Verifier
- Autonomous mode: Markdown backlog with AutonomousBuildCycleMission dispatch
"""
import os
import json
import datetime
import sys
import argparse
import subprocess
import uuid
from pathlib import Path
from typing import Optional, Tuple

from .planner import Planner, Task
from .builder import Builder
from .verifier import Verifier
from .autogate import AutoGate, GateDecision
from .backlog_parser import (
    parse_backlog,
    select_eligible_item,
    mark_item_done,
    BacklogItem,
    BacklogParseError,
)

# FP-003: Derive repo root from module location for cwd-independence
REPO_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Canonical backlog path
BACKLOG_PATH = REPO_ROOT / "docs" / "11_admin" / "BACKLOG.md"

# Artifact output directory (aligned with repo conventions)
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "packets"


class AutonomousRunner:
    """
    Autonomous runner that dispatches AutonomousBuildCycleMission from backlog.
    
    Provides:
    - Deterministic backlog parsing and item selection
    - Git dirty preflight check
    - Structured payload dispatch
    - Fail-closed outcome routing
    - Dry-run mode with zero side effects
    """
    
    def __init__(self, repo_root: Path, dry_run: bool = False, max_items: int = 1):
        self.repo_root = repo_root
        self.dry_run = dry_run
        self.max_items = min(max_items, 3)  # Hard cap at 3
        self.backlog_path = repo_root / "docs" / "11_admin" / "BACKLOG.md"
        self.artifacts_dir = repo_root / "artifacts" / "packets"
        self.run_id = str(uuid.uuid4())[:8]
        self.run_ts = datetime.datetime.now()
    
    def _get_git_head(self) -> Optional[str]:
        """Get current git HEAD commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def _is_git_dirty(self) -> bool:
        """Check if git working directory is dirty."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return bool(result.stdout.strip())
        except Exception:
            pass
        return True  # Fail-closed: assume dirty if can't check
    
    def _emit_artifact(self, name: str, content: dict) -> Path:
        """Emit a JSON artifact to the packets directory."""
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        timestamp = self.run_ts.strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{self.run_id}_{timestamp}.json"
        path = self.artifacts_dir / filename
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        return path
    
    def _emit_blocked(self, reason: str, item: Optional[BacklogItem] = None) -> int:
        """Emit a BLOCKED artifact and return exit code."""
        content = {
            "type": "BLOCKED",
            "reason": reason,
            "run_id": self.run_id,
            "timestamp": self.run_ts.isoformat(),
            "item_key": item.item_key if item else None,
            "item_title": item.title if item else None,
        }
        path = self._emit_artifact("BLOCKED", content)
        print(f"BLOCKED: {reason}")
        print(f"Artifact: {path}")
        return 1
    
    def _emit_escalation(self, reason: str, item: BacklogItem) -> int:
        """Emit an ESCALATION artifact and return exit code."""
        content = {
            "type": "ESCALATION_REQUESTED",
            "reason": reason,
            "run_id": self.run_id,
            "timestamp": self.run_ts.isoformat(),
            "item_key": item.item_key,
            "item_title": item.title,
            "item_payload": item.to_dispatch_payload(),
        }
        path = self._emit_artifact("ESCALATION", content)
        print(f"ESCALATION REQUESTED: {reason}")
        print(f"Artifact: {path}")
        return 2
    
    def _emit_waiver_request(self, reason: str, item: BacklogItem) -> int:
        """Emit a WAIVER_REQUEST artifact and return exit code."""
        content = {
            "type": "WAIVER_REQUESTED",
            "reason": reason,
            "run_id": self.run_id,
            "timestamp": self.run_ts.isoformat(),
            "item_key": item.item_key,
            "item_title": item.title,
            "item_payload": item.to_dispatch_payload(),
        }
        path = self._emit_artifact("WAIVER_REQUEST", content)
        print(f"WAIVER REQUESTED: {reason}")
        print(f"Artifact: {path}")
        return 3
    
    def run(self) -> int:
        """
        Run autonomous mode.
        
        Returns:
            0 on success (or dry-run), non-zero on failure/halt
        """
        print(f"Recursive Kernel Runner v0.2 (Autonomous Mode)")
        print(f"Run ID: {self.run_id}")
        print(f"Dry Run: {self.dry_run}")
        print()
        
        # 1. Preflight: Git dirty check
        if self._is_git_dirty():
            if not self.dry_run:
                return self._emit_blocked("Repository has uncommitted changes (git dirty)")
            else:
                print("WARNING: Repository has uncommitted changes (ignored in dry-run)")
        
        baseline_commit = self._get_git_head()
        print(f"Baseline commit: {baseline_commit or 'UNKNOWN'}")
        
        # 2. Parse backlog
        try:
            items = parse_backlog(self.backlog_path)
        except FileNotFoundError as e:
            return self._emit_blocked(f"Backlog file not found: {e}")
        except BacklogParseError as e:
            return self._emit_blocked(f"Backlog parse error: {e}")
        
        print(f"Parsed {len(items)} total items from backlog")
        
        # 3. Select eligible item
        selected = select_eligible_item(items)
        
        if selected is None:
            print("No eligible P0/P1 TODO items found. Exiting cleanly.")
            return 0
        
        print()
        print("=== Selected Item ===")
        print(f"  Key: {selected.item_key}")
        print(f"  Priority: {selected.priority.value}")
        print(f"  Title: {selected.title}")
        print(f"  DoD: {selected.dod}")
        print(f"  Owner: {selected.owner}")
        print(f"  Line: {selected.line_number}")
        print()
        
        # 4. Dry-run: exit without side effects
        if self.dry_run:
            print("DRY RUN: Would dispatch mission with payload:")
            payload = selected.to_dispatch_payload()
            print(json.dumps(payload, indent=2))
            print()
            print("DRY RUN complete. No side effects performed.")
            return 0
        
        # 5. Create MissionContext and dispatch
        result = self._dispatch_mission(selected, baseline_commit)
        
        # 6. Handle outcome
        return self._handle_result(result, selected)
    
    def _dispatch_mission(self, item: BacklogItem, baseline_commit: Optional[str]) -> dict:
        """
        Dispatch AutonomousBuildCycleMission with structured payload.
        
        Returns:
            MissionResult-like dict
        """
        try:
            from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
            from runtime.orchestration.missions.base import MissionContext
            
            context = MissionContext(
                repo_root=self.repo_root,
                baseline_commit=baseline_commit or "UNKNOWN",
                run_id=self.run_id,
                operation_executor=None,
            )
            
            # Structured payload (not just title string)
            inputs = {
                "task_spec": item.title,  # For backward compatibility
                **item.to_dispatch_payload(),  # Full structured data
            }
            
            mission = AutonomousBuildCycleMission()
            mission.validate_inputs(inputs)
            result = mission.run(context, inputs)
            
            return result.to_dict() if hasattr(result, 'to_dict') else {
                "success": result.success,
                "error": result.error,
                "escalation_reason": result.escalation_reason,
                "outputs": result.outputs,
                "evidence": result.evidence,
            }
            
        except ImportError as e:
            return {"success": False, "error": f"Import error: {e}", "import_failed": True}
        except Exception as e:
            return {"success": False, "error": f"Mission dispatch error: {e}"}
    
    def _check_evidence_contract(self, result: dict) -> Tuple[bool, str]:
        """
        Check if evidence contract is satisfied for marking item DONE.
        
        Minimal contract:
        - success=True
        - No escalation_reason
        - No waiver-related error
        
        Returns:
            (satisfied, reason)
        """
        if not result.get("success"):
            return False, "Mission did not succeed"
        
        if result.get("escalation_reason"):
            return False, f"Escalation required: {result.get('escalation_reason')}"
        
        error = result.get("error", "")
        if error and "WAIVER" in str(error).upper():
            return False, f"Waiver required: {error}"
        
        return True, "Evidence contract satisfied"
    
    def _handle_result(self, result: dict, item: BacklogItem) -> int:
        """Handle mission result and return exit code."""
        
        # Check for import/dispatch failure
        if result.get("import_failed"):
            return self._emit_blocked(result.get("error", "Unknown import error"), item)
        
        # Check for escalation
        escalation = result.get("escalation_reason")
        if escalation:
            return self._emit_escalation(escalation, item)
        
        # Check for waiver
        error = result.get("error", "")
        if error and "WAIVER" in str(error).upper():
            return self._emit_waiver_request(error, item)
        
        # Check for other errors
        if error and not result.get("success"):
            return self._emit_blocked(f"Mission error: {error}", item)
        
        # Check evidence contract
        satisfied, reason = self._check_evidence_contract(result)
        
        if not satisfied:
            return self._emit_blocked(f"Evidence contract not satisfied: {reason}", item)
        
        # Success path: mark done
        try:
            mark_item_done(self.backlog_path, item)
            print(f"SUCCESS: Item marked DONE in backlog")
            print(f"  Item: {item.title}")
            print(f"  Key: {item.item_key}")
            return 0
        except BacklogParseError as e:
            return self._emit_blocked(f"Failed to mark item done: {e}", item)


class RecursiveRunner:
    """Legacy runner using YAML-based backlog."""
    
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.config_path = os.path.join(repo_root, "config", "recursive_kernel_config.yaml")
        self.backlog_path = os.path.join(repo_root, "config", "backlog.yaml")
        self.planner = Planner(self.config_path, self.backlog_path)
        # FP-004: Inject repo_root into Builder
        self.builder = Builder(repo_root)
        # Verifier needs command from config
        self.config = self.planner.config # already loaded
        self.verifier = Verifier(self.config.get("test_command", "pytest"))
        self.gate = AutoGate(self.config)
        self.logs_dir = os.path.join(repo_root, "logs", "recursive_runs")
        os.makedirs(self.logs_dir, exist_ok=True)

    def run(self):
        print("Recursive Kernel Runner v0.1")
        
        # 1. Plan
        try:
            task = self.planner.plan_next_task()
        except Exception as e:
            print(f"Planning failed: {e}")
            return

        if not task:
            print("No eligible tasks found.")
            return

        print(f"Selected task: {task.id} - {task.description} ({task.domain})")
        
        # FP-003: Pin run timestamp at task selection
        run_ts = datetime.datetime.now()

        # 2. Act (Build)
        success = self.builder.build(task)
        
        if not success:
            print(f"Builder fail or no builder for tasks of type {task.type}")
            # Log failure
            self._log_result(task, applied=False, verified=False, decision="NONE", reason="Builder failed", run_ts=run_ts)
            return

        print("Build step complete. Verifying...")

        # 3. Verify
        # Verification runs the configured test command
        verified = self.verifier.verify()
        print(f"Verification result: {'PASS' if verified else 'FAIL'}")

        # 4. Gate
        # H-003: Reference actual index filename
        changed_files = []
        if task.domain == 'docs' and task.type == 'rebuild_index':
            changed_files = ["docs/INDEX_v1.1.md"]
        
        # Mock diff lines for now since we don't have easy git diff access in python without libs/subprocess complexity
        diff_lines = 10 # Assume small change
        
        decision = self.gate.evaluate(changed_files, diff_lines)
        print(f"Gate Decision: {decision.name}")

        # 5. Log
        self._log_result(task, applied=True, verified=verified, decision=decision.name, run_ts=run_ts)
        
        # 6. Action based on decision
        if decision == GateDecision.AUTO_MERGE and verified:
            print("Change is safe to merge. (Simulation: Committed)")
        else:
            print("Change requires human review.")

    def _log_result(self, task: Task, applied: bool, verified: bool, decision: str, run_ts: datetime.datetime, reason: str = ""):
        """
        Log the result of a task execution.
        
        FP-003: Uses pinned run_ts for both timestamp field and filename.
        FP-006: Includes effective_decision field.
        """
        # FP-006: Compute effective decision
        if decision == "AUTO_MERGE" and verified:
            effective_decision = "AUTO_MERGE_ALLOWED"
        elif decision == "AUTO_MERGE" and not verified:
            effective_decision = "AUTO_MERGE_BLOCKED_BY_TESTS"
        else:
            effective_decision = "HUMAN_REVIEW"
        
        log_entry = {
            "timestamp": run_ts.isoformat(),
            "task_id": task.id,
            "domain": task.domain,
            "applied": applied,
            "verified": verified,
            "gate_decision": decision,
            "effective_decision": effective_decision,  # FP-006
            "reason": reason
        }
        # FP-003: Use pinned run_ts for filename
        filename = f"run_{run_ts.strftime('%Y%m%d_%H%M%S')}_{task.id}.json"
        path = os.path.join(self.logs_dir, filename)
        with open(path, "w") as f:
            json.dump(log_entry, f, indent=2)
        print(f"Log written to {path}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Recursive Kernel Runner - Autonomous Build Dispatch"
    )
    parser.add_argument(
        "--autonomous",
        action="store_true",
        help="Enable autonomous mode (dispatch AutonomousBuildCycleMission)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run: select item but do not dispatch or mutate"
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=1,
        help="Maximum items to process (default=1, max=3)"
    )
    
    args = parser.parse_args()
    
    if args.autonomous:
        runner = AutonomousRunner(
            repo_root=REPO_ROOT,
            dry_run=args.dry_run,
            max_items=args.max_items,
        )
        exit_code = runner.run()
        sys.exit(exit_code)
    else:
        # Legacy mode
        runner = RecursiveRunner(str(REPO_ROOT))
        runner.run()


if __name__ == "__main__":
    main()
