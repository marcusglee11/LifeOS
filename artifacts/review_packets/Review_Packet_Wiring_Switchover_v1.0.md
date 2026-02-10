# Review Packet Wiring Switchover v1.0

## Mission
P0 v2.1a Hard Switch-Over: Non-Bypassable Acceptance for `lifeos mission run` and `lifeos run-mission`.

## Scope
In scope:
1. `lifeos mission run`
2. `lifeos run-mission`

Out of scope:
1. `lifeos spine *`
2. non-mission commands/scripts
3. governance redesign
4. CI redesign
5. new dependencies
6. compatibility flags/modes

## Breaking Change
Mission CLI success semantics changed:
1. `success=true` and `exit 0` now require acceptance proof verification.
2. A mission run without valid acceptance token/record proof now fails closed (`success=false`, non-zero exit).
3. In `--json` mode, successful mission outputs now include mandatory proof fields:
   - `acceptance_token_path`
   - `acceptance_record_path`
   - `acceptance_token_sha256`
   - `evidence_manifest_sha256`

## Canonical Chokepoints
1. Canonical writer: `runtime/orchestration/orchestrator.py::ValidationOrchestrator.run()`
2. Canonical verifier/recorder: `runtime/validation/acceptor.py::accept()`
3. Accepted run definition: only runs with Acceptor-generated acceptance record derived from verified token.

## Pre-State Evidence (Verbatim)
Command: `git status --porcelain=v1`

```text
?? artifacts/validation_samples/v2.1a-p0/PRE_git_diff_name_only.txt
?? artifacts/validation_samples/v2.1a-p0/PRE_git_status_porcelain.txt
```

Command: `git diff --name-only`

```text
```

## Post-State Evidence (Verbatim)
Command: `git status --porcelain=v1`

```text
 M runtime/cli.py
 M runtime/tests/test_cli_mission.py
?? artifacts/Review_Packet_Wiring_Switchover_v1.0.md
?? artifacts/validation_samples/v2.1a-p0/WIRING_AUDIT_MAP.md
?? artifacts/validation_samples/v2.1a-p0/WIRING_SWITCHOVER_PYTEST_OUTPUT.txt
```

Command: `git diff --name-only`

```text
runtime/cli.py
runtime/tests/test_cli_mission.py
```

## Files Changed
1. `runtime/cli.py`
2. `runtime/tests/test_cli_mission.py`
3. `artifacts/validation_samples/v2.1a-p0/WIRING_AUDIT_MAP.md`
4. `artifacts/validation_samples/v2.1a-p0/WIRING_SWITCHOVER_PYTEST_OUTPUT.txt`

## Tests Executed
1. `pytest -v runtime/tests/orchestration/test_validation_orchestrator.py` (PASS)
2. `pytest -v runtime/tests/test_cli_mission.py` (PASS)

Verbatim output:
- `artifacts/validation_samples/v2.1a-p0/WIRING_SWITCHOVER_PYTEST_OUTPUT.txt`

## Verbatim Passing `--json` Mission Output Sample
Command context: `lifeos mission run echo --params '{"message":"sample"}' --json`

```json
{"acceptance_record_path":"/tmp/lifeos_sample_1k5t2ao_/repo/artifacts/validation_runs/69546b611c774995a878c05edbcb3237/attempt-0001/acceptance_record.json","acceptance_token_path":"/tmp/lifeos_sample_1k5t2ao_/repo/artifacts/validation_runs/69546b611c774995a878c05edbcb3237/attempt-0001/acceptance_token.json","acceptance_token_sha256":"8e4e5c46cc7b4a456286d8cb36c6016f4b9bff8d83ee8aff0349956751fd143b","attempt_id":"attempt-0001","attempt_index":1,"evidence_manifest_sha256":"377bed3a9eee52d47a4001515402126bc532b93a00c3832191914915c1ba2018","final_state":{"mission_result":{"error":null,"escalation_reason":null,"evidence":{},"executed_steps":[],"mission_type":"echo","outputs":{"message":"sample"},"success":true}},"id":"69546b611c774995a878c05edbcb3237","lineage":{"executed_step_ids":["echo-execute"],"workflow_id":"wf-echo"},"mission_type":"echo","receipt":{"id":"wf-echo","steps":["echo-execute"]},"success":true,"validation_run_id":"69546b611c774995a878c05edbcb3237"}
```

## Outcome
1. Both in-scope mission commands now route through trusted orchestrator + acceptor path.
2. Success emission is fail-closed on acceptance proof verification.
3. JSON success includes required acceptance proof fields.
4. Wiring audit AFTER map shows zero in-scope bypass paths.

## BLOCKED
No blockers encountered.

## Appendix A — Flattened Changed Files (Full Content, No Omissions)

