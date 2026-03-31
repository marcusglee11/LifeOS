from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from scripts.run_certification import (
    CommandSpec,
    classify_skip,
    determine_state,
    ignored_suites_from_pyproject,
    load_profiles,
    run_suite,
    suite_profile_map,
)


def test_load_profiles_contains_expected_suite_entries():
    config = load_profiles()
    profile_map = suite_profile_map(config)
    assert profile_map["tests_recursive/test_steward_runner.py"]["profile"] == "ci"
    assert profile_map["runtime/tests/test_opencode_stage1_5_live.py"]["profile"] == "live"


def test_ignored_suites_are_all_classified():
    config = load_profiles()
    profile_map = suite_profile_map(config)
    for ignored in ignored_suites_from_pyproject():
        assert ignored in profile_map


def test_classify_skip_matches_exact_test_nodeid():
    config = load_profiles()
    classified = classify_skip(
        "runtime/tests/orchestration/missions/test_bypass_dogfood.py::test_plan_bypass_activation",
        "LIFEOS_TODO[P1] bypass path not yet implemented in autonomous_build_cycle.py",
        config,
    )
    assert classified is None


def test_classify_skip_matches_dotted_class_nodeid():
    config = load_profiles()
    classified = classify_skip(
        "runtime.tests.test_doc_hygiene.TestDocHygieneMarkdownLint::test_missing_markdownlint_dependency",
        "LIFEOS_TODO[P2] markdownlint dependency path not yet implemented",
        config,
    )
    assert classified is None


def test_classify_skip_matches_reason_pattern():
    config = load_profiles()
    classified = classify_skip(
        "runtime/tests/test_tool_policy.py::test_foo",
        "Symlinks not supported on this platform",
        config,
    )
    assert classified is not None
    assert classified["classification"] == "platform"


def test_classify_skip_matches_case_insensitive_live_pattern():
    config = load_profiles()
    classified = classify_skip(
        "runtime/tests/test_opencode_stage1_5_live.py::test_live_stage1_5",
        "Requires ZEN_BUILDER_KEY to run live stage 1.5 coverage",
        config,
    )
    assert classified is not None
    assert classified["classification"] == "live_only"


def test_run_suite_handles_malformed_junit_xml(monkeypatch, tmp_path: Path):
    def fake_named_temporary_file(*args, **kwargs):
        class _TmpFile:
            def __init__(self, path: Path):
                self.name = str(path)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return _TmpFile(tmp_path / "broken.xml")

    def fake_subprocess_run(command, cwd, capture_output, text, check):
        junit_path = Path(command[-1])
        junit_path.write_text("<testsuite>", encoding="utf-8")
        return Mock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "scripts.run_certification.tempfile.NamedTemporaryFile", fake_named_temporary_file
    )
    monkeypatch.setattr("scripts.run_certification.subprocess.run", fake_subprocess_run)

    suite_result, counts, observed_skips, passed = run_suite(
        CommandSpec(
            path="runtime/tests",
            profile="local",
            command=["python3", "-m", "pytest", "runtime/tests", "-q"],
            kind="pytest",
        )
    )

    assert suite_result["status"] == "fail"
    assert "parse_error" in suite_result
    assert counts == {"passed": 0, "failed": 0, "skipped": 0}
    assert observed_skips == []
    assert passed is False


def test_determine_state_transitions():
    assert determine_state("local", blocking=True, non_blocking=False) == "red"
    assert determine_state("local", blocking=False, non_blocking=True) == "candidate"
    assert determine_state("local", blocking=False, non_blocking=False) == "prod_local"
    assert determine_state("ci", blocking=False, non_blocking=False) == "prod_ci"
    assert (
        determine_state("live", blocking=False, non_blocking=False, previous_state="prod_ci")
        == "prod_ci"
    )
    assert (
        determine_state("live", blocking=False, non_blocking=False, previous_state=None)
        == "candidate"
    )
