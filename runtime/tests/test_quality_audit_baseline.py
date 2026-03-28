from __future__ import annotations

from scripts.workflow.run_quality_audit_baseline import (
    append_exit_footer,
    classify_disposition,
    expand_subsystems,
    extract_exit_code,
    finding_count,
    known_pytest_failure,
    nonempty_lines,
    representative_examples,
    runtime_baseline_status,
)


def test_extract_exit_code_reads_footer() -> None:
    output = "line one\nline two\nEXIT_CODE=17\n"
    assert extract_exit_code(output) == 17


def test_nonempty_lines_ignores_exit_footer_and_blanks() -> None:
    output = "\nwarning one\n\nEXIT_CODE=1\n"
    assert nonempty_lines(output) == ["warning one"]


def test_nonempty_lines_ignores_timeout_footer() -> None:
    output = "warning one\nTIMEOUT_SECONDS=300\nEXIT_CODE=124\n"
    assert nonempty_lines(output) == ["warning one"]


def test_finding_count_zero_when_command_passes() -> None:
    output = "all good\nEXIT_CODE=0\n"
    assert finding_count(output, 0) == 0


def test_finding_count_counts_nonempty_output_lines_on_failure() -> None:
    output = "issue one\nissue two\nEXIT_CODE=1\n"
    assert finding_count(output, 1) == 2


def test_representative_examples_limits_output() -> None:
    output = "a\nb\nc\nd\nEXIT_CODE=1\n"
    assert representative_examples(output, limit=2) == ["a", "b"]


def test_classify_disposition_marks_opencode_governance_for_rescope() -> None:
    assert classify_disposition("ruff_check", "opencode_governance", 1, "packaged_but_not_in_manifest") == "exclude_or_rescope"


def test_expand_subsystems_splits_governed_python_roots() -> None:
    assert expand_subsystems("runtime+doc_steward+recursive_kernel+project_builder") == [
        "runtime",
        "doc_steward",
        "recursive_kernel",
        "project_builder",
    ]


def test_classify_disposition_marks_success_as_blocking_ready() -> None:
    assert classify_disposition("ruff_check", "runtime", 0, "") == "blocking_ready"


def test_classify_disposition_defaults_failure_to_advisory_keep() -> None:
    assert classify_disposition("mypy", "runtime", 1, "") == "advisory_keep"


def test_known_pytest_failure_extracts_first_failed_nodeid() -> None:
    output = (
        "some setup\n"
        "FAILED runtime/tests/orchestration/coo/test_promotion_fixtures.py::test_all_promotion_fixtures\n"
        "more text\n"
    )
    assert (
        known_pytest_failure(output)
        == "runtime/tests/orchestration/coo/test_promotion_fixtures.py::test_all_promotion_fixtures"
    )


def test_append_exit_footer_adds_timeout_and_exit_code() -> None:
    output = append_exit_footer("partial output", exit_code=124, timeout_seconds=300)
    assert output.endswith("TIMEOUT_SECONDS=300\nEXIT_CODE=124\n")


def test_runtime_baseline_status_reports_timeout() -> None:
    output = "partial output\nTIMEOUT_SECONDS=300\nEXIT_CODE=124\n"
    assert runtime_baseline_status(output) == "timed out after 300 second(s) before first failure"


def test_runtime_baseline_status_reports_pass() -> None:
    assert runtime_baseline_status("ok\nEXIT_CODE=0\n") == "passed within audit budget"
