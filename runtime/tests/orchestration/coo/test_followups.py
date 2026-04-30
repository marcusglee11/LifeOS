"""Tests for COO autonomous follow-up issue planning."""

from __future__ import annotations

import pytest

from runtime.orchestration.coo.followups import (
    FOLLOWUP_DISPOSITION_SCHEMA_VERSION,
    build_followup_issue_packet,
    build_followup_plan,
    build_parent_closure_comment,
    build_parent_link_comment,
    classify_followup,
    issue_ref,
    validate_parent_closure_followups,
)

_REPO = "marcusglee11/LifeOS"
_PARENT = 77
_ROADMAP = 74
_EVIDENCE = "https://github.com/marcusglee11/LifeOS/issues/77#issuecomment-1"


def test_required_now_followup_mints_wi_handoff_and_blocks_parent_until_child_exists() -> None:
    disposition = classify_followup(
        {
            "title": "Fix generated follow-up dispatch smoke",
            "summary": "The follow-up loop found a dispatch blocker.",
            "disposition": "required-now",
            "owner_or_lane": "codex",
            "required_for_parent": True,
            "unblock_condition": "child PR merged and receipt posted",
            "scope_paths": ["runtime/orchestration/coo/"],
        },
        repo=_REPO,
        parent_issue_number=_PARENT,
        roadmap_issue_number=_ROADMAP,
        evidence_ref=_EVIDENCE,
    )

    assert disposition["schema_version"] == FOLLOWUP_DISPOSITION_SCHEMA_VERSION
    assert disposition["disposition"] == "required-now"
    assert disposition["blocks_parent_closure"] is True
    assert disposition["next_action"] == "dispatch"
    assert disposition["child_issue"] is None
    assert disposition["wi_handoff"]["eligible_for_wi_minting"] is True
    assert disposition["wi_handoff"]["status_after_triage"] == "READY"
    assert validate_parent_closure_followups([disposition]) == [
        "followups[0]: required-now follow-up requires child_issue before parent closure"
    ]


def test_required_now_followup_allows_parent_closure_after_child_issue_is_linked() -> None:
    child = issue_ref(_REPO, 100)
    disposition = classify_followup(
        {
            "title": "Fix generated follow-up dispatch smoke",
            "disposition": "required-now",
            "unblock_condition": "child issue closed with evidence",
        },
        repo=_REPO,
        parent_issue_number=_PARENT,
        roadmap_issue_number=_ROADMAP,
        evidence_ref=_EVIDENCE,
        child_issue=child,
    )

    comment = build_parent_closure_comment(
        parent_issue=issue_ref(_REPO, _PARENT),
        followups=[disposition],
        evidence_ref=_EVIDENCE,
    )

    assert validate_parent_closure_followups([disposition]) == []
    assert "`required-now`" in comment
    assert child in comment
    assert "unblock_condition: child issue closed with evidence" in comment


def test_deferred_followup_creates_child_issue_but_does_not_block_parent_closure() -> None:
    disposition = classify_followup(
        {
            "title": "Add retention for continuation hook audit log",
            "summary": "Heartbeat logging can grow without bound.",
            "disposition": "deferred",
            "reason": "Useful hardening but not required for #77 closure.",
        },
        repo=_REPO,
        parent_issue_number=_PARENT,
        roadmap_issue_number=_ROADMAP,
        evidence_ref=_EVIDENCE,
        child_issue=issue_ref(_REPO, 101),
    )
    packet = build_followup_issue_packet(
        disposition,
        repo=_REPO,
        roadmap_issue=issue_ref(_REPO, _ROADMAP),
    ).to_dict()

    assert disposition["disposition"] == "deferred"
    assert disposition["blocks_parent_closure"] is False
    assert disposition["next_action"] == "defer"
    assert validate_parent_closure_followups([disposition]) == []
    assert packet["schema_version"] == "coo_followup_issue_packet.v0"
    assert packet["gh"]["argv"][:5] == ["gh", "issue", "create", "-R", _REPO]
    assert f"Parent issue: {issue_ref(_REPO, _PARENT)}" in packet["body"]
    assert f"Roadmap issue: {issue_ref(_REPO, _ROADMAP)}" in packet["body"]
    assert "disposition: deferred" in packet["body"]


