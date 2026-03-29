from __future__ import annotations

from pathlib import Path

from scripts.workflow.run_quality_audit_baseline import (
    CommandSpec,
    append_exit_footer,
    build_finding_matrix,
    capture_command,
    classify_disposition,
    extract_exit_code,
    finding_count,
    known_pytest_failure,
    nonempty_lines,
    representative_examples,
    runtime_baseline_status,
    updated_docs_index_text,
    updated_tech_debt_inventory_text,
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


def test_capture_command_uses_appended_tool_exit_code(tmp_path: Path) -> None:
    output_path = tmp_path / "tool.txt"
    result = capture_command(
        tmp_path,
        f"printf 'problem\\n' > {output_path}; printf '\\nEXIT_CODE=7\\n' >> {output_path}; exit 0",
        output_path,
    )

    assert result["exit_code"] == 7
    assert extract_exit_code(str(result["output"])) == 7


def test_runtime_baseline_status_reports_timeout() -> None:
    output = "partial output\nTIMEOUT_SECONDS=300\nEXIT_CODE=124\n"
    assert runtime_baseline_status(output) == "timed out after 300 second(s) before first failure"


def test_runtime_baseline_status_reports_pass() -> None:
    assert runtime_baseline_status("ok\nEXIT_CODE=0\n") == "passed within audit budget"


def test_build_finding_matrix_keeps_subsystem_specific_output(tmp_path: Path) -> None:
    specs = [
        CommandSpec(
            artifact_name="ruff_check_runtime.txt",
            lane="python_style",
            tool="ruff_check",
            failure_class="ruff_error",
            subsystem="runtime",
            command="ruff check runtime",
        ),
        CommandSpec(
            artifact_name="ruff_check_doc_steward.txt",
            lane="python_style",
            tool="ruff_check",
            failure_class="ruff_error",
            subsystem="doc_steward",
            command="ruff check doc_steward",
        ),
    ]
    outputs = {
        "ruff_check_runtime.txt": {
            "exit_code": 1,
            "output": "runtime/file.py:1: error\nEXIT_CODE=1\n",
        },
        "ruff_check_doc_steward.txt": {
            "exit_code": 1,
            "output": "doc_steward/file.py:1: error\nEXIT_CODE=1\n",
        },
    }

    rows = build_finding_matrix(tmp_path, specs, outputs)

    assert rows[0]["path_or_subsystem"] == "runtime"
    assert rows[0]["representative_examples"] == ["runtime/file.py:1: error"]
    assert rows[1]["path_or_subsystem"] == "doc_steward"
    assert rows[1]["representative_examples"] == ["doc_steward/file.py:1: error"]


def test_build_finding_matrix_omits_examples_for_passing_rows(tmp_path: Path) -> None:
    specs = [
        CommandSpec(
            artifact_name="ruff_check_runtime.txt",
            lane="python_style",
            tool="ruff_check",
            failure_class="ruff_error",
            subsystem="runtime",
            command="ruff check runtime",
        )
    ]
    outputs = {
        "ruff_check_runtime.txt": {
            "exit_code": 0,
            "output": "informational output\nEXIT_CODE=0\n",
        }
    }

    rows = build_finding_matrix(tmp_path, specs, outputs)

    assert rows[0]["finding_count"] == 0
    assert rows[0]["representative_examples"] == []


def test_updated_docs_index_text_preserves_timestamp_when_row_exists() -> None:
    original = (
        "# Index\n\n"
        "Last Updated: 2026-03-28\n\n"
        "| Document | Purpose |\n"
        "|----------|---------|\n"
        "| [TECH_DEBT_INVENTORY.md](./11_admin/TECH_DEBT_INVENTORY.md) | Debt |\n"
        "| [QUALITY_AUDIT_BASELINE_v1.0.md](./11_admin/QUALITY_AUDIT_BASELINE_v1.0.md) | Audit |\n"
    )

    updated = updated_docs_index_text(original)

    assert updated == original


def test_updated_tech_debt_inventory_text_is_idempotent_when_reference_exists() -> None:
    original = (
        "# Tech Debt Inventory\n\n"
        "## Audit References\n\n"
        "- [QUALITY_AUDIT_BASELINE_v1.0.md](./QUALITY_AUDIT_BASELINE_v1.0.md) — repo-wide quality baseline audit.\n"
    )

    updated = updated_tech_debt_inventory_text(original)

    assert updated == original
