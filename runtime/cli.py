import argparse
import sys
import json
from pathlib import Path

from runtime.config import detect_repo_root, load_config

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


def cmd_mission_run(args: argparse.Namespace, repo_root: Path) -> int:
    """
    Run a mission with specified parameters.

    Returns:
        0 on success, 1 on failure
    """
    # Local imports
    import uuid
    import subprocess

    # Parse --param flags into inputs dict
    inputs = {}
    if args.param:
        for param in args.param:
            if "=" not in param:
                print(f"Error: Invalid parameter format '{param}'. Expected 'key=value'")
                return 1
            key, value = param.split("=", 1)
            inputs[key] = value

    try:
        # Detect git context
        baseline_commit = None
        try:
            cmd_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
                cwd=repo_root
            )
            if cmd_result.returncode == 0:
                baseline_commit = cmd_result.stdout.strip()
        except Exception:
            pass  # Fail-soft

        # Try registry path first (preferred)
        try:
            from runtime.orchestration import registry
            from runtime.orchestration.engine import ExecutionContext

            # CRITICAL (E4): Create proper ExecutionContext (empty state, metadata for git context)
            ctx = ExecutionContext(
                initial_state={},
                metadata={"repo_root": str(repo_root), "baseline_commit": baseline_commit, "cli_invocation": True}
            )
            result = registry.run_mission(args.mission_type, ctx, inputs)

            # Extract result dict (prefer to_dict)
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {'success': False, 'error': 'Invalid result format'}

            # Determine success (same logic as engine.py)
            if 'success' in result_dict:
                success = bool(result_dict['success'])
            elif result_dict.get('status') is not None:
                success = (result_dict['status'] == 'success')
            else:
                success = False
        except (ImportError, AttributeError):
            # Fall back to direct mission execution
            from runtime.orchestration.missions import get_mission_class, MissionContext

            mission_class = get_mission_class(args.mission_type)
            mission = mission_class()

            # Optional validation
            if hasattr(mission, 'validate_inputs'):
                mission.validate_inputs(inputs)

            # Create MissionContext and execute
            context = MissionContext(
                repo_root=repo_root,
                baseline_commit=baseline_commit,
                run_id=str(uuid.uuid4()),
                operation_executor=None,
                journal=None,
                metadata={"cli_invocation": True}
            )

            result = mission.run(context, inputs)

            # Normalize result (same as registry path)
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {
                    'success': bool(getattr(result, 'success', False)),
                    'status': getattr(result, 'status', None),
                    'output': getattr(result, 'output', None),
                    'error': getattr(result, 'error', None)
                }

            # Determine success (same logic as engine.py)
            if 'success' in result_dict:
                success = bool(result_dict['success'])
            elif result_dict.get('status') is not None:
                success = (result_dict['status'] == 'success')
            else:
                success = False

        # Output canonical JSON (indent=2, sort_keys=True per instruction block)
        output = json.dumps(result_dict, indent=2, sort_keys=True)
        print(output)

        return 0 if success else 1

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return 1


def cmd_run_mission(args: argparse.Namespace, repo_root: Path) -> int:
    """Run a mission from backlog via orchestrator."""
    from runtime.backlog.synthesizer import synthesize_mission, execute_mission, SynthesisError
    
    task_id = args.from_backlog
    backlog_path = repo_root / (args.backlog if args.backlog else "config/backlog.yaml")
    mission_type = args.mission_type if args.mission_type else "steward"
    
    print(f"=== Mission Synthesis Engine ===")
    print(f"Task ID: {task_id}")
    print(f"Backlog: {backlog_path}")
    print(f"Mission Type: {mission_type}")
    print()
    
    # Step 1: Synthesize mission packet
    try:
        print("Step 1: Synthesizing mission packet...")
        packet = synthesize_mission(
            task_id=task_id,
            backlog_path=backlog_path,
            repo_root=repo_root,
            mission_type=mission_type,
        )
        print(f"  packet_id: {packet.packet_id}")
        print(f"  task_description: {packet.task_description[:80]}...")
        print(f"  context_refs: {len(packet.context_refs)} files")
        print(f"  constraints: {len(packet.constraints)}")
        print()
    except SynthesisError as e:
        print(f"ERROR: Synthesis failed: {e}")
        return 1
    
    # Step 2: Execute via orchestrator
    try:
        print("Step 2: Executing mission via orchestrator...")
        result = execute_mission(packet, repo_root)
        print(f"  success: {result.get('success', False)}")
        print(f"  mission_type: {result.get('mission_type')}")
        print()
    except SynthesisError as e:
        print(f"ERROR: Execution failed: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected execution error: {e}")
        return 1
    
    # Step 3: Report results
    print("=== Mission Complete ===")
    print(f"Packet ID: {packet.packet_id}")
    if result.get('success'):
        print("Status: SUCCESS")
        return 0
    else:
        print("Status: FAILED")
        return 1

def main() -> int:
    # Use a custom parser that handles global options before subcommands
    # This is achieved by defining them on the main parser.
    parser = argparse.ArgumentParser(
        prog="runtime",
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
    p_mission_run.add_argument("--param", action="append", help="Parameter as key=value")

    # run-mission command
    p_run = subparsers.add_parser("run-mission", help="Run a mission from backlog")
    p_run.add_argument("--from-backlog", required=True, help="Task ID from backlog to execute")
    p_run.add_argument("--backlog", type=str, help="Path to backlog file (default: config/backlog.yaml)")
    p_run.add_argument("--mission-type", type=str, help="Mission type override (default: steward)")
    
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

        if args.subcommand == "run-mission":
            return cmd_run_mission(args, repo_root)
                
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())