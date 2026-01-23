"""
Build With Validation Mission v0.1

Implements a deterministic, smoke-first build validation mission using subprocesses.
Replaces the previous Worker->Validator LLM loop implementation.
"""
from __future__ import annotations

import hashlib
import json
import re  # Added for P0.1 commit validation
import sys
from pathlib import Path
from dataclasses import dataclass
from runtime.tools.evidence_capture import run_command_capture, CaptureStatus, CaptureResult

# External dependencies (assumed present in env)
import jsonschema

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
    MissionExecutionError,
)

# Constants
SCHEMA_DIR = Path(__file__).parent / "schemas"
PARAMS_SCHEMA_FILE = SCHEMA_DIR / "build_with_validation_params_v0_1.json"
RESULT_SCHEMA_FILE = SCHEMA_DIR / "build_with_validation_result_v0_1.json"


class BuildWithValidationMission(BaseMission):
    """
    Build With Validation Mission
    
    Executes a deterministic validation sequence:
    1. Validate inputs against strict JSON schema.
    2. Compute deterministic run token.
    3. Run 'smoke' checks (pyproject check + compileall).
    4. Optionally run 'full' checks (pytest).
    5. Capture all outputs to evidence validation directory.
    6. Return result with cryptographic proofs.
    """

    @property
    def mission_type(self) -> MissionType:
        return MissionType.BUILD_WITH_VALIDATION

    def _load_schema(self, path: Path) -> Dict[str, Any]:
        """Load a JSON schema from disk."""
        if not path.exists():
            raise MissionExecutionError(f"Schema file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate mission inputs against the params schema.
        Fail-closed: raises MissionValidationError on any schema violation.
        
        Note: jsonschema 4.x does NOT apply defaults by default. 
        We rely on the schema for type checking, but apply defaults explicitly 
        in run() to ensure deterministic behavior.
        """
        # Load schema
        try:
            schema = self._load_schema(PARAMS_SCHEMA_FILE)
        except Exception as e:
            raise MissionValidationError(f"Failed to load params schema: {e}")

        # Coerce None to empty dict
        if inputs is None:
            inputs = {}

        # Validate
        try:
            jsonschema.validate(instance=inputs, schema=schema)
        except jsonschema.ValidationError as e:
            raise MissionValidationError(f"Invalid inputs: {e.message}")

    def run(self, context: MissionContext, inputs: Dict[str, Any]) -> MissionResult:
        # P0.1: Handle inputs=None deterministically and type-check
        if inputs is None:
            inputs = {}
        if not isinstance(inputs, dict):
            # Fail-closed via exception, caught by engine generally, or distinct error
            # The prompt asks to raise MissionValidationError
            raise MissionValidationError(f"inputs must be an object/dict, got {type(inputs)}")

        # Refinement P0.1: Enforce strict baseline_commit invariants (Option A)
        if context.baseline_commit is not None:
             # Must be 7-40 hex chars
            if not re.match(r"^[0-9a-fA-F]{7,40}$", context.baseline_commit):
                raise MissionValidationError(
                    f"Invalid baseline_commit format (must be 7-40 hex chars): {context.baseline_commit}"
                )

        # 0. Validate Inputs (Fail-Closed)
        self.validate_inputs(inputs)

        # 1. Apply Defaults Explicitly (Determinism P0.2)
        defaults = {
            "mode": "smoke",
            "pytest_args": ["-q"],
            "pytest_targets": [],
            "capture_root_rel": "artifacts/evidence/mission_runs"
        }
        
        # Merge defaults (fail-closed handled by validate_inputs additionalProperties:false)
        params = defaults.copy()
        params.update(inputs)
        
        # 2. Generate Deterministic Run Token
        canonical_params_json = json.dumps(
            params, 
            sort_keys=True, 
            separators=(",", ":"), 
            ensure_ascii=False
        )
        
        # Normalize baseline commit (none -> "null")
        baseline_commit_norm = context.baseline_commit or "null"
        
        # Hash: type + commit + params
        token_payload = f"build_with_validation\n{baseline_commit_norm}\n{canonical_params_json}"
        run_token = hashlib.sha256(token_payload.encode("utf-8")).hexdigest()[:16]
        
        # 3. Setup Evidence Directory
        evidence_dir = context.repo_root / params["capture_root_rel"] / "build_with_validation" / run_token
        evidence_dir.mkdir(parents=True, exist_ok=True)
        
        evidence_map: Dict[str, str] = {}

        def _capture_to_dict(res: CaptureResult) -> Dict[str, Any]:
            """Convert CaptureResult to schema-compliant dict."""
            return {
                "command": res.command,
                "exit_code": res.exit_code,
                "stdout_sha256": res.stdout_sha256,
                "stderr_sha256": res.stderr_sha256
            }

        # Substituted shared primitive (runtime/tools/evidence_capture.py)

        executed_steps = []
        
        # 4. Smoke Test Execution
        # SMOKE-1: Check pyproject.toml
        smoke_cmd = [sys.executable, "-c", 
            "import sys, os; "
            "sys.exit(0 if os.path.exists('pyproject.toml') else 1)"
        ]
        smoke1_res = run_command_capture("smoke_check", smoke_cmd, context.repo_root, evidence_dir)
        # Update evidence map with results
        evidence_map[smoke1_res.stdout_path.name] = smoke1_res.stdout_sha256
        evidence_map[smoke1_res.stderr_path.name] = smoke1_res.stderr_sha256
        evidence_map[smoke1_res.exitcode_path.name] = smoke1_res.exitcode_sha256
        evidence_map[smoke1_res.meta_path.name] = smoke1_res.meta_sha256 # Corrected meta hash
        
        executed_steps.append("smoke:check_pyproject")
        
        if smoke1_res.exit_code != 0:
             # Fast fail
             final_smoke = smoke1_res
        else:
            # SMOKE-2: Compileall
            # Use sys.executable to ensure same python env
            smoke2_cmd = [sys.executable, "-m", "compileall", "-q", "runtime"]
            smoke2_res = run_command_capture("smoke_compile", smoke2_cmd, context.repo_root, evidence_dir)
            
            # Update evidence map with results
            evidence_map[smoke2_res.stdout_path.name] = smoke2_res.stdout_sha256
            evidence_map[smoke2_res.stderr_path.name] = smoke2_res.stderr_sha256
            evidence_map[smoke2_res.exitcode_path.name] = smoke2_res.exitcode_sha256
            evidence_map[smoke2_res.meta_path.name] = smoke2_res.meta_sha256

            executed_steps.append("smoke:compileall")
            final_smoke = smoke2_res
            
        # 5. Full Validation (Optional)
        pytest_block = None
        
        if params["mode"] == "full":
            if final_smoke.exit_code == 0:
                # P0.4: Fail closed if no targets and defaults needed
                targets = params["pytest_targets"]
                if not targets:
                    # P0.4: Fail closed if no targets (no default subset allowed)
                    # P1.1: Return audit-grade receipt (preserve smoke outputs & evidence path)
                    
                    # Construct partial evidence/outputs for the receipt
                    final_evidence = {
                        "run_token": run_token,
                        "evidence_path": str(evidence_dir),
                        **evidence_map
                    }
                    
                    partial_outputs = {
                        "run_token": run_token,
                        "repo_root": str(context.repo_root),
                        "baseline_commit": context.baseline_commit,
                        "params_canonical_sha256": hashlib.sha256(canonical_params_json.encode("utf-8")).hexdigest(),
                        "smoke": _capture_to_dict(final_smoke), # Fix: Use helper
                        "pytest": None,
                        "evidence_dir": str(evidence_dir),
                        "evidence": final_evidence
                    }
                    
                    return self._make_result(
                        success=False,
                        error="Full mode requires explicit pytest_targets (fail-closed, no defaults allowed)",
                        executed_steps=executed_steps,
                        outputs=partial_outputs, # Include what we have
                        evidence=final_evidence
                    )
                
                cmd = [sys.executable, "-m", "pytest"] + params["pytest_args"] + targets
                pytest_res = run_command_capture("pytest", cmd, context.repo_root, evidence_dir)
                # Update evidence map with results
                evidence_map[pytest_res.stdout_path.name] = pytest_res.stdout_sha256
                evidence_map[pytest_res.stderr_path.name] = pytest_res.stderr_sha256
                evidence_map[pytest_res.exitcode_path.name] = pytest_res.exitcode_sha256
                evidence_map[pytest_res.meta_path.name] = pytest_res.meta_sha256

                executed_steps.append("full:pytest")
                pytest_block = pytest_res
            else:
                 # Smoke failed, skip full
                 pass

        # 6. Construct Result
        
        # P0.2: Evidence Contract construction
        final_evidence = {
            "run_token": run_token,
            "evidence_path": str(evidence_dir),
            **evidence_map  # Flattened map (filename -> hash)
        }

        # Prepare result structures for schema matching
        smoke_block = _capture_to_dict(final_smoke)
        
        pytest_output = None
        if pytest_block:
            pytest_output = _capture_to_dict(pytest_block)

        outputs = {
            "run_token": run_token,
            "repo_root": str(context.repo_root),
            "baseline_commit": context.baseline_commit,
            "params_canonical_sha256": hashlib.sha256(canonical_params_json.encode("utf-8")).hexdigest(),
            "smoke": smoke_block,
            "pytest": pytest_output,
            "evidence_dir": str(evidence_dir),
            "evidence": final_evidence # Canonical shape
        }
        
        # 7. Validate Output Schema
        try:
            result_schema = self._load_schema(RESULT_SCHEMA_FILE)
            jsonschema.validate(instance=outputs, schema=result_schema)
        except Exception as e:
            return self._make_result(
                success=False,
                error=f"Internal Error: Result schema validation failed: {str(e)}",
                executed_steps=executed_steps
            )

        # 8. Determine Success
        success = (final_smoke.exit_code == 0)
        if pytest_block:
            success = success and (pytest_block.exit_code == 0)

        return self._make_result(
            success=success,
            outputs=outputs,
            executed_steps=executed_steps,
            evidence=final_evidence # Canonical source match
        )
