from __future__ import annotations

from scripts.workflow.reconcile_active_branches import reconcile


def test_reconcile_closes_missing_branch_and_duplicate_active_rows() -> None:
    data = {
        "branches": [
            {"name": "build/missing", "status": "active", "worktree_path": "/gone"},
            {
                "name": "build/live",
                "status": "active",
                "created": "2026-03-06T10:00:00",
                "worktree_path": "/live",
            },
            {
                "name": "build/live",
                "status": "active",
                "created": "2026-03-06T09:00:00",
                "worktree_path": "/stale",
            },
        ]
    }

    updated, changes = reconcile(
        data,
        branch_names={"build/live"},
        live_worktrees={"/live"},
    )

    missing = updated["branches"][0]
    live_primary = updated["branches"][1]
    live_duplicate = updated["branches"][2]

    assert missing["status"] == "closed"
    assert missing["worktree_path"] is None
    assert live_primary["status"] == "active"
    assert live_duplicate["status"] == "closed"
    assert live_duplicate["worktree_path"] is None
    assert changes


def test_reconcile_no_changes_when_already_clean() -> None:
    data = {
        "branches": [
            {
                "name": "build/live",
                "status": "active",
                "created": "2026-03-06T10:00:00",
                "worktree_path": "/live",
            }
        ]
    }

    updated, changes = reconcile(
        data,
        branch_names={"build/live"},
        live_worktrees={"/live"},
    )

    assert updated["branches"][0]["status"] == "active"
    assert changes == []
