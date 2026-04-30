"""COO autonomous follow-up issue planning and closure checks.

The functions in this module are deterministic: they build issue/comment/WI handoff
packets and validation decisions, but do not call GitHub. Callers execute the
returned packets only after their normal policy/credential gates pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

FOLLOWUP_DISPOSITION_SCHEMA_VERSION = "coo_followup_disposition.v0"
FOLLOWUP_PLAN_SCHEMA_VERSION = "coo_followup_plan.v0"
FOLLOWUP_ISSUE_PACKET_SCHEMA_VERSION = "coo_followup_issue_packet.v0"
FOLLOWUP_CLOSURE_SCHEMA_VERSION = "coo_followup_closure.v0"

FOLLOWUP_DISPOSITIONS = {"required-now", "deferred", "duplicate", "no-action"}
FOLLOWUP_OWNER_LANES = {"coo", "codex", "human", "deferred", "none"}
FOLLOWUP_NEXT_ACTIONS = {"dispatch", "defer", "close-duplicate", "none"}

_GITHUB_ISSUE_URL_RE = re.compile(
    r"^https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(?P<number>\d+)$"
)
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class FollowUpIssuePacket:
    """A dry-run packet that can be executed with `gh issue create`."""

    schema_version: str
    repo: str
    parent_issue: str
    roadmap_issue: str
    title: str
    body: str
    labels: tuple[str, ...]
    disposition: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repo": self.repo,
            "parent_issue": self.parent_issue,
            "roadmap_issue": self.roadmap_issue,
            "title": self.title,
            "body": self.body,
            "labels": list(self.labels),
            "disposition": self.disposition,
            "gh": {
                "argv": [
                    "gh",
                    "issue",
                    "create",
                    "-R",
                    self.repo,
                    "--title",
                    self.title,
                    "--body",
                    self.body,
                ]
                + [arg for label in self.labels for arg in ("--label", label)]
            },
        }


def issue_ref(repo: str, issue_number: int) -> str:
    """Return a canonical GitHub issue URL."""
    if not isinstance(repo, str) or not _REPO_RE.match(repo):
        raise ValueError("repo must be owner/name")
    if not isinstance(issue_number, int) or isinstance(issue_number, bool) or issue_number <= 0:
        raise ValueError("issue_number must be a positive integer")
    return f"https://github.com/{repo}/issues/{issue_number}"


def normalize_followup_title(title: str) -> str:
    """Normalize only insignificant surrounding/internal whitespace for exact title scans."""
    return " ".join(str(title).strip().split())


def find_duplicate_followup(
    *,
    title: str,
    existing_issues: Sequence[dict[str, Any]],
    link_refs: Sequence[str] = (),
) -> dict[str, Any] | None:
    """Find an obvious duplicate by exact normalized title or explicit link reference."""
    wanted_title = normalize_followup_title(title)
    refs = [str(ref).strip() for ref in link_refs if str(ref).strip()]
    for issue in existing_issues:
        issue_title = normalize_followup_title(str(issue.get("title", "")))
        if wanted_title and issue_title == wanted_title:
            return issue
        haystack = " ".join(str(issue.get(field, "")) for field in ("url", "body", "description"))
        if refs and any(ref in haystack for ref in refs):
            return issue
    return None


def classify_followup(
    candidate: dict[str, Any],
    *,
    repo: str,
    parent_issue_number: int,
    roadmap_issue_number: int,
    existing_issues: Sequence[dict[str, Any]] = (),
    evidence_ref: str,
    child_issue: str | None = None,
) -> dict[str, Any]:
    """Classify one discovered follow-up into the v0 disposition contract."""
    parent_issue = issue_ref(repo, parent_issue_number)
    title = str(candidate.get("title") or "").strip()
    summary = str(candidate.get("summary") or candidate.get("body") or "").strip()
    requested = str(candidate.get("disposition") or "").strip().lower()
    explicit_duplicate = _clean_optional(candidate.get("duplicate_of"))

    duplicate = None
    if title:
        duplicate = find_duplicate_followup(
            title=title,
            existing_issues=existing_issues,
            link_refs=[explicit_duplicate] if explicit_duplicate else (),
        )
    if explicit_duplicate or duplicate is not None:
        duplicate_ref = explicit_duplicate or _issue_url_from_record(repo, duplicate)
        return _disposition(
            disposition="duplicate",
            reason=_first_non_empty(
                candidate.get("reason"),
                f"Existing follow-up already covers this work: {duplicate_ref}",
            ),
            owner_or_lane="none",
            parent_issue=parent_issue,
            child_issue=duplicate_ref,
            blocks_parent_closure=False,
            unblock_condition=None,
            next_action="close-duplicate",
            evidence_ref=evidence_ref,
            title=title,
            summary=summary,
        )

    if requested == "no-action" or candidate.get("action_required") is False:
        return _disposition(
            disposition="no-action",
            reason=_first_non_empty(candidate.get("reason"), "No follow-up action is required."),
            owner_or_lane="none",
            parent_issue=parent_issue,
            child_issue=None,
            blocks_parent_closure=False,
            unblock_condition=None,
            next_action="none",
            evidence_ref=evidence_ref,
            title=title,
            summary=summary,
        )

    if requested == "deferred" or candidate.get("defer") is True:
        return _disposition(
            disposition="deferred",
            reason=_first_non_empty(
                candidate.get("reason"),
                candidate.get("defer_reason"),
                "Follow-up is real but not required for the current objective.",
            ),
            owner_or_lane="deferred",
            parent_issue=parent_issue,
            child_issue=child_issue,
            blocks_parent_closure=False,
            unblock_condition=_clean_optional(candidate.get("unblock_condition")),
            next_action="defer",
            evidence_ref=evidence_ref,
            title=title,
            summary=summary,
        )

    required_now = (
        requested == "required-now"
        or candidate.get("required_for_parent") is True
        or candidate.get("blocks_parent_closure") is True
    )
    if required_now:
        return _disposition(
            disposition="required-now",
            reason=_first_non_empty(
                candidate.get("reason"),
                "Follow-up is required to complete or safely close the parent objective.",
            ),
            owner_or_lane=_lane(candidate.get("owner_or_lane"), default="codex"),
            parent_issue=parent_issue,
            child_issue=child_issue,
            blocks_parent_closure=True,
            unblock_condition=_first_non_empty(
                candidate.get("unblock_condition"), "linked child issue is closed with evidence"
            ),
            next_action="dispatch",
            evidence_ref=evidence_ref,
            title=title,
            summary=summary,
            wi_handoff=build_wi_handoff(candidate, repo=repo, parent_issue=parent_issue),
        )

    return _disposition(
        disposition="deferred",
        reason=_first_non_empty(
            candidate.get("reason"),
            "Defaulted to deferred because the follow-up is not required for current closure.",
        ),
        owner_or_lane="deferred",
        parent_issue=parent_issue,
        child_issue=child_issue,
        blocks_parent_closure=False,
        unblock_condition=_clean_optional(candidate.get("unblock_condition")),
        next_action="defer",
        evidence_ref=evidence_ref,
        title=title,
        summary=summary,
    )


def build_wi_handoff(
    candidate: dict[str, Any],
    *,
    repo: str,
    parent_issue: str,
) -> dict[str, Any]:
    """Build a minimal WI minting/dispatch handoff for required-now follow-ups."""
    return {
        "schema_version": "coo_followup_wi_handoff.v0",
        "eligible_for_wi_minting": True,
        "repo": repo,
        "parent_issue": parent_issue,
        "title": str(candidate.get("title") or "").strip(),
        "priority": str(candidate.get("priority") or "P1"),
        "risk": str(candidate.get("risk") or "med"),
        "task_type": str(candidate.get("task_type") or "build"),
        "scope_paths": [str(path) for path in candidate.get("scope_paths") or []],
        "status_after_triage": "READY",
        "next_action": "dispatch",
    }


def build_followup_issue_body(
    disposition: dict[str, Any],
    *,
    roadmap_issue: str,
) -> str:
    """Render a generated follow-up issue body with parent/roadmap links."""
    errors = validate_followup_disposition(disposition, for_parent_closure=False)
    if errors:
        raise ValueError("Invalid follow-up disposition: " + "; ".join(errors))
    title = str(disposition.get("title") or "Follow-up")
    summary = str(disposition.get("summary") or disposition["reason"])
    return "\n".join(
        [
            "## Generated follow-up",
            "",
            f"Parent issue: {disposition['parent_issue']}",
            f"Roadmap issue: {roadmap_issue}",
            f"Disposition: `{disposition['disposition']}`",
            "",
            "## Objective",
            "",
            title,
            "",
            "## Context",
            "",
            summary,
            "",
            "## Disposition packet",
            "",
            "```yaml",
            f"disposition: {disposition['disposition']}",
            f"reason: {disposition['reason']}",
            f"owner_or_lane: {disposition['owner_or_lane']}",
            f"parent_issue: {disposition['parent_issue']}",
            f"child_issue: {disposition['child_issue'] or 'null'}",
            f"blocks_parent_closure: {str(disposition['blocks_parent_closure']).lower()}",
            f"unblock_condition: {disposition['unblock_condition'] or 'null'}",
            f"next_action: {disposition['next_action']}",
            f"evidence_ref: {disposition['evidence_ref']}",
            "```",
        ]
    )


def build_followup_issue_packet(
    disposition: dict[str, Any],
    *,
    repo: str,
    roadmap_issue: str,
    labels: Sequence[str] = ("ops", "follow-up"),
) -> FollowUpIssuePacket:
    """Build the GitHub issue creation packet for a non-duplicate follow-up."""
    if disposition.get("disposition") not in {"required-now", "deferred"}:
        raise ValueError("only required-now or deferred dispositions create child issues")
    title = str(disposition.get("title") or "Follow-up").strip()
    if not title:
        raise ValueError("follow-up issue title must be non-empty")
    return FollowUpIssuePacket(
        schema_version=FOLLOWUP_ISSUE_PACKET_SCHEMA_VERSION,
        repo=repo,
        parent_issue=str(disposition["parent_issue"]),
        roadmap_issue=roadmap_issue,
        title=title,
        body=build_followup_issue_body(disposition, roadmap_issue=roadmap_issue),
        labels=tuple(str(label) for label in labels),
        disposition=disposition,
    )


def build_parent_link_comment(disposition: dict[str, Any]) -> str:
    """Render the parent issue link comment after a child issue is created."""
    errors = validate_followup_disposition(disposition, for_parent_closure=False)
    if errors:
        raise ValueError("Invalid follow-up disposition: " + "; ".join(errors))
    child = disposition.get("child_issue") or "pending child issue"
    return (
        "## Follow-up linked\n\n"
        f"Disposition: `{disposition['disposition']}`\n"
        f"Child issue: {child}\n"
        f"Blocks parent closure: `{str(disposition['blocks_parent_closure']).lower()}`\n"
        f"Unblock condition: {disposition['unblock_condition'] or 'null'}\n"
        f"Evidence: {disposition['evidence_ref']}"
    )


def build_parent_closure_comment(
    *,
    parent_issue: str,
    followups: Sequence[dict[str, Any]],
    evidence_ref: str,
) -> str:
    """Render the closure comment and fail closed for unresolved required-now follow-ups."""
    errors = validate_parent_closure_followups(followups)
    if errors:
        raise ValueError("Parent closure follow-up validation failed: " + "; ".join(errors))
    lines = [
        "## Follow-up closure disposition",
        "",
        f"Parent issue: {parent_issue}",
        f"Evidence: {evidence_ref}",
        "",
    ]
    if not followups:
        lines.append("No discovered follow-ups.")
    for item in followups:
        child = item.get("child_issue") or "null"
        lines.extend(
            [
                f"- `{item['disposition']}` — {item.get('title') or item['reason']}",
                f"  - child_issue: {child}",
                f"  - owner_or_lane: {item['owner_or_lane']}",
                f"  - blocks_parent_closure: {str(item['blocks_parent_closure']).lower()}",
                f"  - unblock_condition: {item['unblock_condition'] or 'null'}",
                f"  - next_action: {item['next_action']}",
                f"  - evidence_ref: {item['evidence_ref']}",
            ]
        )
    return "\n".join(lines)


def build_followup_plan(
    candidates: Sequence[dict[str, Any]],
    *,
    repo: str,
    parent_issue_number: int,
    roadmap_issue_number: int,
    existing_issues: Sequence[dict[str, Any]] = (),
    evidence_ref: str,
) -> dict[str, Any]:
    """Classify candidates and build executable dry-run packets for issue creation."""
    parent_issue = issue_ref(repo, parent_issue_number)
    roadmap_issue = issue_ref(repo, roadmap_issue_number)
    dispositions = [
        classify_followup(
            candidate,
            repo=repo,
            parent_issue_number=parent_issue_number,
            roadmap_issue_number=roadmap_issue_number,
            existing_issues=existing_issues,
            evidence_ref=evidence_ref,
        )
        for candidate in candidates
    ]
    issue_packets = [
        build_followup_issue_packet(item, repo=repo, roadmap_issue=roadmap_issue).to_dict()
        for item in dispositions
        if item["disposition"] in {"required-now", "deferred"}
    ]
    closure_errors = validate_parent_closure_followups(dispositions)
    return {
        "schema_version": FOLLOWUP_PLAN_SCHEMA_VERSION,
        "repo": repo,
        "parent_issue": parent_issue,
        "roadmap_issue": roadmap_issue,
        "dispositions": dispositions,
        "issue_create_packets": issue_packets,
        "closure_allowed": not closure_errors,
        "closure_blockers": closure_errors,
    }


def validate_followup_disposition(
    disposition: Any,
    *,
    for_parent_closure: bool = False,
) -> list[str]:
    """Validate one disposition packet against the #77 contract."""
    if not isinstance(disposition, dict):
        return ["disposition must be an object"]
    errors: list[str] = []
    required = (
        "schema_version",
        "disposition",
        "reason",
        "owner_or_lane",
        "parent_issue",
        "child_issue",
        "blocks_parent_closure",
        "unblock_condition",
        "next_action",
        "evidence_ref",
    )
    for field in required:
        if field not in disposition:
            errors.append(f"missing required field: {field}")
    if errors:
        return errors
    if disposition["schema_version"] != FOLLOWUP_DISPOSITION_SCHEMA_VERSION:
        errors.append(f"schema_version must be {FOLLOWUP_DISPOSITION_SCHEMA_VERSION}")
    if disposition["disposition"] not in FOLLOWUP_DISPOSITIONS:
        errors.append("disposition must be one of: deferred, duplicate, no-action, required-now")
    if disposition["owner_or_lane"] not in FOLLOWUP_OWNER_LANES:
        errors.append("owner_or_lane must be one of: codex, coo, deferred, human, none")
    if disposition["next_action"] not in FOLLOWUP_NEXT_ACTIONS:
        errors.append("next_action must be one of: close-duplicate, defer, dispatch, none")
    _require_non_empty(disposition.get("reason"), "reason", errors)
    _require_issue_url(disposition.get("parent_issue"), "parent_issue", errors)
    child_issue = disposition.get("child_issue")
    if child_issue is not None:
        _require_issue_url(child_issue, "child_issue", errors)
    if not isinstance(disposition.get("blocks_parent_closure"), bool):
        errors.append("blocks_parent_closure must be boolean")
    unblock_condition = disposition.get("unblock_condition")
    if unblock_condition is not None and not isinstance(unblock_condition, str):
        errors.append("unblock_condition must be a string or null")
    _require_non_empty(disposition.get("evidence_ref"), "evidence_ref", errors)

    if disposition.get("disposition") == "required-now":
        if disposition.get("blocks_parent_closure") is not True:
            errors.append("required-now follow-up must block parent closure")
        if disposition.get("next_action") != "dispatch":
            errors.append("required-now follow-up next_action must be dispatch")
        if not disposition.get("unblock_condition"):
            errors.append("required-now follow-up requires unblock_condition")
        if for_parent_closure and not disposition.get("child_issue"):
            errors.append("required-now follow-up requires child_issue before parent closure")
    if disposition.get("disposition") == "deferred":
        if disposition.get("blocks_parent_closure") is not False:
            errors.append("deferred follow-up must not block parent closure")
        if disposition.get("next_action") != "defer":
            errors.append("deferred follow-up next_action must be defer")
    if (
        disposition.get("disposition") == "duplicate"
        and disposition.get("next_action") != "close-duplicate"
    ):
        errors.append("duplicate follow-up next_action must be close-duplicate")
    if disposition.get("disposition") == "no-action" and disposition.get("next_action") != "none":
        errors.append("no-action follow-up next_action must be none")
    return errors


