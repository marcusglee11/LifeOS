from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_SUMMARY_RE = re.compile(
    r"Summary:\s*(?P<critical>\d+)\s+critical(?:\s*·\s*(?P<warn>\d+)\s+warn)?(?:\s*·\s*(?P<info>\d+)\s+info)?",
    re.IGNORECASE,
)
_FINDING_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SEVERITIES = {"CRITICAL": "critical", "WARN": "warn", "INFO": "info"}


@dataclass(frozen=True)
class SecurityAuditAssessment:
    """Result of evaluating an OpenClaw security audit report."""

    clean: bool
    summary_present: bool
    summary_critical_count: int | None
    summary_warn_count: int | None
    warn_codes: tuple[str, ...]
    unexpected_warn_codes: tuple[str, ...]


def _parse_summary_counts(text: str) -> tuple[int, int] | None:
    """Extract critical and warning counts from the audit summary line."""

    match = _SUMMARY_RE.search(text)
    if match is None:
        return None
    critical = int(match.group("critical"))
    warn = int(match.group("warn") or "0")
    return critical, warn


def _extract_codes(text: str, severity: str) -> tuple[str, ...]:
    """Collect top-level finding codes from the named severity section."""

    selected = _SEVERITIES[severity]
    current: str | None = None
    codes: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        maybe_severity = _SEVERITIES.get(line.upper())
        if maybe_severity is not None:
            current = maybe_severity
            continue
        if current != selected:
            continue
        if raw_line[:1].isspace():
            continue
        code = line.split()[0]
        if _FINDING_CODE_RE.match(code):
            codes.append(code)
    return tuple(codes)


def assess_security_audit_text(
    text: str,
    *,
    allow_gateway_probe_warning: bool = True,
    allow_multiuser_heuristic: bool = False,
) -> SecurityAuditAssessment:
    """
    Assess whether an OpenClaw security audit report is acceptable.

    Args:
        text: Full text emitted by the `openclaw security audit` command.
        allow_gateway_probe_warning: Whether to accept `gateway.probe_failed`.
        allow_multiuser_heuristic: Whether to accept the shared-ingress heuristic.

    Returns:
        A structured assessment describing whether the audit is clean enough to pass.
    """

    summary = _parse_summary_counts(text)
    if summary is None:
        return SecurityAuditAssessment(
            clean=False,
            summary_present=False,
            summary_critical_count=None,
            summary_warn_count=None,
            warn_codes=(),
            unexpected_warn_codes=(),
        )

    summary_critical_count, summary_warn_count = summary
    critical_codes = _extract_codes(text, "CRITICAL")
    warn_codes = _extract_codes(text, "WARN")
    allowed_warn_codes: set[str] = set()
    if allow_gateway_probe_warning:
        allowed_warn_codes.add("gateway.probe_failed")
    if allow_multiuser_heuristic:
        allowed_warn_codes.add("security.trust_model.multi_user_heuristic")
    unexpected_warn_codes = tuple(code for code in warn_codes if code not in allowed_warn_codes)
    clean = (
        summary_critical_count == len(critical_codes) == 0
        and summary_warn_count == len(warn_codes)
        and not unexpected_warn_codes
    )
    return SecurityAuditAssessment(
        clean=clean,
        summary_present=True,
        summary_critical_count=summary_critical_count,
        summary_warn_count=summary_warn_count,
        warn_codes=warn_codes,
        unexpected_warn_codes=unexpected_warn_codes,
    )


def assess_security_audit_file(
    path: str | Path,
    *,
    allow_gateway_probe_warning: bool = True,
    allow_multiuser_heuristic: bool = False,
) -> SecurityAuditAssessment:
    """
    Read and assess an OpenClaw security audit report from disk.

    Args:
        path: Audit report path.
        allow_gateway_probe_warning: Whether to accept `gateway.probe_failed`.
        allow_multiuser_heuristic: Whether to accept the shared-ingress heuristic.

    Returns:
        A structured assessment describing whether the audit is clean enough to pass.
    """

    audit_path = Path(path)
    return assess_security_audit_text(
        audit_path.read_text(encoding="utf-8", errors="replace"),
        allow_gateway_probe_warning=allow_gateway_probe_warning,
        allow_multiuser_heuristic=allow_multiuser_heuristic,
    )
