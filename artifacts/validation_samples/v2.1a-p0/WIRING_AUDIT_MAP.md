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
