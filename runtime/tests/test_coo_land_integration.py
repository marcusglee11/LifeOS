from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def _setup_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "runtime" / "tools").mkdir(parents=True)
    (repo / "runtime" / "tests").mkdir(parents=True)
    (repo / "artifacts" / "evidence" / "openclaw" / "jobs").mkdir(parents=True)
    (repo / ".gitignore").write_text("/artifacts/evidence/openclaw/jobs/\n", encoding="utf-8")

    source_repo = Path(__file__).resolve().parents[2]
    for rel in ("runtime/tools/coo_worktree.sh", "runtime/tools/coo_land_policy.py"):
        src = source_repo / rel
        dst = repo / rel
        shutil.copy2(src, dst)
        dst.chmod(dst.stat().st_mode | stat.S_IEXEC)

    (repo / "runtime" / "tests" / "test_coo_capsule_render.py").write_text(
        "def test_stub_capsule_render():\n    assert True\n",
        encoding="utf-8",
    )
    (repo / "runtime" / "tests" / "test_coo_worktree_marker_receipt.py").write_text(
        "def test_stub_marker_receipt():\n    assert True\n",
        encoding="utf-8",
    )

    _run(["git", "init", "-b", "main"], repo)
    _run(["git", "config", "user.email", "test@example.com"], repo)
    _run(["git", "config", "user.name", "Test User"], repo)
    _run(["git", "add", "."], repo)
    _run(["git", "commit", "-m", "init"], repo)
    return repo, source_repo


def test_coo_land_path_transplant_creates_receipt(tmp_path: Path) -> None:
    repo, _ = _setup_repo(tmp_path)

    _run(["git", "checkout", "-b", "feature-src"], repo)
    target = repo / "runtime" / "tools" / "coo_worktree.sh"
    target.write_text(target.read_text(encoding="utf-8") + "\n# land-test-marker\n", encoding="utf-8")
    _run(["git", "add", "runtime/tools/coo_worktree.sh"], repo)
    _run(["git", "commit", "-m", "feature change"], repo)
    src_head = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    _run(["git", "checkout", "main"], repo)

    evid = repo / "artifacts" / "evidence" / "openclaw" / "jobs" / "20990101T000000Z"
    evid.mkdir(parents=True)
    (evid / "worktree_head.txt").write_text(src_head + "\n", encoding="utf-8")
    (evid / "worktree_status_porcelain.txt").write_text("(empty)\n", encoding="utf-8")
    (evid / "worktree_diff_name_only.txt").write_text("runtime/tools/coo_worktree.sh\n", encoding="utf-8")

    proc = subprocess.run(
        [
            str(repo / "runtime" / "tools" / "coo_worktree.sh"),
            "land",
            "--evid",
            str(evid),
            "--src",
            src_head,
            "--dest",
            "main",
            "--skip-e2e",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr

    receipt = evid / "land_receipt.txt"
    assert receipt.exists()
    text = receipt.read_text(encoding="utf-8")
    assert "MODE=path_transplant" in text
    assert "ALLOWLIST_HASH=" in text
    assert "runtime/tools/coo_worktree.sh" in text
    assert "VERIFICATION_PYTEST_RC=0" in text
    assert "VERIFICATION_E2E_CMD=SKIPPED(--skip-e2e)" in text
    assert f"EVID_SELECTED={evid}" in text
    assert "CLEAN_PROOF_PRE_STATUS_BEGIN\n(empty)\nCLEAN_PROOF_PRE_STATUS_END" in text
    assert "CLEAN_PROOF_POST_STATUS_BEGIN\n(empty)\nCLEAN_PROOF_POST_STATUS_END" in text

    assert "land-test-marker" in (repo / "runtime" / "tools" / "coo_worktree.sh").read_text(encoding="utf-8")
    assert _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo).stdout.strip() == "main"
    assert _run(["git", "status", "--porcelain=v1"], repo).stdout.strip() == ""


def test_coo_land_routes_blocked_report_into_evidence_dir(tmp_path: Path) -> None:
    repo, _ = _setup_repo(tmp_path)
    src_head = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

    evid = repo / "artifacts" / "evidence" / "openclaw" / "jobs" / "20990101T010000Z"
    evid.mkdir(parents=True)
    (evid / "worktree_head.txt").write_text(src_head + "\n", encoding="utf-8")
    (evid / "worktree_status_porcelain.txt").write_text("(empty)\n", encoding="utf-8")
    (evid / "worktree_diff_name_only.txt").write_text("", encoding="utf-8")

    proc = subprocess.run(
        [
            str(repo / "runtime" / "tools" / "coo_worktree.sh"),
            "land",
            "--evid",
            str(evid),
            "--src",
            src_head,
            "--dest",
            "main",
            "--skip-e2e",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0

    reports = sorted(evid.glob("REPORT_BLOCKED__coo_land__*.md"))
    assert reports, "blocked report must be written into evidence dir"

    root_reports = sorted((repo / "artifacts").glob("REPORT_BLOCKED__*.md"))
    assert not root_reports, "blocked report must not be written to tracked artifacts root"
    assert _run(["git", "status", "--porcelain=v1"], repo).stdout.strip() == ""