### `runtime/cli.py`
```python
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
import subprocess
from typing import Any, Dict

from runtime.config import detect_repo_root, load_config
from runtime.orchestration.ceo_queue import CEOQueue
from runtime.orchestration.orchestrator import OrchestrationResult, ValidationOrchestrator
from runtime.validation.core import JobSpec
from runtime.validation.evidence import compute_manifest
from runtime.validation.reporting import sha256_file

def cmd_status(args: argparse.Namespace, repo_root: Path, config: dict | None, config_path: Path | None) -> int:
    """Print status of repo root, config, and validation."""
    print(f"repo_root: {repo_root}")
    if config_path:
        print(f"config_source: {config_path}")
        print("config_validation: VALID")
    else:
        print("config_source: NONE")
        print("config_validation: N/A")
    return 0

def cmd_config_validate(args: argparse.Namespace, repo_root: Path, config: dict | None, config_path: Path | None) -> int:
    """Validate the configuration and exit 0/1."""
    if not config_path:
        print("Error: No config file provided. Use --config <path>")
        return 1
    
    # If we reached here, load_config already passed in main()
    print("VALID")
    return 0

def cmd_config_show(args: argparse.Namespace, repo_root: Path, config: dict | None, config_path: Path | None) -> int:
    """Show the configuration in canonical JSON format."""
    if config is None:
        if config_path:
             # This shouldn't happen if main loaded it, but for safety:
             try:
                 config = load_config(config_path)
             except Exception as e:
                 print(f"Error: {e}")
                 return 1
        else:
            print("{}")
            return 0
            
    # Canonical JSON: sort_keys=True, no spaces in separators, no ASCII escape
    output = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    print(output)
    return 0

def cmd_mission_list(args: argparse.Namespace) -> int:
    """List all available mission types in sorted JSON."""
    # Local import

    # Get mission types from canonical registry (prefer registry keys over enum)
    try:
        from runtime.orchestration import registry
        if hasattr(registry, 'MISSION_REGISTRY'):
            mission_types = sorted(registry.MISSION_REGISTRY.keys())
        else:
            raise AttributeError
    except (ImportError, AttributeError):
        # Fallback: use MissionType enum
        from runtime.orchestration.missions.base import MissionType
        mission_types = sorted([mt.value for mt in MissionType])

    # Output canonical JSON (indent=2, sort_keys=True)
    output = json.dumps(mission_types, indent=2, sort_keys=True)
    print(output)
    return 0


def _canonical_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _baseline_commit(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=repo_root,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _mission_success(payload: Dict[str, Any]) -> bool:
    if "success" in payload:
        return bool(payload["success"])
    if payload.get("status") is not None:
        return payload.get("status") == "success"
    return False


def _extract_mission_result(result_dict: Dict[str, Any], mission_type: str) -> Dict[str, Any]:
    final_state = result_dict.get("final_state")
    if isinstance(final_state, dict):
        mission_result = final_state.get("mission_result")
        if isinstance(mission_result, dict):
            return mission_result

        mission_results = final_state.get("mission_results")
        if isinstance(mission_results, dict) and mission_results:
            first = next(iter(mission_results.values()))
            if isinstance(first, dict):
                extracted = dict(first)
                extracted.setdefault("mission_type", mission_type)
                extracted.setdefault("success", _mission_success(extracted))
                extracted.setdefault("outputs", extracted.get("outputs", {}))
                extracted.setdefault("evidence", extracted.get("evidence", {}))
                extracted.setdefault("executed_steps", extracted.get("executed_steps", []))
                extracted.setdefault("error", extracted.get("error"))
                return extracted

    return {
        "mission_type": mission_type,
        "success": _mission_success(result_dict),
        "outputs": result_dict.get("outputs", result_dict.get("output", {})),
        "evidence": result_dict.get("evidence", {}),
        "executed_steps": result_dict.get("executed_steps", []),
        "error": result_dict.get("error") or result_dict.get("error_message"),
    }


def _run_registry_mission(
    *,
    repo_root: Path,
    mission_type: str,
    mission_inputs: Dict[str, Any],
    initial_state: Dict[str, Any] | None = None,
    extra_metadata: Dict[str, Any] | None = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    from runtime.orchestration import registry
    from runtime.orchestration.engine import ExecutionContext

    metadata = {
        "repo_root": str(repo_root),
        "baseline_commit": _baseline_commit(repo_root),
        "cli_invocation": True,
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    ctx = ExecutionContext(
        initial_state=initial_state or {},
        metadata=metadata,
    )
    result = registry.run_mission(mission_type, ctx, mission_inputs)

    if hasattr(result, "to_dict"):
        result_dict = result.to_dict()
    elif isinstance(result, dict):
        result_dict = result
    else:
        result_dict = {"success": False, "error": "Invalid mission result type"}

    return result_dict, _extract_mission_result(result_dict, mission_type)


def _write_mission_attempt_evidence(
    *,
    attempt_dir: Path,
    mission_type: str,
    mission_inputs: Dict[str, Any],
    mission_result: Dict[str, Any],
) -> None:
    evidence_root = attempt_dir / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    meta_payload = {
        "schema_version": "mission_cli_attempt_meta_v1",
        "mission_type": mission_type,
        "mission_success": bool(mission_result.get("success")),
    }
    (evidence_root / "meta.json").write_text(
        json.dumps(meta_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (evidence_root / "exitcode.txt").write_text(
        "0\n" if mission_result.get("success") else "1\n",
        encoding="utf-8",
    )
    command_payload = {
        "operation": "mission",
        "mission_type": mission_type,
        "inputs_keys": sorted(mission_inputs.keys()),
    }
    (evidence_root / "commands.jsonl").write_text(
        json.dumps(command_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    compute_manifest(evidence_root)


def _verify_acceptance_proof(orchestration: OrchestrationResult) -> tuple[Dict[str, str | None], str | None]:
    proof: Dict[str, str | None] = {
        "acceptance_token_path": None,
        "acceptance_record_path": None,
        "acceptance_token_sha256": None,
        "evidence_manifest_sha256": None,
    }

    if not orchestration.acceptance_token_path:
        return proof, "Missing acceptance_token_path from orchestrator result"
    if not orchestration.acceptance_record_path:
        return proof, "Missing acceptance_record_path from orchestrator result"

    token_path = Path(orchestration.acceptance_token_path)
    record_path = Path(orchestration.acceptance_record_path)

    if not token_path.exists():
        return proof, f"Acceptance token missing on disk: {token_path}"
    if not record_path.exists():
        return proof, f"Acceptance record missing on disk: {record_path}"

    try:
        with open(record_path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
    except Exception as exc:
        return proof, f"Failed to read acceptance record: {exc}"

    if not isinstance(record, dict):
        return proof, "Acceptance record payload must be an object"
    if record.get("schema_version") != "acceptance_record_v1":
        return proof, "Acceptance record schema_version mismatch"
    if record.get("accepted") is not True:
        return proof, "Acceptance record is not marked accepted=true"

    required_record_fields = {
        "token_path",
        "manifest_path",
        "acceptance_token_sha256",
        "evidence_manifest_sha256",
    }
    missing = sorted(field for field in required_record_fields if not record.get(field))
    if missing:
        return proof, f"Acceptance record missing required fields: {missing}"

    record_token_path = Path(str(record["token_path"]))
    if record_token_path.resolve() != token_path.resolve():
        return proof, "Acceptance record token_path does not match orchestrator token path"

    token_sha = sha256_file(token_path)
    if token_sha != record["acceptance_token_sha256"]:
        return proof, "Acceptance token sha256 mismatch"

    manifest_path = Path(str(record["manifest_path"]))
    if not manifest_path.exists():
        return proof, f"Acceptance record manifest_path missing on disk: {manifest_path}"

    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != record["evidence_manifest_sha256"]:
        return proof, "Evidence manifest sha256 mismatch"

    proof["acceptance_token_path"] = str(token_path)
    proof["acceptance_record_path"] = str(record_path)
    proof["acceptance_token_sha256"] = token_sha
    proof["evidence_manifest_sha256"] = manifest_sha
    return proof, None


def _build_cli_mission_payload(
    *,
    mission_type: str,
    mission_result: Dict[str, Any],
    raw_result: Dict[str, Any],
    orchestration: OrchestrationResult | None,
    proof: Dict[str, str | None],
    success: bool,
    error: str | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": success,
        "id": orchestration.run_id if orchestration is not None else "mission-cli-exception",
        "lineage": raw_result.get("lineage") if isinstance(raw_result, dict) else None,
        "receipt": raw_result.get("receipt") if isinstance(raw_result, dict) else None,
        "final_state": {
            "mission_result": mission_result,
        },
        "acceptance_token_path": proof.get("acceptance_token_path"),
        "acceptance_record_path": proof.get("acceptance_record_path"),
        "acceptance_token_sha256": proof.get("acceptance_token_sha256"),
        "evidence_manifest_sha256": proof.get("evidence_manifest_sha256"),
    }
    if orchestration is not None:
        payload["validation_run_id"] = orchestration.run_id
        payload["attempt_id"] = orchestration.attempt_id
        payload["attempt_index"] = orchestration.attempt_index
        if orchestration.validator_report_path:
            payload["validator_report_path"] = orchestration.validator_report_path
    if error:
        payload["error"] = error
    payload["mission_type"] = mission_type
    return payload


def _run_mission_with_acceptance(
    *,
    repo_root: Path,
    mission_type: str,
    mission_inputs: Dict[str, Any],
    initial_state: Dict[str, Any] | None = None,
    extra_metadata: Dict[str, Any] | None = None,
) -> tuple[int, Dict[str, Any]]:
    mission_result: Dict[str, Any] = {
        "mission_type": mission_type,
        "success": False,
        "outputs": {},
        "evidence": {},
        "executed_steps": [],
        "error": "Mission did not execute",
    }
    raw_result: Dict[str, Any] = {}

    def _agent_runner(attempt_dir: Path, _job_spec: JobSpec) -> None:
        nonlocal mission_result, raw_result
        try:
            raw_result, mission_result = _run_registry_mission(
                repo_root=repo_root,
                mission_type=mission_type,
                mission_inputs=mission_inputs,
                initial_state=initial_state,
                extra_metadata=extra_metadata,
            )
        except Exception as exc:
            raw_result = {}
            mission_result = {
                "mission_type": mission_type,
                "success": False,
                "outputs": {},
                "evidence": {},
                "executed_steps": [],
                "error": f"{type(exc).__name__}: {exc}",
            }
        finally:
            _write_mission_attempt_evidence(
                attempt_dir=attempt_dir,
                mission_type=mission_type,
                mission_inputs=mission_inputs,
                mission_result=mission_result,
            )

    try:
        orchestration = ValidationOrchestrator(workspace_root=repo_root).run(
            mission_kind=mission_type,
            evidence_tier="light",
            agent_runner=_agent_runner,
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        payload = _build_cli_mission_payload(
            mission_type=mission_type,
            mission_result=mission_result,
            raw_result=raw_result,
            orchestration=None,
            proof={
                "acceptance_token_path": None,
                "acceptance_record_path": None,
                "acceptance_token_sha256": None,
                "evidence_manifest_sha256": None,
            },
            success=False,
            error=error,
        )
        return 1, payload

    proof, proof_error = _verify_acceptance_proof(orchestration)
    mission_ok = bool(mission_result.get("success"))

    acceptance_ok = (
        orchestration.success
        and proof_error is None
        and all(
            proof.get(key)
            for key in (
                "acceptance_token_path",
                "acceptance_record_path",
                "acceptance_token_sha256",
                "evidence_manifest_sha256",
            )
        )
    )
    success = mission_ok and acceptance_ok

    error = None
    if not acceptance_ok:
        error = proof_error or orchestration.message
    elif not mission_ok:
        error = str(mission_result.get("error") or "Mission execution failed")

    payload = _build_cli_mission_payload(
        mission_type=mission_type,
        mission_result=mission_result,
        raw_result=raw_result,
        orchestration=orchestration,
        proof=proof,
        success=success,
        error=error,
    )
    return (0 if success else 1), payload


def _emit_mission_result(
    *,
    mission_type: str,
    payload: Dict[str, Any],
    as_json: bool,
    header_lines: list[str] | None = None,
) -> int:
    success = bool(payload.get("success"))
    if as_json:
        print(_canonical_json(payload))
        return 0 if success else 1

    if header_lines:
        for line in header_lines:
            print(line)

    if success:
        print(f"Mission '{mission_type}' succeeded.")
        print(f"Acceptance record: {payload.get('acceptance_record_path')}")
    else:
        print(f"Mission '{mission_type}' failed: {payload.get('error', 'Unknown error')}", file=sys.stderr)
    return 0 if success else 1


def cmd_mission_run(args: argparse.Namespace, repo_root: Path) -> int:
    """Run a mission through trusted orchestrator + acceptor path."""
    inputs: Dict[str, Any] = {}

    if args.param:
        for param in args.param:
            if "=" not in param:
                payload = _build_cli_mission_payload(
                    mission_type=args.mission_type,
                    mission_result={
                        "mission_type": args.mission_type,
                        "success": False,
                        "outputs": {},
                        "evidence": {},
                        "executed_steps": [],
                        "error": f"Invalid parameter format '{param}'. Expected 'key=value'",
                    },
                    raw_result={},
                    orchestration=None,
                    proof={
                        "acceptance_token_path": None,
                        "acceptance_record_path": None,
                        "acceptance_token_sha256": None,
                        "evidence_manifest_sha256": None,
                    },
                    success=False,
                    error=f"Invalid parameter format '{param}'. Expected 'key=value'",
                )
                return _emit_mission_result(
                    mission_type=args.mission_type,
                    payload=payload,
                    as_json=args.json,
                )
            key, value = param.split("=", 1)
            inputs[key] = value

    if args.params:
        try:
            json_inputs = json.loads(args.params)
        except json.JSONDecodeError as exc:
            payload = _build_cli_mission_payload(
                mission_type=args.mission_type,
                mission_result={
                    "mission_type": args.mission_type,
                    "success": False,
                    "outputs": {},
                    "evidence": {},
                    "executed_steps": [],
                    "error": f"Invalid JSON in --params: {exc}",
                },
                raw_result={},
                orchestration=None,
                proof={
                    "acceptance_token_path": None,
                    "acceptance_record_path": None,
                    "acceptance_token_sha256": None,
                    "evidence_manifest_sha256": None,
                },
                success=False,
                error=f"Invalid JSON in --params: {exc}",
            )
            return _emit_mission_result(
                mission_type=args.mission_type,
                payload=payload,
                as_json=args.json,
            )
        if not isinstance(json_inputs, dict):
            payload = _build_cli_mission_payload(
                mission_type=args.mission_type,
                mission_result={
                    "mission_type": args.mission_type,
                    "success": False,
                    "outputs": {},
                    "evidence": {},
                    "executed_steps": [],
                    "error": "--params must be a JSON object (dict)",
                },
                raw_result={},
                orchestration=None,
                proof={
                    "acceptance_token_path": None,
                    "acceptance_record_path": None,
                    "acceptance_token_sha256": None,
                    "evidence_manifest_sha256": None,
                },
                success=False,
                error="--params must be a JSON object (dict)",
            )
            return _emit_mission_result(
                mission_type=args.mission_type,
                payload=payload,
                as_json=args.json,
            )
        inputs.update(json_inputs)

    _, payload = _run_mission_with_acceptance(
        repo_root=repo_root,
        mission_type=args.mission_type,
        mission_inputs=inputs,
        initial_state={},
        extra_metadata={"cli_command": "mission run"},
    )
    return _emit_mission_result(
        mission_type=args.mission_type,
        payload=payload,
        as_json=args.json,
    )


def cmd_run_mission(args: argparse.Namespace, repo_root: Path) -> int:
    """Run a mission from backlog via trusted orchestrator + acceptor path."""
    from runtime.backlog.synthesizer import SynthesisError, synthesize_mission

    task_id = args.from_backlog
    backlog_arg = Path(args.backlog) if args.backlog else Path("config/backlog.yaml")
    backlog_path = backlog_arg if backlog_arg.is_absolute() else repo_root / backlog_arg
    mission_type = args.mission_type if args.mission_type else "steward"

    try:
        packet = synthesize_mission(
            task_id=task_id,
            backlog_path=backlog_path,
            repo_root=repo_root,
            mission_type=mission_type,
        )
    except SynthesisError as exc:
        payload = _build_cli_mission_payload(
            mission_type=mission_type,
            mission_result={
                "mission_type": mission_type,
                "success": False,
                "outputs": {},
                "evidence": {},
                "executed_steps": [],
                "error": f"Synthesis failed: {exc}",
            },
            raw_result={},
            orchestration=None,
            proof={
                "acceptance_token_path": None,
                "acceptance_record_path": None,
                "acceptance_token_sha256": None,
                "evidence_manifest_sha256": None,
            },
            success=False,
            error=f"Synthesis failed: {exc}",
        )
        return _emit_mission_result(
            mission_type=mission_type,
            payload=payload,
            as_json=args.json,
        )

    mission_inputs = {
        "task_spec": packet.task_description,
        "context_refs": list(packet.context_refs),
    }
    initial_state = {
        "task_id": packet.task_id,
        "task_description": packet.task_description,
        "context_refs": list(packet.context_refs),
        "constraints": list(packet.constraints),
    }
    extra_metadata = {
        "packet_id": packet.packet_id,
        "priority": packet.priority,
        "cli_command": "run-mission",
    }

    _, payload = _run_mission_with_acceptance(
        repo_root=repo_root,
        mission_type=packet.mission_type,
        mission_inputs=mission_inputs,
        initial_state=initial_state,
        extra_metadata=extra_metadata,
    )
    payload["packet_id"] = packet.packet_id
    payload["task_id"] = packet.task_id

    header_lines = None
    if not args.json:
        header_lines = [
            "=== Mission Synthesis Engine ===",
            f"Task ID: {task_id}",
            f"Backlog: {backlog_path}",
            f"Mission Type: {mission_type}",
            "",
            f"Packet ID: {packet.packet_id}",
        ]

    return _emit_mission_result(
        mission_type=packet.mission_type,
        payload=payload,
        as_json=args.json,
        header_lines=header_lines,
    )

def cmd_queue_list(args: argparse.Namespace, repo_root: Path) -> int:
    """List pending escalations in JSON format."""
    queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
    pending = queue.get_pending()

    output = [
        {
            "id": e.id,
            "type": e.type.value,
            "age_hours": (datetime.utcnow() - e.created_at).total_seconds() / 3600,
            "summary": e.context.get("summary", "No summary"),
            "run_id": e.run_id,
        }
        for e in pending
    ]

    print(json.dumps(output, indent=2))
    return 0


def cmd_queue_show(args: argparse.Namespace, repo_root: Path) -> int:
    """Show full details of an escalation."""
    queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
    entry = queue.get_by_id(args.escalation_id)

    if entry is None:
        print(f"Error: Escalation {args.escalation_id} not found")
        return 1

    output = {
        "id": entry.id,
        "type": entry.type.value,
        "status": entry.status.value,
        "created_at": entry.created_at.isoformat(),
        "run_id": entry.run_id,
        "context": entry.context,
        "resolved_at": entry.resolved_at.isoformat() if entry.resolved_at else None,
        "resolution_note": entry.resolution_note,
        "resolver": entry.resolver,
    }

    print(json.dumps(output, indent=2))
    return 0


def cmd_queue_approve(args: argparse.Namespace, repo_root: Path) -> int:
    """Approve an escalation."""
    queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
    note = args.note if hasattr(args, 'note') and args.note else "Approved via CLI"

    result = queue.approve(args.escalation_id, note=note, resolver="CEO")

    if not result:
        print(f"Error: Could not approve {args.escalation_id}")
        return 1

    print(f"Approved: {args.escalation_id}")
    return 0


def cmd_queue_reject(args: argparse.Namespace, repo_root: Path) -> int:
    """Reject an escalation with reason."""
    queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")

    if not args.reason:
        print("Error: --reason is required for rejection")
        return 1

    result = queue.reject(args.escalation_id, reason=args.reason, resolver="CEO")

    if not result:
        print(f"Error: Could not reject {args.escalation_id}")
        return 1

    print(f"Rejected: {args.escalation_id}")
    return 0


def cmd_spine_run(args: argparse.Namespace, repo_root: Path) -> int:
    """
    Run Loop Spine with a task specification.

    Args:
        args: Parsed arguments with task_spec and optional run_id
        repo_root: Repository root path

    Returns:
        0 on success (PASS), 1 on failure (BLOCKED), 2 on checkpoint pause
    """
    from runtime.orchestration.loop.spine import LoopSpine
    from runtime.orchestration.run_controller import RepoDirtyError

    # Parse task spec (JSON file or inline JSON)
    task_spec_path = Path(args.task_spec)
    if task_spec_path.exists():
        with open(task_spec_path, 'r') as f:
            task_spec = json.load(f)
    else:
        # Try parsing as inline JSON
        try:
            task_spec = json.loads(args.task_spec)
        except json.JSONDecodeError:
            print(f"Error: task_spec must be a JSON file path or valid JSON string")
            return 1

    # Create spine instance
    spine = LoopSpine(repo_root=repo_root)

    try:
        # Run chain
        result = spine.run(task_spec=task_spec, resume_from=None)

        # Output result
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"Run ID: {result['run_id']}")
            print(f"State: {result['state']}")
            print(f"Outcome: {result.get('outcome', 'N/A')}")

            if result['state'] == 'CHECKPOINT':
                print(f"Checkpoint: {result.get('checkpoint_id')}")
                print("Execution paused. Use 'lifeos spine resume' to continue.")
                return 2
            elif result.get('outcome') == 'PASS':
                print(f"Commit: {result.get('commit_hash', 'N/A')}")
                return 0
            else:
                print(f"Reason: {result.get('reason', 'Unknown')}")
                return 1

    except RepoDirtyError as e:
        print(f"Error: Repository is dirty. Cannot proceed.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def cmd_spine_resume(args: argparse.Namespace, repo_root: Path) -> int:
    """
    Resume Loop Spine execution from a checkpoint.

    Args:
        args: Parsed arguments with checkpoint_id
        repo_root: Repository root path

    Returns:
        0 on success (PASS), 1 on failure (BLOCKED/error)
    """
    from runtime.orchestration.loop.spine import LoopSpine, PolicyChangedError, SpineError
    from runtime.orchestration.run_controller import RepoDirtyError

    # Create spine instance
    spine = LoopSpine(repo_root=repo_root)

    try:
        # Resume from checkpoint
        result = spine.resume(checkpoint_id=args.checkpoint_id)

        # Output result
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"Run ID: {result['run_id']}")
            print(f"State: {result['state']}")
            print(f"Outcome: {result.get('outcome', 'N/A')}")

            if result.get('outcome') == 'PASS':
                print(f"Commit: {result.get('commit_hash', 'N/A')}")
                return 0
            elif result.get('outcome') == 'BLOCKED':
                print(f"Reason: {result.get('reason')}")
                return 1
            else:
                return 1

    except PolicyChangedError as e:
        print(f"Error: Policy changed mid-run. Cannot resume.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1
    except RepoDirtyError as e:
        print(f"Error: Repository is dirty. Cannot proceed.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1
    except SpineError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def main() -> int:
    # Use a custom parser that handles global options before subcommands
    # This is achieved by defining them on the main parser.
    parser = argparse.ArgumentParser(
        prog="lifeos",
        description="LifeOS Runtime Tier-3 CLI",
        add_help=True
    )
    
    # Global --config flag
    parser.add_argument("--config", type=Path, help="Path to YAML config file")
    
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    
    # status command
    subparsers.add_parser("status", help="Show runtime status")
    
    # config group
    p_config = subparsers.add_parser("config", help="Configuration commands")
    config_subparsers = p_config.add_subparsers(dest="config_command", required=True)
    
    config_subparsers.add_parser("validate", help="Validate config file")
    config_subparsers.add_parser("show", help="Show config in canonical JSON")

    # mission group
    p_mission = subparsers.add_parser("mission", help="Mission commands")
    mission_subs = p_mission.add_subparsers(dest="mission_cmd", required=True)

    mission_subs.add_parser("list", help="List mission types")

    p_mission_run = mission_subs.add_parser("run", help="Run mission")
    p_mission_run.add_argument("mission_type", help="Mission type")
    p_mission_run.add_argument("--param", action="append", help="Parameter as key=value (legacy)")
    p_mission_run.add_argument("--params", help="Parameters as JSON string (P0.2)")
    p_mission_run.add_argument("--json", action="store_true", help="Output results as JSON")

    # queue group
    p_queue = subparsers.add_parser("queue", help="CEO approval queue commands")
    queue_subs = p_queue.add_subparsers(dest="queue_cmd", required=True)

    # queue list
    queue_subs.add_parser("list", help="List pending escalations")

    # queue show
    p_queue_show = queue_subs.add_parser("show", help="Show escalation details")
    p_queue_show.add_argument("escalation_id", help="Escalation ID (ESC-XXXX)")

    # queue approve
    p_queue_approve = queue_subs.add_parser("approve", help="Approve escalation")
    p_queue_approve.add_argument("escalation_id", help="Escalation ID")
    p_queue_approve.add_argument("--note", help="Approval note")

    # queue reject
    p_queue_reject = queue_subs.add_parser("reject", help="Reject escalation")
    p_queue_reject.add_argument("escalation_id", help="Escalation ID")
    p_queue_reject.add_argument("--reason", required=True, help="Rejection reason")

    # run-mission command
    p_run = subparsers.add_parser("run-mission", help="Run a mission from backlog")
    p_run.add_argument("--from-backlog", required=True, help="Task ID from backlog to execute")
    p_run.add_argument("--backlog", type=str, help="Path to backlog file (default: config/backlog.yaml)")
    p_run.add_argument("--mission-type", type=str, help="Mission type override (default: steward)")
    p_run.add_argument("--json", action="store_true", help="Output results as JSON")

    # spine group (Phase 4A0)
    p_spine = subparsers.add_parser("spine", help="Loop Spine (A1 Chain Controller) commands")
    spine_subs = p_spine.add_subparsers(dest="spine_cmd", required=True)

    # spine run
    p_spine_run = spine_subs.add_parser("run", help="Run a new chain execution")
    p_spine_run.add_argument("task_spec", help="Path to task spec JSON file or inline JSON string")
    p_spine_run.add_argument("--run-id", help="Optional run ID (generated if not provided)")
    p_spine_run.add_argument("--json", action="store_true", help="Output results as JSON")

    # spine resume
    p_spine_resume = spine_subs.add_parser("resume", help="Resume execution from checkpoint")
    p_spine_resume.add_argument("checkpoint_id", help="Checkpoint ID (e.g., CP_run_123_2)")
    p_spine_resume.add_argument("--json", action="store_true", help="Output results as JSON")

    # Parse args
    # Note: argparse by default allows flags before subcommands
    args = parser.parse_args()
    
    try:
        # P0.2 & P0.4 - Repo root detection
        repo_root = detect_repo_root()
        
        # Config loading
        config = None
        if args.config:
            config = load_config(args.config)
            
        # Dispatch
        if args.subcommand == "status":
            return cmd_status(args, repo_root, config, args.config)
        
        if args.subcommand == "config":
            if args.config_command == "validate":
                return cmd_config_validate(args, repo_root, config, args.config)
            if args.config_command == "show":
                return cmd_config_show(args, repo_root, config, args.config)

        if args.subcommand == "mission":
            if args.mission_cmd == "list":
                return cmd_mission_list(args)
            elif args.mission_cmd == "run":
                return cmd_mission_run(args, repo_root)

        if args.subcommand == "queue":
            if args.queue_cmd == "list":
                return cmd_queue_list(args, repo_root)
            elif args.queue_cmd == "show":
                return cmd_queue_show(args, repo_root)
            elif args.queue_cmd == "approve":
                return cmd_queue_approve(args, repo_root)
            elif args.queue_cmd == "reject":
                return cmd_queue_reject(args, repo_root)

        if args.subcommand == "run-mission":
            return cmd_run_mission(args, repo_root)

        if args.subcommand == "spine":
            if args.spine_cmd == "run":
                return cmd_spine_run(args, repo_root)
            elif args.spine_cmd == "resume":
                return cmd_spine_resume(args, repo_root)

    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### `runtime/tests/test_cli_mission.py`
```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

