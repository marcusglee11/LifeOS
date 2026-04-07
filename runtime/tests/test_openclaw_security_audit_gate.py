from runtime.tools.openclaw_security_audit_gate import assess_security_audit_text


def test_accepts_clean_audit_without_warnings() -> None:
    result = assess_security_audit_text(
        "OpenClaw security audit\nSummary: 0 critical · 0 warn\n",
    )
    assert result.clean is True
    assert result.warn_codes == ()


def test_accepts_gateway_probe_warning() -> None:
    result = assess_security_audit_text(
        "\n".join(
            [
                "OpenClaw security audit",
                "Summary: 0 critical · 1 warn",
                "",
                "WARN",
                "gateway.probe_failed Gateway probe failed (deep)",
            ]
        )
        + "\n",
    )
    assert result.clean is True
    assert result.warn_codes == ("gateway.probe_failed",)


def test_accepts_combined_benign_warnings_when_multiuser_allowed() -> None:
    result = assess_security_audit_text(
        "\n".join(
            [
                "OpenClaw security audit",
                "Summary: 0 critical · 2 warn · 1 info",
                "",
                "WARN",
                "security.trust_model.multi_user_heuristic Shared gateway detected",
                "gateway.probe_failed Gateway probe failed (deep)",
                "",
                "INFO",
                "summary.attack_surface Attack surface summary",
            ]
        )
        + "\n",
        allow_multiuser_heuristic=True,
    )
    assert result.clean is True
    assert result.warn_codes == (
        "security.trust_model.multi_user_heuristic",
        "gateway.probe_failed",
    )


def test_rejects_combined_benign_warnings_when_multiuser_not_allowed() -> None:
    result = assess_security_audit_text(
        "\n".join(
            [
                "OpenClaw security audit",
                "Summary: 0 critical · 2 warn",
                "",
                "WARN",
                "security.trust_model.multi_user_heuristic Shared gateway detected",
                "gateway.probe_failed Gateway probe failed (deep)",
            ]
        )
        + "\n",
    )
    assert result.clean is False
    assert result.unexpected_warn_codes == ("security.trust_model.multi_user_heuristic",)


def test_rejects_unexpected_warning_code() -> None:
    result = assess_security_audit_text(
        "\n".join(
            [
                "OpenClaw security audit",
                "Summary: 0 critical · 1 warn",
                "",
                "WARN",
                "security.runtime.tool_exposed Unexpected runtime tool",
            ]
        )
        + "\n",
    )
    assert result.clean is False
    assert result.unexpected_warn_codes == ("security.runtime.tool_exposed",)


def test_rejects_critical_findings_when_summary_claims_zero() -> None:
    result = assess_security_audit_text(
        "\n".join(
            [
                "OpenClaw security audit",
                "Summary: 0 critical · 0 warn",
                "",
                "CRITICAL",
                "security.runtime.tool_exposed Unexpected runtime tool",
            ]
        )
        + "\n",
    )
    assert result.clean is False


def test_rejects_summary_warning_count_mismatch() -> None:
    result = assess_security_audit_text(
        "\n".join(
            [
                "OpenClaw security audit",
                "Summary: 0 critical · 2 warn",
                "",
                "WARN",
                "gateway.probe_failed Gateway probe failed (deep)",
            ]
        )
        + "\n",
    )
    assert result.clean is False
    assert result.warn_codes == ("gateway.probe_failed",)


def test_rejects_summary_critical_count_mismatch() -> None:
    result = assess_security_audit_text(
        "\n".join(
            [
                "OpenClaw security audit",
                "Summary: 1 critical · 0 warn",
                "",
                "CRITICAL",
                "security.runtime.tool_exposed Unexpected runtime tool",
                "security.runtime.egress_unbounded Unexpected egress access",
            ]
        )
        + "\n",
    )
    assert result.clean is False


def test_marks_report_unparseable_when_summary_line_missing() -> None:
    result = assess_security_audit_text(
        "\n".join(
            [
                "OpenClaw security audit",
                "",
                "WARN",
                "security.trust_model.multi_user_heuristic Shared gateway detected",
                "[exit_code]=124",
            ]
        )
        + "\n",
        allow_multiuser_heuristic=True,
    )
    assert result.clean is False
    assert result.summary_present is False
    assert result.summary_critical_count is None
    assert result.warn_codes == ()
