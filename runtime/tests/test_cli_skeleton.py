import os
import json
import pytest
from pathlib import Path
from runtime.config import detect_repo_root, load_config, verify_containment
from runtime.cli import main
from unittest.mock import patch

@pytest.fixture
def temp_repo(tmp_path):
    """Create a mock repo structure."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git_dir = repo / ".git"
    git_dir.mkdir()
    return repo

class TestRepoRootDetection:
    def test_detect_repo_root_git_dir(self, temp_repo):
        """Should find repo root with .git directory."""
        subdir = temp_repo / "a" / "b"
        subdir.mkdir(parents=True)
        assert detect_repo_root(start_path=subdir) == temp_repo

    def test_detect_repo_root_git_file(self, tmp_path):
        """Should find repo root with .git file (worktree support)."""
        repo_root = tmp_path / "worktree_root"
        repo_root.mkdir()
        git_file = repo_root / ".git"
        git_file.write_text("gitdir: /path/to/main/repo/.git/worktrees/wt1")
        
        subdir = repo_root / "src"
        subdir.mkdir()
        
        assert detect_repo_root(start_path=subdir) == repo_root

    def test_detect_repo_root_no_marker_fails(self, tmp_path):
        """Should fail closed when no .git marker is found."""
        with pytest.raises(RuntimeError) as excinfo:
            detect_repo_root(start_path=tmp_path, max_depth=5)
        assert "Fail-closed: Repo root not found" in str(excinfo.value)

    def test_detect_repo_root_max_depth(self, tmp_path):
        """Should fail closed if max_depth is exceeded."""
        root = tmp_path / "root"
        root.mkdir()
        (root / ".git").mkdir()
        
        current = root
        for i in range(10):
            current = current / f"level_{i}"
            current.mkdir()
            
        with pytest.raises(RuntimeError):
            detect_repo_root(start_path=current, max_depth=5)

class TestPathContainment:
    def test_verify_containment_success(self, temp_repo):
        """Should allow paths inside repo root."""
        inside = temp_repo / "docs" / "file.md"
        assert verify_containment(inside, temp_repo) is True
        
    def test_verify_containment_failure(self, temp_repo, tmp_path):
        """Should reject paths outside repo root."""
        outside = tmp_path / "other_repo" / "secret.txt"
        assert verify_containment(outside, temp_repo) is False

class TestConfigLoader:
    def test_load_config_valid(self, tmp_path):
        """Should load valid YAML."""
        cfg_path = tmp_path / "test.yaml"
        cfg_path.write_text("key: value\nlist:\n  - 1\n  - 2")
        data = load_config(cfg_path)
        assert data == {"key": "value", "list": [1, 2]}

    def test_load_config_invalid_root(self, tmp_path):
        """Should fail if root is not a mapping."""
        cfg_path = tmp_path / "test.yaml"
        cfg_path.write_text("- item1\n- item2")
        with pytest.raises(ValueError) as excinfo:
            load_config(cfg_path)
        assert "mapping" in str(excinfo.value)

    def test_load_config_non_string_keys(self, tmp_path):
        """Should fail if keys are not strings."""
        cfg_path = tmp_path / "test.yaml"
        cfg_path.write_text("1: numeric_key")
        with pytest.raises(ValueError) as excinfo:
            load_config(cfg_path)
        assert "string" in str(excinfo.value)

class TestCLI:
    def test_cli_status(self, temp_repo, capsys):
        """Test status command."""
        # We need to monkeypatch detect_repo_root because it uses CWD by default
        with patch("runtime.cli.detect_repo_root", return_value=temp_repo):
            with patch("sys.argv", ["runtime", "status"]):
                assert main() == 0
                captured = capsys.readouterr()
                assert f"repo_root: {temp_repo}" in captured.out
                assert "config_source: NONE" in captured.out

    def test_cli_global_config_placement(self, temp_repo, tmp_path, capsys):
        """Test that --config works BEFORE subcommand."""
        cfg_path = tmp_path / "test.yaml"
        cfg_path.write_text("key: value")
        
        with patch("runtime.cli.detect_repo_root", return_value=temp_repo):
            with patch("sys.argv", ["runtime", "--config", str(cfg_path), "status"]):
                assert main() == 0
                captured = capsys.readouterr()
                assert f"config_source: {cfg_path}" in captured.out

    def test_cli_canonical_json(self, temp_repo, tmp_path, capsys):
        """Test that config show emits canonical JSON."""
        cfg_path = tmp_path / "test.yaml"
        # Use unsorted keys to test sorting
        cfg_path.write_text("z: 1\na: 2\nm: 3")
        
        with patch("runtime.cli.detect_repo_root", return_value=temp_repo):
            with patch("sys.argv", ["runtime", "--config", str(cfg_path), "config", "show"]):
                assert main() == 0
                captured = capsys.readouterr()
                expected = '{"a":2,"m":3,"z":1}'
                assert captured.out.strip() == expected

    def test_cli_config_validate_success(self, temp_repo, tmp_path, capsys):
        """Test config validate with valid file."""
        cfg_path = tmp_path / "test.yaml"
        cfg_path.write_text("ok: true")
        
        with patch("runtime.cli.detect_repo_root", return_value=temp_repo):
            with patch("sys.argv", ["runtime", "--config", str(cfg_path), "config", "validate"]):
                assert main() == 0
                captured = capsys.readouterr()
                assert "VALID" in captured.out

    def test_cli_config_validate_missing_fails(self, temp_repo, capsys):
        """Test config validate fails without --config flag."""
        with patch("runtime.cli.detect_repo_root", return_value=temp_repo):
            # argparse will fail if required subcommand/arguments are missing
            # But validate command itself checks if config_path was passed via global flag
            with patch("sys.argv", ["runtime", "config", "validate"]):
                assert main() == 1
                captured = capsys.readouterr()
                assert "Error: No config file" in captured.out


class TestCLIMission:
    """Tests for mission CLI commands."""

    def test_mission_list(self, temp_repo, capsys, monkeypatch):
        """Test mission list outputs sorted JSON array."""
        monkeypatch.chdir(temp_repo)
        with patch("sys.argv", ["runtime", "mission", "list"]):
            assert main() == 0

            captured = capsys.readouterr()
            mission_types = json.loads(captured.out.strip())

            assert isinstance(mission_types, list)
            assert mission_types == sorted(mission_types)
            assert len(mission_types) > 0  # At least one mission type exists

    def test_mission_run_invalid_param(self, temp_repo, capsys, monkeypatch):
        """Test invalid parameter format."""
        monkeypatch.chdir(temp_repo)
        with patch("sys.argv", [
            "runtime", "mission", "run", "design",
            "--param", "no_equals"
        ]):
            assert main() == 1

            captured = capsys.readouterr()
            assert "Invalid parameter" in captured.out
            assert "key=value" in captured.out