import pytest

from runtime.cli import cmd_mission_list, cmd_mission_run, cmd_run_mission
from runtime.orchestration.orchestrator import OrchestrationResult
from runtime.validation.acceptor import accept
from runtime.validation.core import JobSpec, RetryCaps
from runtime.validation.reporting import sha256_file, write_acceptance_token


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _setup_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    (repo / ".gitignore").write_text("artifacts/validation_runs/\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")

    config_dir = repo / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "backlog.yaml").write_text(
        """
schema_version: "1.0"
tasks:
  - id: TASK001
    description: Echo mission backlog task
    priority: P1
    context_hints: []
    constraints: []
""".strip()
        + "\n",
        encoding="utf-8",
    )

    _git(repo, "add", ".gitignore", "tracked.txt", "config/backlog.yaml")
    _git(repo, "commit", "-m", "init")
    return repo


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    return _setup_repo(tmp_path)


def _mission_run_args(params: str = "{}") -> argparse.Namespace:
    return argparse.Namespace(
        mission_type="echo",
        param=None,
        params=params,
        json=True,
    )


def _run_mission_args() -> argparse.Namespace:
    return argparse.Namespace(
        from_backlog="TASK001",
        backlog="config/backlog.yaml",
        mission_type="echo",
        json=True,
    )