def validate_parent_closure_followups(followups: Sequence[dict[str, Any]]) -> list[str]:
    """Fail closed if required-now follow-ups lack child issues or unblock conditions."""
    errors: list[str] = []
    for index, followup in enumerate(followups):
        for error in validate_followup_disposition(followup, for_parent_closure=True):
            errors.append(f"followups[{index}]: {error}")
    return errors


def _disposition(
    *,
    disposition: str,
    reason: str,
    owner_or_lane: str,
    parent_issue: str,
    child_issue: str | None,
    blocks_parent_closure: bool,
    unblock_condition: str | None,
    next_action: str,
    evidence_ref: str,
    title: str,
    summary: str,
    wi_handoff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet: dict[str, Any] = {
        "schema_version": FOLLOWUP_DISPOSITION_SCHEMA_VERSION,
        "disposition": disposition,
        "reason": reason,
        "owner_or_lane": owner_or_lane,
        "parent_issue": parent_issue,
        "child_issue": child_issue,
        "blocks_parent_closure": blocks_parent_closure,
        "unblock_condition": unblock_condition,
        "next_action": next_action,
        "evidence_ref": evidence_ref,
        "title": title,
        "summary": summary,
    }
    if wi_handoff is not None:
        packet["wi_handoff"] = wi_handoff
    errors = validate_followup_disposition(packet, for_parent_closure=False)
    if errors:
        raise ValueError("Invalid follow-up disposition: " + "; ".join(errors))
    return packet


def _first_non_empty(*values: Any) -> str:
    for value in values:
        cleaned = _clean_optional(value)
        if cleaned:
            return cleaned
    return "unspecified"


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _lane(value: Any, *, default: str) -> str:
    cleaned = _clean_optional(value) or default
    return cleaned if cleaned in FOLLOWUP_OWNER_LANES else default


def _issue_url_from_record(repo: str, issue: dict[str, Any] | None) -> str | None:
    if not isinstance(issue, dict):
        return None
    url = _clean_optional(issue.get("url"))
    if url:
        return url
    number = issue.get("number")
    if isinstance(number, int) and not isinstance(number, bool) and number > 0:
        return issue_ref(repo, number)
    return None


def _require_non_empty(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty string")


def _require_issue_url(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not _GITHUB_ISSUE_URL_RE.match(value):
        errors.append(f"{field} must be a GitHub issue URL")
