# Review Packet: Capability Proof Experiment

**Mode**: Lightweight Stewardship  
**Date**: 2026-01-08  
**Files Changed**: 2

## Summary

Executed proof-of-capability experiment to demonstrate bounded build task execution. Successfully registered `run_tests` operation in `runtime/orchestration/operations.py` and created comprehensive unit tests. All 5 tests pass.

---

## Success Criteria Evaluation

| Criterion | Status |
|-----------|--------|
| Syntactically valid Python produced | ✅ PASS |
| Follows existing patterns | ✅ PASS |
| `pytest` passes on new test | ✅ PASS (5/5) |
| No modifications outside allowed paths | ✅ PASS |

**CAPABILITY_PROOF_001: ✅ PASS**

---

## Changes

| File | Change Type |
|------|-------------|
| [operations.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/orchestration/operations.py) | MODIFIED (+71 lines) |
| [test_registry_run_tests.py](file:///c:/Users/cabra/Projects/LifeOS/tests/test_registry_run_tests.py) | CREATED (+161 lines) |

---

## Evidence Artifacts

| Artifact | Path |
|----------|------|
| Test Output | [pytest_output.txt](file:///c:/Users/cabra/Projects/LifeOS/artifacts/capability_proof/pytest_output.txt) |
| Code Diff | [changes.diff](file:///c:/Users/cabra/Projects/LifeOS/artifacts/capability_proof/changes.diff) |
| Post-State | [post_state.txt](file:///c:/Users/cabra/Projects/LifeOS/artifacts/capability_proof/post_state.txt) |
| Full Summary | [EVIDENCE_SUMMARY.md](file:///c:/Users/cabra/Projects/LifeOS/artifacts/capability_proof/EVIDENCE_SUMMARY.md) |

---

## Diff Appendix

### operations.py

```diff
@@ -314,6 +314,7 @@
             "tool_invoke": self._handle_tool_invoke,
             "packet_route": self._handle_packet_route,
             "gate_check": self._handle_gate_check,
+            "run_tests": self._handle_run_tests,
         }

@@ -399,4 +400,74 @@
+    def _handle_run_tests(
+        self,
+        operation: Operation,
+        ctx: ExecutionContext
+    ) -> tuple[Any, Dict[str, Any]]:
+        """
+        Handle run_tests operation.
+        
+        Executes pytest on specified test paths within envelope constraints.
+        Per LifeOS Build Loop Phase 3 requirements.
+        
+        Params:
+            test_paths: List of test file/directory paths (relative to repo_root)
+            pytest_args: Optional list of additional pytest arguments
+        """
+        test_paths = operation.params.get("test_paths", ["tests/"])
+        pytest_args = operation.params.get("pytest_args", ["-v", "-q"])
+        
+        # Validate test_paths are within allowed paths
+        for test_path in test_paths:
+            norm_path = test_path.replace("\\", "/")
+            allowed = False
+            for allowed_path in ctx.envelope.allowed_paths:
+                allowed_norm = allowed_path.replace("\\", "/")
+                if norm_path.startswith(allowed_norm) or allowed_norm.startswith(norm_path):
+                    allowed = True
+                    break
+            
+            if not allowed and ctx.envelope.allowed_paths:
+                raise EnvelopeViolation(
+                    f"Test path '{test_path}' not in allowed paths: {ctx.envelope.allowed_paths}"
+                )
+        
+        # Build and execute pytest command
+        cmd = ["python", "-m", "pytest"] + pytest_args + test_paths
+        
+        try:
+            result = subprocess.run(
+                cmd,
+                cwd=str(ctx.repo_root),
+                capture_output=True,
+                text=True,
+                timeout=ctx.envelope.timeout_seconds,
+            )
+            
+            passed = result.returncode == 0
+            
+            return {
+                "passed": passed,
+                "exit_code": result.returncode,
+                "stdout": result.stdout,
+                "stderr": result.stderr,
+                "test_paths": test_paths,
+            }, {
+                "handler": "run_tests",
+                "passed": passed,
+                "exit_code": result.returncode,
+                "stdout_lines": len(result.stdout.splitlines()),
+                "stderr_lines": len(result.stderr.splitlines()),
+            }
+        
+        except subprocess.TimeoutExpired as e:
+            raise OperationFailed(
+                f"Test execution timed out after {ctx.envelope.timeout_seconds}s"
+            )
+        except Exception as e:
+            raise OperationFailed(f"Failed to execute tests: {str(e)}")
```

### test_registry_run_tests.py (NEW)

```python
"""Tests for run_tests operation registration."""

class TestRunTestsRegistration:
    """Test run_tests operation registration and behavior."""
    
    def test_run_tests_is_registered(self, executor):
        """run_tests operation type is recognized by executor."""
        
    def test_run_tests_executes_pytest(self, executor, context):
        """run_tests calls pytest with correct arguments."""
        
    def test_run_tests_returns_output_on_failure(self, executor, context):
        """run_tests captures output even when tests fail."""
        
    def test_run_tests_enforces_envelope(self, executor, context):
        """run_tests rejects paths outside envelope."""
        
    def test_run_tests_handles_timeout(self, executor, context):
        """run_tests handles pytest timeout gracefully."""
```

---

## Recommendation

Per decision tree: **PASS → Proceed to Phase 3a (Council Ruling for envelope expansion) and Phase 3b (real OpenCode integration)**.