def _assert_success_payload(payload: dict) -> None:
    required = (
        "acceptance_token_path",
        "acceptance_record_path",
        "acceptance_token_sha256",
        "evidence_manifest_sha256",
    )
    for field in required:
        assert field in payload
        assert isinstance(payload[field], str)
        assert payload[field]

    assert Path(payload["acceptance_token_path"]).exists()
    assert Path(payload["acceptance_record_path"]).exists()


def _fake_orchestrator_run(repo_root: Path, corruption: str):
    def _run(
        self,
        *,
        mission_kind: str,
        evidence_tier: str,
        agent_runner,
        run_id: str | None = None,
        gate_pipeline_version: str = "v2.1a-p0",
        retry_caps=None,
        receipt_required: bool = False,
    ) -> OrchestrationResult:
        _ = evidence_tier
        _ = retry_caps
        _ = receipt_required
        run_id = run_id or "fake-run"
        attempt_id = "attempt-0001"

        attempt_dir = repo_root / "artifacts" / "validation_runs" / run_id / attempt_id
        attempt_dir.mkdir(parents=True, exist_ok=True)

        job_spec = JobSpec(
            schema_version="job_spec_v1",
            run_id=run_id,
            mission_kind=mission_kind,
            evidence_tier="light",
            gate_pipeline_version=gate_pipeline_version,
            retry_caps=RetryCaps(2, 3, 2),
        )
        agent_runner(attempt_dir, job_spec)

        manifest_path = attempt_dir / "evidence" / "evidence_manifest.json"
        token_path = attempt_dir / "acceptance_token.json"

        token_payload = {
            "schema_version": "acceptance_token_v1",
            "pass": True,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "attempt_index": 1,
            "gate_pipeline_version": gate_pipeline_version,
            "evidence_manifest_sha256": sha256_file(manifest_path),
            "receipt_sha256": None,
            "created_at": "2026-02-10T00:00:00+00:00",
            "provenance": {
                "minted_by": "runtime.tests.test_cli_mission",
                "attempt_dir": str(attempt_dir),
                "manifest_path": str(manifest_path),
                "receipt_path": str(attempt_dir / "receipt.json"),
            },
        }
        write_acceptance_token(token_path, token_payload)
        accept(token_path)

        record_path = attempt_dir / "acceptance_record.json"

        if corruption == "missing_record":
            record_path.unlink()
        elif corruption == "missing_token":
            token_path.unlink()
        elif corruption == "tampered_token":
            tampered_payload = json.loads(token_path.read_text(encoding="utf-8"))
            tampered_payload["pass"] = False
            token_path.write_text(json.dumps(tampered_payload, sort_keys=True), encoding="utf-8")
        elif corruption == "missing_record_path":
            return OrchestrationResult(
                success=True,
                run_id=run_id,
                attempt_id=attempt_id,
                attempt_index=1,
                message="Accepted",
                acceptance_token_path=str(token_path),
                acceptance_record_path=None,
            )

        return OrchestrationResult(
            success=True,
            run_id=run_id,
            attempt_id=attempt_id,
            attempt_index=1,
            message="Accepted",
            acceptance_token_path=str(token_path),
            acceptance_record_path=str(record_path),
        )

    return _run


