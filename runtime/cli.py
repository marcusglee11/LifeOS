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
        
        if args.subcommand == "run-mission":
            return cmd_run_mission(args, repo_root)
                
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())