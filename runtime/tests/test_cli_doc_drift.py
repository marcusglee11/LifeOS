"""
CLI Doc Drift Tests — verify that documented CLI commands either exist
in runtime/cli.py or are explicitly marked as not-yet-implemented.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_cli_source() -> str:
    return (REPO_ROOT / "runtime/cli.py").read_text(encoding="utf-8")


class TestCoreSpecCliAccuracy:
    """Verify COO_Runtime_Core_Spec_v1.0.md CLI section."""

    def _read_spec(self) -> str:
        return (REPO_ROOT / "docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md").read_text(
            encoding="utf-8"
        )

    def test_unimplemented_commands_are_marked(self):
        """Commands not in cli.py must be marked [NOT YET IMPLEMENTED]."""
        spec = self._read_spec()
        cli = _read_cli_source()

        # Commands documented in spec that don't exist in cli.py
        missing_commands = ["coo orchestrator", "coo chat", "coo logs", "coo dlq", "coo metrics"]
        for cmd in missing_commands:
            # Find lines referencing this command
            for i, line in enumerate(spec.splitlines(), 1):
                if cmd in line and "NOT YET IMPLEMENTED" not in line:
                    # Check if the command actually exists in cli.py
                    subcmd = cmd.replace("coo ", "")
                    if f'"{subcmd}"' not in cli and f"'{subcmd}'" not in cli:
                        raise AssertionError(
                            f"Line {i}: '{cmd}' documented but not in cli.py "
                            f"and not marked [NOT YET IMPLEMENTED]"
                        )

    def test_implemented_commands_are_not_marked_unimplemented(self):
        spec = self._read_spec()

        for i, line in enumerate(spec.splitlines(), 1):
            if "coo chat" in line and "NOT YET IMPLEMENTED" in line:
                raise AssertionError(
                    f"Line {i}: 'coo chat' exists in cli.py but is still marked [NOT YET IMPLEMENTED]"
                )


class TestWalkthroughCliAccuracy:
    """Verify COO_Runtime_Walkthrough_v1.0.md CLI section."""

    def _read_walkthrough(self) -> str:
        return (REPO_ROOT / "docs/03_runtime/COO_Runtime_Walkthrough_v1.0.md").read_text(
            encoding="utf-8"
        )

    def test_unimplemented_walkthrough_commands_marked(self):
        """Walkthrough commands not in cli.py must be marked."""
        walkthrough = self._read_walkthrough()
        cli = _read_cli_source()

        missing_commands = ["coo logs", "coo dlq-replay", "coo resume"]
        for cmd in missing_commands:
            for i, line in enumerate(walkthrough.splitlines(), 1):
                if cmd in line and "NOT YET IMPLEMENTED" not in line:
                    subcmd = cmd.replace("coo ", "")
                    if f'"{subcmd}"' not in cli and f"'{subcmd}'" not in cli:
                        raise AssertionError(
                            f"Line {i}: '{cmd}' in walkthrough but not in cli.py "
                            f"and not marked [NOT YET IMPLEMENTED]"
                        )