class TestMissionCLI:
    def test_mission_list_returns_sorted_json(self, capsys):
        ret = cmd_mission_list(None)
        assert ret == 0

        output = json.loads(capsys.readouterr().out)
        assert isinstance(output, list)
        assert output == sorted(output)
        assert "echo" in output

    def test_mission_run_json_success_includes_acceptance_proof(self, temp_repo: Path, capsys):
        ret = cmd_mission_run(_mission_run_args('{"message":"hello"}'), temp_repo)
        assert ret == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["success"] is True
        assert payload["final_state"]["mission_result"]["success"] is True
        _assert_success_payload(payload)

    def test_run_mission_json_success_includes_acceptance_proof(self, temp_repo: Path, capsys):
        ret = cmd_run_mission(_run_mission_args(), temp_repo)
        assert ret == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["success"] is True
        assert payload["final_state"]["mission_result"]["success"] is True
        _assert_success_payload(payload)

    @pytest.mark.parametrize("command", ["mission_run", "run_mission"])
    @pytest.mark.parametrize("corruption", ["missing_record", "missing_token", "tampered_token"])
    def test_commands_fail_closed_when_proof_invalid(
        self,
        temp_repo: Path,
        capsys,
        monkeypatch: pytest.MonkeyPatch,
        command: str,
        corruption: str,
    ):
        monkeypatch.setattr(
            "runtime.cli.ValidationOrchestrator.run",
            _fake_orchestrator_run(temp_repo, corruption),
        )

        if command == "mission_run":
            ret = cmd_mission_run(_mission_run_args('{"message":"hello"}'), temp_repo)
        else:
            ret = cmd_run_mission(_run_mission_args(), temp_repo)

        assert ret == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["success"] is False

    @pytest.mark.parametrize("command", ["mission_run", "run_mission"])
    def test_commands_fail_closed_without_acceptance_record_path(
        self,
        temp_repo: Path,
        capsys,
        monkeypatch: pytest.MonkeyPatch,
        command: str,
    ):
        monkeypatch.setattr(
            "runtime.cli.ValidationOrchestrator.run",
            _fake_orchestrator_run(temp_repo, "missing_record_path"),
        )

        if command == "mission_run":
            ret = cmd_mission_run(_mission_run_args('{"message":"hello"}'), temp_repo)
        else:
            ret = cmd_run_mission(_run_mission_args(), temp_repo)

        assert ret == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["success"] is False
        assert payload.get("acceptance_record_path") is None
