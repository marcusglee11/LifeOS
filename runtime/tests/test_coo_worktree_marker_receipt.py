from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def _write_stub_openclaw(bin_dir: Path) -> None:
    job = {
        "kind": "lifeos.job.v0.1",
        "job_type": "e2e_test",
        "objective": "Run a representative E2E test in the LifeOS repo",
        "scope": ["run tests only", "no code edits"],
        "non_goals": ["no installs", "no network", "no git operations"],
        "workdir": ".",
        "command": [
            "python3",
            "-c",
            "print('================ 1 passed, 1 deselected in 0.01s ================')",
        ],
        "timeout_s": 1800,
        "expected_artifacts": ["stdout.txt", "stderr.txt", "rc.txt", "duration_s.txt"],
        "clean_repo_required": True,
    }
    stub = bin_dir / "openclaw"
    job_json = json.dumps(job)
    stub.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "job_json = " + repr(job_json),
                "resp = {'payloads': [{'text': job_json}]}",
                "print(json.dumps(resp))",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)


def test_coo_e2e_marker_receipt_projects_canonical_capsule(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "runtime" / "tools").mkdir(parents=True)
    (repo_dir / "artifacts").mkdir()
    (repo_dir / ".gitignore").write_text(
        "/artifacts/evidence/openclaw/jobs/\n",
        encoding="utf-8",
    )
    (repo_dir / "README.md").write_text("temp repo for coo e2e marker test\n", encoding="utf-8")

    source_repo = Path(__file__).resolve().parents[2]
    for rel in ("runtime/tools/coo_worktree.sh", "runtime/tools/coo_capsule_render.py"):
        src = source_repo / rel
        dst = repo_dir / rel
        shutil.copy2(src, dst)
        dst.chmod(dst.stat().st_mode | stat.S_IEXEC)

    _run(["git", "init"], repo_dir)
    _run(["git", "config", "user.email", "test@example.com"], repo_dir)
    _run(["git", "config", "user.name", "Test User"], repo_dir)
    _run(["git", "add", "."], repo_dir)
    _run(["git", "commit", "-m", "init"], repo_dir)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_stub_openclaw(bin_dir)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["OPENCLAW_MODELS_PREFLIGHT_SKIP"] = "1"  # Skip model preflight for test

    proc = subprocess.run(
        [str(repo_dir / "runtime" / "tools" / "coo_worktree.sh"), "e2e"],
        cwd=repo_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr

    marker_match = re.search(
        r"COO_E2E_MINI_CAPSULE_BEGIN\n(?P<body>.*?)\nCOO_E2E_MINI_CAPSULE_END",
        proc.stdout,
        flags=re.S,
    )
    assert marker_match, proc.stdout
    marker_body = marker_match.group("body")

    result_lines = re.findall(r"^RESULT_PRETTY_ERR_BYTES=\d+$", marker_body, flags=re.M)
    assert len(result_lines) == 1
    assert re.search(r"^JOB_PRETTY_ERR_BYTES=", marker_body, flags=re.M) is None

    evid_match = re.search(r"^EVID=(.+)$", proc.stdout, flags=re.M)
    assert evid_match, proc.stdout
    evid_dir = Path(evid_match.group(1).strip())
    assert evid_dir.is_dir()

    capsule_file = evid_dir / "capsule.txt"
    marker_receipt = evid_dir / "marker_receipt.txt"
    clean_pre = evid_dir / "clean_pre.txt"
    clean_post = evid_dir / "clean_post.txt"
    hashes = evid_dir / "hashes.sha256"

    for path in (capsule_file, marker_receipt, clean_pre, clean_post, hashes):
        assert path.exists(), f"missing {path.name}"

    capsule_text = capsule_file.read_text(encoding="utf-8")
    capsule_result_lines = re.findall(
        r"^RESULT_PRETTY_ERR_BYTES=\d+$",
        capsule_text,
        flags=re.M,
    )
    assert len(capsule_result_lines) == 1

    hashes_text = hashes.read_text(encoding="utf-8")
    assert re.search(r"capsule\.txt$", hashes_text, flags=re.M)
    assert re.search(r"marker_receipt\.txt$", hashes_text, flags=re.M)
    assert re.search(r"clean_pre\.txt$", hashes_text, flags=re.M)
    assert re.search(r"clean_post\.txt$", hashes_text, flags=re.M)
