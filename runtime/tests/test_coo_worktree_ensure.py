from __future__ import annotations

import json
import subprocess
from pathlib import Path

from runtime.tests.test_coo_worktree_breakglass import _prepare_repo


def _run_ensure(
    repo_dir: Path, env: dict[str, str], *extra: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"), "ensure", *extra],
        cwd=repo_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _set_home(env: dict[str, str], tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    env["HOME"] = str(home)
    return home


def _seed_windows_launcher(repo_dir: Path, name: str = "COO_TUI.cmd") -> Path:
    win_dir = repo_dir / "tools" / "windows"
    win_dir.mkdir(parents=True, exist_ok=True)
    launcher = win_dir / name
    launcher.write_text(
        "@echo off\n"
        "setlocal\n"
        'wsl.exe -d Ubuntu -e bash -lic "cd /mnt/c/Users/cabra/Projects/LifeOS && coo tui"\n'
        "endlocal\n",
        encoding="utf-8",
    )
    return launcher


def test_ensure_installs_coo_real_symlink_when_missing(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    home = _set_home(env, tmp_path)

    proc = _run_ensure(repo_dir, env)

    assert proc.returncode == 0, proc.stderr
    assert "SHIM_REAL_INSTALLED=" in proc.stdout
    real_path = home / ".local" / "bin" / "coo.real"
    assert real_path.is_symlink()
    assert real_path.resolve() == repo_dir / "runtime" / "tools" / "coo_worktree.sh"


def test_ensure_installs_coo_shim_when_missing(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    home = _set_home(env, tmp_path)

    proc = _run_ensure(repo_dir, env)

    assert proc.returncode == 0, proc.stderr
    assert "SHIM_INSTALLED=" in proc.stdout
    shim_path = home / ".local" / "bin" / "coo"
    assert shim_path.exists()
    assert shim_path.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash\n")
    assert "LIFEOS_BUILD_REPO" in shim_path.read_text(encoding="utf-8")
    assert shim_path.stat().st_mode & 0o111


def test_ensure_idempotent_second_run_emits_ok(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _set_home(env, tmp_path)

    first = _run_ensure(repo_dir, env)
    second = _run_ensure(repo_dir, env)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert "SHIM_OK=" in second.stdout
    assert "SHIM_REAL_OK=" in second.stdout


def test_ensure_repairs_stale_shim_wrong_repo(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    home = _set_home(env, tmp_path)
    bin_dir = home / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    stale_shim = bin_dir / "coo"
    stale_shim.write_text(
        "#!/usr/bin/env bash\n"
        "export LIFEOS_BUILD_REPO=/tmp/wrong-repo\n"
        'exec "$HOME/.local/bin/coo.real" "$@"\n',
        encoding="utf-8",
    )
    stale_shim.chmod(0o755)

    proc = _run_ensure(repo_dir, env)

    assert proc.returncode == 0, proc.stderr
    assert "SHIM_INSTALLED=" in proc.stdout
    assert f'LIFEOS_BUILD_REPO="{repo_dir}"' in stale_shim.read_text(encoding="utf-8")


def test_ensure_json_output_is_parseable(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _set_home(env, tmp_path)

    proc = _run_ensure(repo_dir, env, "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "ok"
    assert "shim" in payload
    assert "openclaw_bin" in payload


def test_ensure_windows_launchers_ok_when_cmd_invokes_coo(tmp_path: Path) -> None:
    repo_dir, env, _ = _prepare_repo(tmp_path)
    _set_home(env, tmp_path)
    _seed_windows_launcher(repo_dir)

    proc = _run_ensure(repo_dir, env)

    assert proc.returncode == 0, proc.stderr
    assert "WINDOWS_LAUNCHER_OK=COO_TUI.cmd" in proc.stdout


def test_pyproject_no_coo_entrypoint() -> None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert 'coo = "runtime.cli:main"' not in text