```

### `artifacts/validation_samples/v2.1a-p0/WIRING_AUDIT_MAP.md`
```markdown
# Wiring Audit Map — v2.1a P0 Mission CLI Acceptance Enforcement

## Scope
In scope mission entrypoints:
1. `lifeos mission run`
2. `lifeos run-mission`

Out of scope:
1. `lifeos spine *`
2. non-mission commands
3. non-mission scripts

## Pre-State Evidence (Verbatim)
Command: `git status --porcelain=v1`

```text
?? artifacts/validation_samples/v2.1a-p0/PRE_git_diff_name_only.txt
?? artifacts/validation_samples/v2.1a-p0/PRE_git_status_porcelain.txt
```

Command: `git diff --name-only`

```text

```

## Invocation Surfaces (In Scope)
| Surface | Source | Path |
|---|---|---|
| Console script `lifeos` | `pyproject.toml` `[project.scripts]` | `lifeos = "runtime.cli:main"` |
| Console script `coo` | `pyproject.toml` `[project.scripts]` | `coo = "runtime.cli:main"` |
| Module entrypoint | `runtime/__main__.py` | `python -m runtime -> runtime.cli.main()` |
| CLI dispatch route 1 | `runtime/cli.py` | `main() -> subcommand mission/run -> cmd_mission_run()` |
| CLI dispatch route 2 | `runtime/cli.py` | `main() -> subcommand run-mission -> cmd_run_mission()` |