def test_duplicate_detection_uses_exact_title_or_link_scan_and_skips_creation() -> None:
    existing = [
        {
            "number": 102,
            "title": "Add retention for continuation hook audit log",
            "url": issue_ref(_REPO, 102),
            "body": f"Parent issue: {issue_ref(_REPO, _PARENT)}",
        }
    ]

    plan = build_followup_plan(
        [
            {
                "title": "Add retention for continuation hook audit log",
                "summary": "Same follow-up rediscovered.",
            }
        ],
        repo=_REPO,
        parent_issue_number=_PARENT,
        roadmap_issue_number=_ROADMAP,
        existing_issues=existing,
        evidence_ref=_EVIDENCE,
    )

    assert plan["dispositions"][0]["disposition"] == "duplicate"
    assert plan["dispositions"][0]["child_issue"] == issue_ref(_REPO, 102)
    assert plan["dispositions"][0]["next_action"] == "close-duplicate"
    assert plan["issue_create_packets"] == []
    assert plan["closure_allowed"] is True


def test_duplicate_scan_does_not_treat_parent_or_roadmap_link_as_duplicate() -> None:
    plan = build_followup_plan(
        [{"title": "Different follow-up", "disposition": "required-now"}],
        repo=_REPO,
        parent_issue_number=_PARENT,
        roadmap_issue_number=_ROADMAP,
        existing_issues=[
            {
                "number": 200,
                "title": "Unrelated linked issue",
                "url": issue_ref(_REPO, 200),
                "body": (
                    f"Parent issue: {issue_ref(_REPO, _PARENT)}\n"
                    f"Roadmap: {issue_ref(_REPO, _ROADMAP)}"
                ),
            }
        ],
        evidence_ref=_EVIDENCE,
    )

    assert plan["dispositions"][0]["disposition"] == "required-now"
    assert plan["dispositions"][0]["child_issue"] is None
    assert len(plan["issue_create_packets"]) == 1


def test_no_action_followup_records_evidence_and_creates_no_issue() -> None:
    plan = build_followup_plan(
        [
            {
                "title": "No material follow-up",
                "action_required": False,
                "reason": "Reviewer note is already resolved by the current diff.",
            }
        ],
        repo=_REPO,
        parent_issue_number=_PARENT,
        roadmap_issue_number=_ROADMAP,
        evidence_ref=_EVIDENCE,
    )

    assert plan["dispositions"][0]["disposition"] == "no-action"
    assert plan["dispositions"][0]["owner_or_lane"] == "none"
    assert plan["dispositions"][0]["next_action"] == "none"
    assert plan["issue_create_packets"] == []
    assert plan["closure_allowed"] is True


def test_parent_link_comment_lists_child_disposition_contract() -> None:
    disposition = classify_followup(
        {"title": "Dispatch child", "disposition": "required-now"},
        repo=_REPO,
        parent_issue_number=_PARENT,
        roadmap_issue_number=_ROADMAP,
        evidence_ref=_EVIDENCE,
        child_issue=issue_ref(_REPO, 103),
    )

    comment = build_parent_link_comment(disposition)

    assert "## Follow-up linked" in comment
    assert "Disposition: `required-now`" in comment
    assert issue_ref(_REPO, 103) in comment


def test_build_plan_dry_run_covers_required_deferred_duplicate_and_no_action() -> None:
    plan = build_followup_plan(
        [
            {"title": "Required child", "disposition": "required-now"},
            {"title": "Deferred child", "disposition": "deferred"},
            {"title": "Existing child"},
            {"title": "Nothing to do", "action_required": False},
        ],
        repo=_REPO,
        parent_issue_number=_PARENT,
        roadmap_issue_number=_ROADMAP,
        existing_issues=[{"number": 104, "title": "Existing child", "url": issue_ref(_REPO, 104)}],
        evidence_ref=_EVIDENCE,
    )

    assert [item["disposition"] for item in plan["dispositions"]] == [
        "required-now",
        "deferred",
        "duplicate",
        "no-action",
    ]
    assert len(plan["issue_create_packets"]) == 2
    assert plan["closure_allowed"] is False
    assert plan["closure_blockers"] == [
        "followups[0]: required-now follow-up requires child_issue before parent closure"
    ]


def test_parent_closure_comment_fails_closed_for_required_now_without_child() -> None:
    disposition = classify_followup(
        {"title": "Required child", "disposition": "required-now"},
        repo=_REPO,
        parent_issue_number=_PARENT,
        roadmap_issue_number=_ROADMAP,
        evidence_ref=_EVIDENCE,
    )

    with pytest.raises(ValueError, match="requires child_issue"):
        build_parent_closure_comment(
            parent_issue=issue_ref(_REPO, _PARENT),
            followups=[disposition],
            evidence_ref=_EVIDENCE,
        )
