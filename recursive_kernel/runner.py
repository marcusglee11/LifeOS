import os
import json
import datetime
import sys
from .planner import Planner, Task
from .builder import Builder
from .verifier import Verifier
from .autogate import AutoGate, GateDecision

class RecursiveRunner:
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.config_path = os.path.join(repo_root, "config", "recursive_kernel_config.yaml")
        self.backlog_path = os.path.join(repo_root, "config", "backlog.yaml")
        self.planner = Planner(self.config_path, self.backlog_path)
        self.builder = Builder()
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

        # 2. Act (Build)
        success = self.builder.build(task)
        
        if not success:
            print(f"Builder fail or no builder for tasks of type {task.type}")
            # Log failure
            self._log_result(task, applied=False, verified=False, decision="NONE", reason="Builder failed")
            return

        print("Build step complete. Verifying...")

        # 3. Verify
        # Verification runs the configured test command
        verified = self.verifier.verify()
        print(f"Verification result: {'PASS' if verified else 'FAIL'}")

        # 4. Gate
        # For v0.1 we assume docs/INDEX_v1.1.md changed if build succeeded for that task
        changed_files = []
        if task.domain == 'docs' and task.type == 'rebuild_index':
            changed_files = ["docs/INDEX_v1.1.md"]
        
        # Mock diff lines for now since we don't have easy git diff access in python without libs/subprocess complexity
        diff_lines = 10 # Assume small change
        
        decision = self.gate.evaluate(changed_files, diff_lines)
        print(f"Gate Decision: {decision.name}")

        # 5. Log
        self._log_result(task, applied=True, verified=verified, decision=decision.name)
        
        # 6. Action based on decision
        if decision == GateDecision.AUTO_MERGE and verified:
            print("Change is safe to merge. (Simulation: Committed)")
        else:
            print("Change requires human review.")

    def _log_result(self, task: Task, applied: bool, verified: bool, decision: str, reason: str = ""):
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "task_id": task.id,
            "domain": task.domain,
            "applied": applied,
            "verified": verified,
            "gate_decision": decision,
            "reason": reason
        }
        filename = f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{task.id}.json"
        path = os.path.join(self.logs_dir, filename)
        with open(path, "w") as f:
            json.dump(log_entry, f, indent=2)
        print(f"Log written to {path}")

if __name__ == "__main__":
    # If running as module (python -m recursive_kernel.runner), cwd is likely root
    runner = RecursiveRunner(os.getcwd())
    runner.run()