## CI Workflow Scan (Direct Invocation of In-Scope Commands)
Scan target: `.github/workflows/*`

Patterns scanned:
1. `lifeos mission run`
2. `lifeos run-mission`
3. `python -m runtime` with mission command

Result: **none found** (no direct in-scope mission command invocation in workflow files).

## Acceptance/Success Emitters and Transitions
| Component | Function | Role |
|---|---|---|
| `runtime/orchestration/orchestrator.py` | `ValidationOrchestrator.run()` | canonical orchestration flow with gate + acceptor call |
| `runtime/validation/acceptor.py` | `accept()` | canonical token verification + acceptance record writer |
| `runtime/cli.py` | `cmd_mission_run()` | mission result JSON builder + exit emitter |
| `runtime/cli.py` | `cmd_run_mission()` | mission status print + exit emitter |

## BEFORE Map (Entrypoint -> Call Chain -> Success Emitter)
| Entrypoint | Call Chain (BEFORE) | Success Emitter(s) |
|---|---|---|
| `lifeos mission run` (also via `coo` and `python -m runtime`) | `runtime.cli.main()` -> `cmd_mission_run()` -> `registry.run_mission()` OR direct fallback mission execution -> local wrapper synthesis in `cmd_mission_run()` | `cmd_mission_run()` emits JSON with `success` and returns exit code from local success logic (no acceptance proof gate) |
| `lifeos run-mission` (also via `coo` and `python -m runtime`) | `runtime.cli.main()` -> `cmd_run_mission()` -> `synthesize_mission()` -> `execute_mission()` -> `registry.run_mission()` | `cmd_run_mission()` prints `Status: SUCCESS` and returns `0` from `result.get('success')` (no acceptance proof gate) |

