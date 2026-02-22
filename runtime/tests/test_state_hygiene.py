"""
State Hygiene Tests — verify canonical state docs are internally consistent.

These tests read LIFEOS_STATE.md and LifeOS_Master_Execution_Plan_v1.1.md
and assert that known-resolved items are not still listed as open blockers.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestBlockersAccuracy:
    """Verify LIFEOS_STATE.md blockers section reflects reality."""

    def _read_state(self) -> str:
        return (REPO_ROOT / "docs/11_admin/LIFEOS_STATE.md").read_text(encoding="utf-8")

    def test_no_pyyaml_blocker(self):
        """PyYAML 6.0.3 is installed; blocker should be closed."""
        content = self._read_state()
        assert "missing `PyYAML`" not in content, (
            "Stale blocker: PyYAML is installed (6.0.3). Remove from blockers section."
        )

    def test_no_auto_commit_blocker(self):
        """Auto-commit works in recent merges; blocker should be closed."""
        content = self._read_state()
        assert "Auto-commit integration gap" not in content, (
            "Stale blocker: auto-commit works (see 8f6287e, adab507). Remove from blockers."
        )

    def test_no_free_model_blocker(self):
        """Zen paid routing merged; free model blocker should be closed."""
        content = self._read_state()
        assert "Free OpenCode models" not in content, (
            "Stale blocker: Zen paid routing merged (adab507). Remove from blockers."
        )

    def test_blockers_section_is_clean(self):
        """After cleanup, blockers section should say 'None' or list only real blockers."""
        content = self._read_state()
        # Find the blockers section
        match = re.search(
            r"## ⚠️ System Blockers.*?\n---",
            content,
            re.DOTALL,
        )
        assert match, "Could not find System Blockers section in LIFEOS_STATE.md"
        section = match.group(0)
        # Should not have numbered items (all resolved)
        assert "1." not in section or "None" in section, (
            "Blockers section still has numbered items. Update to reflect resolved state."
        )


class TestPlanAccuracy:
    """Verify execution plan matches known completion status."""

    def _read_plan(self) -> str:
        return (REPO_ROOT / "docs/11_admin/LifeOS_Master_Execution_Plan_v1.1.md").read_text(
            encoding="utf-8"
        )

    def test_w5_t02_marked_done(self):
        """W5-T02 checkpoint/resume proof completed 2026-02-19."""
        content = self._read_plan()
        # Should NOT still say OPEN for W5 T02
        found_w5_t02 = False
        lines = content.splitlines()
        for line in lines:
            if "W5" in line and "T02" in line:
                found_w5_t02 = True
                assert "OPEN" not in line, (
                    f"W5-T02 still marked OPEN in plan but was completed 2026-02-19. Line: {line}"
                )
                break
        assert found_w5_t02, "Could not find W5-T02 row in execution plan."
