
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from runtime.orchestration.engine import Orchestrator, StepSpec, ExecutionContext
from runtime.orchestration.missions.base import MissionContext

def test_engine_mission_context_construction():
    """Verify engine constructs MissionContext with correct arguments."""
    
    # Mock _detect_git_context to return known values
    known_repo_root = Path("/tmp/mock_repo")
    known_commit = "commit_123"
    
    orchestrator = Orchestrator()
    orchestrator._detect_git_context = MagicMock(return_value=(known_repo_root, known_commit))
    
    # Mock mission class so we can inspect call args
    mock_mission = MagicMock()
    mock_mission_class = MagicMock(return_value=mock_mission)
    
    # Patch get_mission_class to return our mock
    with patch("runtime.orchestration.missions.get_mission_class", return_value=mock_mission_class):
        
        step = StepSpec(id="step1", kind="runtime", payload={"operation": "mission", "mission_type": "mock_mission"})
        state = {}
        ctx = ExecutionContext()
        
        # Execute
        orchestrator._execute_mission(step, state, ctx)
        
        # Verify MissionContext was created correctly
        # The engine instantiates MissionContext and passes it to mission.run(context, inputs)
        assert mock_mission.run.called
        call_args = mock_mission.run.call_args
        passed_context = call_args[0][0] # First arg is context
        
        assert isinstance(passed_context, MissionContext)
        assert passed_context.repo_root == known_repo_root
        assert passed_context.baseline_commit == known_commit
        assert passed_context.repo_root != passed_context.baseline_commit # Verify not swapped values if they were same types (but they aren't)

def test_cli_mission_context_construction():
    """Verify CLI constructs MissionContext correctly (fallback path)."""
    from runtime.cli import cmd_mission_run
    
    class Args:
        mission_type = "mock_mission"
        param = None
        params = None
        json = True
        
    repo_root = Path("/tmp/cli_repo")
    
    # Patch inputs to force fallback path and capture context
    with patch("runtime.cli.subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0, stdout="cli_commit_456")
        
        # Force fallback by raising ImportError on registry
        with patch.dict("sys.modules", {"runtime.orchestration.registry": None}):
             # Mock get_mission_class
             mock_mission = MagicMock()
             mock_mission_class = MagicMock(return_value=mock_mission)
             
             with patch("runtime.orchestration.missions.get_mission_class", return_value=mock_mission_class):
                 cmd_mission_run(Args(), repo_root)
                 
                 assert mock_mission.run.called
                 passed_context = mock_mission.run.call_args[0][0]
                 
                 assert passed_context.repo_root == repo_root
                 assert passed_context.baseline_commit == "cli_commit_456"

if __name__ == "__main__":
    test_engine_mission_context_construction()
    test_cli_mission_context_construction()
    print("MissionContext construction verified.")