## Explicit In-Scope Bypass Risks (BEFORE)
1. `cmd_mission_run()` can emit `success=true` and return `0` without `ValidationOrchestrator.run()` and without acceptance record verification.
2. `cmd_run_mission()` can return `0` on mission success without acceptance token verification and without acceptance record existence.
3. Mission success in both in-scope commands is currently tied to mission completion status, not canonical acceptance state.

## Canonical Chokepoint Decision (LOCK)
1. Canonical acceptance writer: `runtime/orchestration/orchestrator.py::ValidationOrchestrator.run()`
2. Canonical verifier/recorder: `runtime/validation/acceptor.py::accept()`
3. Accepted run definition: run is accepted only if Acceptor verifies token and writes `acceptance_record.json` derived from that verified token.
4. Legacy mission success emitters in `runtime/cli.py` that bypass the canonical acceptance flow are deprecated and must be removed from in-scope paths.

## AFTER Map (Post-Switchover)
| Entrypoint | Call Chain (AFTER) | Success Emitter(s) |
|---|---|---|
| `lifeos mission run` (also via `coo` and `python -m runtime`) | `runtime.cli.main()` -> `cmd_mission_run()` -> `_run_mission_with_acceptance()` -> `ValidationOrchestrator.run()` -> `GateRunner.run_postflight()` token mint -> `accept()` acceptance record mint -> `_verify_acceptance_proof()` -> `_emit_mission_result()` | `_emit_mission_result()` can return exit `0` only when payload `success=true`, where payload `success` is gated by mission success **and** verified acceptance record proof |
| `lifeos run-mission` (also via `coo` and `python -m runtime`) | `runtime.cli.main()` -> `cmd_run_mission()` -> `synthesize_mission()` -> `_run_mission_with_acceptance()` -> `ValidationOrchestrator.run()` -> `GateRunner.run_postflight()` token mint -> `accept()` acceptance record mint -> `_verify_acceptance_proof()` -> `_emit_mission_result()` | `_emit_mission_result()` can return exit `0` only when payload `success=true`, where payload `success` is gated by mission success **and** verified acceptance record proof |

## Acceptance Proof Contract (AFTER)
For `--json` success (`success=true`) both commands now emit:
1. `acceptance_token_path`
2. `acceptance_record_path`
3. `acceptance_token_sha256`
4. `evidence_manifest_sha256`

Proof gate now validates:
1. token path exists
2. acceptance record path exists
3. acceptance record schema and accepted flag
4. record token path matches emitted token path
5. token sha256 matches record
6. evidence manifest exists and sha256 matches record

Any failed check forces fail-closed: `success=false`, non-zero exit.

## In-Scope Bypass Risk Status (AFTER)
1. Prior `cmd_mission_run()` local success emitter bypass is removed from in-scope path.
2. Prior `cmd_run_mission()` direct status-based success emitter bypass is removed from in-scope path.
3. In-scope mission command success now converges on canonical chokepoints (`ValidationOrchestrator.run()` + `accept()`).
4. **Zero in-scope bypass paths identified** from repository evidence after switchover.

## Blockers
None.
```

### `artifacts/validation_samples/v2.1a-p0/WIRING_SWITCHOVER_PYTEST_OUTPUT.txt`
```text
$ pytest -v runtime/tests/orchestration/test_validation_orchestrator.py
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /mnt/c/Users/cabra/Projects/LifeOS
configfile: pyproject.toml
plugins: anyio-4.12.1
collecting ... collected 5 items

runtime/tests/orchestration/test_validation_orchestrator.py::test_orchestrator_success_path PASSED [ 20%]
runtime/tests/orchestration/test_validation_orchestrator.py::test_orchestrator_preflight_failure_is_terminal PASSED [ 40%]
runtime/tests/orchestration/test_validation_orchestrator.py::test_orchestrator_owns_retry_loop PASSED [ 60%]
runtime/tests/orchestration/test_validation_orchestrator.py::test_orchestrator_detects_job_spec_tamper_as_terminal PASSED [ 80%]
runtime/tests/orchestration/test_validation_orchestrator.py::test_retry_cap_boundary_stops_at_second_failure PASSED [100%]

============================== 5 passed in 2.11s ===============================

$ pytest -v runtime/tests/test_cli_mission.py
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /mnt/c/Users/cabra/Projects/LifeOS
configfile: pyproject.toml
plugins: anyio-4.12.1
collecting ... collected 11 items

runtime/tests/test_cli_mission.py::TestMissionCLI::test_mission_list_returns_sorted_json PASSED [  9%]
runtime/tests/test_cli_mission.py::TestMissionCLI::test_mission_run_json_success_includes_acceptance_proof PASSED [ 18%]
runtime/tests/test_cli_mission.py::TestMissionCLI::test_run_mission_json_success_includes_acceptance_proof PASSED [ 27%]
runtime/tests/test_cli_mission.py::TestMissionCLI::test_commands_fail_closed_when_proof_invalid[missing_record-mission_run] PASSED [ 36%]
runtime/tests/test_cli_mission.py::TestMissionCLI::test_commands_fail_closed_when_proof_invalid[missing_record-run_mission] PASSED [ 45%]
runtime/tests/test_cli_mission.py::TestMissionCLI::test_commands_fail_closed_when_proof_invalid[missing_token-mission_run] PASSED [ 54%]
runtime/tests/test_cli_mission.py::TestMissionCLI::test_commands_fail_closed_when_proof_invalid[missing_token-run_mission] PASSED [ 63%]
runtime/tests/test_cli_mission.py::TestMissionCLI::test_commands_fail_closed_when_proof_invalid[tampered_token-mission_run] PASSED [ 72%]
runtime/tests/test_cli_mission.py::TestMissionCLI::test_commands_fail_closed_when_proof_invalid[tampered_token-run_mission] PASSED [ 81%]
runtime/tests/test_cli_mission.py::TestMissionCLI::test_commands_fail_closed_without_acceptance_record_path[mission_run] PASSED [ 90%]
runtime/tests/test_cli_mission.py::TestMissionCLI::test_commands_fail_closed_without_acceptance_record_path[run_mission] PASSED [100%]

============================== 11 passed in 2.81s ==============================
```
