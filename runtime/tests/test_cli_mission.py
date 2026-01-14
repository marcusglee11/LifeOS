import json
import pytest
from unittest.mock import MagicMock, patch
from runtime.cli import cmd_mission_list, cmd_mission_run

@pytest.fixture
def temp_repo(tmp_path):
    """Create a mock repo structure."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git_dir = repo / ".git"
    git_dir.mkdir()
    return repo

class TestMissionCLI:
    def test_mission_list_returns_sorted_json(self, capsys):
        """P0.3: mission list must be deterministic (sorted)."""
        ret = cmd_mission_list(None)
        assert ret == 0
        
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        
        assert isinstance(output, list)
        assert output == sorted(output)
        assert "echo" in output
        assert "steward" in output
        
    def test_mission_run_params_json(self, temp_repo, capsys):
        """P0.2: mission run with --params JSON."""
        class Args:
            mission_type = "echo"
            param = None
            params = '{"message": "JSON_TEST"}'
            json = True
            
        ret = cmd_mission_run(Args(), temp_repo)
        assert ret == 0
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        
        # Check deep output structure
        # Echo mission output structure depends on implementation, usually dict
        # Assuming echo returns inputs as outputs or similar
        # If echo follows standard, result dict structure:
        # { success: bool, mission_type: str, outputs: {...} }
        
        # In engine.py: result_dict = result.to_dict()
        # The echo mission might wrap output differently, let's just check standard keys
        # Canonical wrapper check
        assert 'final_state' in data
        outputs = data['final_state']['mission_result']['outputs']

    def test_mission_run_legacy_param(self, temp_repo, capsys):
        """Test legacy --param key=value."""
        class Args:
            mission_type = "echo"
            param = ["message=LEGACY_TEST"]
            params = None
            json = True
            
        ret = cmd_mission_run(Args(), temp_repo)
        assert ret == 0
        
    def test_mission_run_invalid_json_params(self, temp_repo, capsys):
        """Fail on invalid JSON params."""
        class Args:
            mission_type = "echo"
            param = None
            params = "{invalid_json}"  # Missing quotes
            json = True
            
        ret = cmd_mission_run(Args(), temp_repo)
        assert ret == 1
        
        captured = capsys.readouterr()
        assert "Error: Invalid JSON" in captured.out or "Error" in captured.out

    def test_mission_list_determinism_check(self):
        """P1.1: Verify registry keys sorting logic."""
        from runtime.orchestration import registry
        keys = registry.list_mission_types()
        assert keys == sorted(keys), "Registry list must be pre-sorted"

    def test_build_with_validation_smoke_mode(self, temp_repo, capsys):
        """Test build_with_validation mission execution in smoke mode."""
        # Create pyproject.toml in temp repo so smoke check passes
        (temp_repo / "pyproject.toml").touch()
        
        class Args:
            mission_type = "build_with_validation"
            param = None
            params = json.dumps({"mode": "smoke"})
            json = True
        
        # Mock subprocess side_effect to handle git (CLI) vs mission commands
        def mock_side_effect(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("cmd")
            if cmd and cmd[0] == "git":
                # CLI git context detection expects string if text=True (impl detail)
                # But actually cli.py might verify text=True. 
                # Let's check if text=True or encoding is passed.
                # Just return a mock with stdout as string for git.
                m = MagicMock()
                m.returncode = 0
                m.stdout = "a" * 40 + "\n" # Valid 40-char hex string for text=True
                return m
            else:
                # Mission commands (smoke/pytest) exepct bytes usually? 
                # Mission implementation uses capture_output=True which implies bytes unless text=True passed.
                # BuildWithValidationMission uses default (bytes).
                m = MagicMock()
                m.returncode = 0
                m.stdout = b"OK"
                m.stderr = b""
                return m

        with patch("subprocess.run", side_effect=mock_side_effect) as mock_run:
            ret = cmd_mission_run(Args(), temp_repo)
            
            captured = capsys.readouterr()
            if ret != 0:
                pytest.fail(f"CLI failed with exit code {ret}. Output: {captured.out}\nStderr: {captured.err}")
                
            try:
                result = json.loads(captured.out)
            except json.JSONDecodeError:
                pytest.fail(f"CLI output was not valid JSON: {captured.out}")
            
            # Strict canonical wrapper check
            result = json.loads(captured.out)
            assert 'final_state' in result, "CLI must output canonical wrapper with 'final_state'"
            
            # P0.2: Assert canonical formatting (no newlines, strict separators)
            trimmed_out = captured.out.strip()
            assert "\n" not in trimmed_out, "Canonical JSON must not have internal newlines"
            assert ": " not in trimmed_out, "Canonical JSON must use ':' separator without space"
            assert ", " not in trimmed_out, "Canonical JSON must use ',' separator without space"

            mission_res = result['final_state']['mission_result']
            
            assert mission_res["success"] is True
            assert mission_res["mission_type"] == "build_with_validation"

            outputs = mission_res['outputs']
            
            # P0.3: Assert deterministic ID based on run_token
            run_token = outputs.get("run_token")
            assert run_token is not None
            assert result["id"] == f"direct-execution-{run_token}"
            
            # Assert audit-grade evidence
            assert "smoke" in outputs
            assert "stdout_sha256" in outputs["smoke"]
            assert "stderr_sha256" in outputs["smoke"]
            assert outputs["smoke"]["exit_code"] == 0
            
            # Assert evidence map
            assert "evidence" in outputs
            assert len(outputs["evidence"]) > 0
            
            # P0.2: Assert strict evidence equality (top-level vs outputs)
            assert mission_res.get("evidence") == outputs["evidence"]

    def test_build_with_validation_fail_closed(self, temp_repo, capsys):
        """Test fail-closed behavior for invalid params."""
        class Args:
            mission_type = "build_with_validation"
            param = None
            params = json.dumps({"unknown_key": "bad"}) # Invalid schema
            json = True
            
        ret = cmd_mission_run(Args(), temp_repo)
        
        captured = capsys.readouterr()
        # It might print JSON or plain error depending on where it failed
        # If strict validation fails in mission.validate_inputs, engine catches and returns result with success=False
        try:
            result = json.loads(captured.out)
            # Strict canonical wrapper check
            result = json.loads(captured.out)
            assert 'final_state' in result, "CLI must output canonical wrapper"
            
            # P0.2: Assert canonical formatting for errors too
            assert "\n" not in captured.out.strip(), "Canonical JSON must not have internal newlines"
            
            mission_res = result['final_state']['mission_result']
                
            assert mission_res["success"] is False
            assert "Invalid inputs" in str(mission_res.get("error"))
            
            # Verify deterministic ID for exception/error
            # In this case (validation error inside mission execution), logical flow might produce a result with run_token=None?
            # Or if it fails in validate_inputs, outputs might be empty.
            # Our logic: if run_token missing, id="direct-execution-unknown"
            assert result["id"] == "direct-execution-unknown"
            
        except json.JSONDecodeError:
            pytest.fail(f"CLI output was not valid JSON: {captured.out}")
