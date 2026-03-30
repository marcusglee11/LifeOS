"""Tests for scripts/ci/resolve_nightly_task.py."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from runtime.orchestration.dispatch.order import ORDER_SCHEMA_VERSION, load_order


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    (tmp_path / "artifacts" / "dispatch" / "inbox").mkdir(parents=True)
    (tmp_path / "artifacts" / "dispatch" / "active").mkdir(parents=True)
    (tmp_path / "artifacts" / "dispatch" / "completed").mkdir(parents=True)
    return tmp_path


def _write_order(
    path: Path, order_id: str = "test-order-001", task_ref: str = "BACKLOG-42"
) -> None:
    order = {
        "schema_version": ORDER_SCHEMA_VERSION,
        "order_id": order_id,
        "task_ref": task_ref,
        "created_at": "2026-02-28T02:00:00Z",
        "steps": [{"name": "execute", "role": "builder", "provider": "auto"}],
        "constraints": {"worktree": True, "max_duration_seconds": 2400, "scope_paths": []},
        "shadow": {"enabled": False, "provider": "codex"},
        "supervision": {"per_cycle_check": False},
    }
    path.write_text(yaml.dump(order, default_flow_style=False, sort_keys=False), encoding="utf-8")


def _write_queue(repo_root: Path, entries: list[dict]) -> None:
    queue_path = repo_root / "artifacts" / "dispatch" / "nightly_queue.yaml"
    queue_path.write_text(
        yaml.dump(entries, default_flow_style=False, sort_keys=False), encoding="utf-8"
    )


# --- import resolve helpers ---
def _import_resolve():
    """Import the resolve module from scripts/ci/."""
    import importlib.util

    script_path = Path(__file__).resolve().parents[3] / "scripts" / "ci" / "resolve_nightly_task.py"
    spec = importlib.util.spec_from_file_location("resolve_nightly_task", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestInboxOrder:
    def test_uses_first_inbox_order(self, fake_repo: Path, tmp_path: Path) -> None:
        inbox = fake_repo / "artifacts" / "dispatch" / "inbox"
        _write_order(inbox / "alpha.yaml", order_id="alpha")
        _write_order(inbox / "beta.yaml", order_id="beta")

        output = tmp_path / "resolved.yaml"
        mod = _import_resolve()
        rc = mod.main(["--output", str(output), "--repo-root", str(fake_repo)])

        assert rc == 0
        assert output.exists()
        order = load_order(output)
        assert order.order_id == "alpha"

    def test_skips_tmp_files(self, fake_repo: Path, tmp_path: Path) -> None:
        inbox = fake_repo / "artifacts" / "dispatch" / "inbox"
        _write_order(inbox / "real.yaml", order_id="real")
        (inbox / "partial.yaml.tmp").write_text("incomplete", encoding="utf-8")

        output = tmp_path / "resolved.yaml"
        mod = _import_resolve()
        rc = mod.main(["--output", str(output), "--repo-root", str(fake_repo)])

        assert rc == 0
        order = load_order(output)
        assert order.order_id == "real"


class TestQueueFallback:
    def test_pops_first_queue_entry(self, fake_repo: Path, tmp_path: Path) -> None:
        entries = [
            {"task_ref": "BACKLOG-10", "steps": [{"name": "build", "role": "builder"}]},
            {"task_ref": "BACKLOG-11", "steps": [{"name": "build", "role": "builder"}]},
        ]
        _write_queue(fake_repo, entries)

        output = tmp_path / "resolved.yaml"
        mod = _import_resolve()
        rc = mod.main(["--output", str(output), "--repo-root", str(fake_repo)])

        assert rc == 0
        assert output.exists()
        order = load_order(output)
        assert order.task_ref == "BACKLOG-10"
        assert order.schema_version == ORDER_SCHEMA_VERSION

        # Queue should have one entry left
        queue_path = fake_repo / "artifacts" / "dispatch" / "nightly_queue.yaml"
        remaining = yaml.safe_load(queue_path.read_text(encoding="utf-8"))
        assert len(remaining) == 1
        assert remaining[0]["task_ref"] == "BACKLOG-11"

    def test_generated_order_passes_validation(self, fake_repo: Path, tmp_path: Path) -> None:
        entries = [{"task_ref": "BACKLOG-99"}]
        _write_queue(fake_repo, entries)

        output = tmp_path / "resolved.yaml"
        mod = _import_resolve()
        rc = mod.main(["--output", str(output), "--repo-root", str(fake_repo)])

        assert rc == 0
        order = load_order(output)
        assert order.task_ref == "BACKLOG-99"
        assert len(order.steps) == 1
        assert order.steps[0].name == "execute"


class TestNoTasks:
    def test_empty_inbox_and_no_queue(self, fake_repo: Path, tmp_path: Path, capsys) -> None:
        output = tmp_path / "resolved.yaml"
        mod = _import_resolve()
        rc = mod.main(["--output", str(output), "--repo-root", str(fake_repo)])

        assert rc == 0
        assert not output.exists()
        captured = capsys.readouterr()
        assert "no tasks available" in captured.out

    def test_empty_queue_file(self, fake_repo: Path, tmp_path: Path, capsys) -> None:
        _write_queue(fake_repo, [])

        output = tmp_path / "resolved.yaml"
        mod = _import_resolve()
        rc = mod.main(["--output", str(output), "--repo-root", str(fake_repo)])

        assert rc == 0
        assert not output.exists()
        captured = capsys.readouterr()
        assert "no tasks available" in captured.out
