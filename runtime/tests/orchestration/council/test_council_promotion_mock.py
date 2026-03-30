from __future__ import annotations

from pathlib import Path

from runtime.orchestration.council.fsm import CouncilFSMv2
from runtime.orchestration.council.models import (
    DECISION_STATUS_NORMAL,
    VERDICT_ACCEPT,
)
from runtime.orchestration.council.policy import load_council_policy, resolve_model_family
from scripts.workflow.run_council_review_coo_unsandboxed_promotion import (
    CCP_PATH,
    build_draft_ruling_markdown,
    build_review_packet_markdown,
    compile_promotion_plan,
    load_promotion_ccp,
)


def test_council_promotion_ccp_compiles_to_t3() -> None:
    policy = load_council_policy()
    ccp = load_promotion_ccp()
    compiled, issues = compile_promotion_plan(ccp, policy)
    core = compiled["core"]

    assert issues == []
    assert core["tier"] == "T3"
    assert "Risk" in core["required_lenses"]
    assert "Governance" in core["required_lenses"]
    assert core["model_assignments"]["Chair"] == "openrouter/minimax/minimax-m2.5"
    assert core["model_assignments"]["Challenger"] == "openrouter/minimax/minimax-m2.5"
    assert core["model_assignments"]["Risk"] == "openrouter/z-ai/glm-5"
    assert core["model_assignments"]["Governance"] == "openrouter/z-ai/glm-5"
    for model in core["model_assignments"].values():
        assert resolve_model_family(model, policy.model_families) not in {"anthropic", "openai"}


def test_council_promotion_mock_v2() -> None:
    policy = load_council_policy()
    ccp = load_promotion_ccp()

    def lens_executor(lens_name, ccp_obj, plan, retry_count):
        return {
            "run_type": plan.run_type,
            "lens_name": lens_name,
            "confidence": "medium",
            "notes": f"{lens_name} mock assessment",
            "operator_view": [f"{lens_name} reviewed the promotion package."],
            "claims": [
                {
                    "claim_id": f"{lens_name.lower()}-01",
                    "statement": f"{lens_name} finds no blocker. [ASSUMPTION]",
                    "evidence_refs": ["ASSUMPTION: mock council output"],
                }
            ],
            "verdict_recommendation": VERDICT_ACCEPT,
            "_actual_model": plan.model_assignments[lens_name],
        }

    fsm = CouncilFSMv2(policy=policy, lens_executor=lens_executor)
    result = fsm.run(ccp)

    assert result.status == "complete"
    assert result.decision_payload["status"] == "COMPLETE"
    assert result.decision_payload["decision_status"] == DECISION_STATUS_NORMAL
    assert result.decision_payload["verdict"] == VERDICT_ACCEPT


def test_promotion_packet_markdown_validates(tmp_path: Path) -> None:
    mock_log = tmp_path / "mock.log"
    live_log = tmp_path / "live.log"
    live_result = tmp_path / "live.json"
    summary = tmp_path / "summary.json"
    draft = tmp_path / "draft.md"
    packet = tmp_path / "packet.md"

    for path in [mock_log, live_log, live_result, summary, draft]:
        path.write_text("x\n", encoding="utf-8")

    packet.write_text(
        build_review_packet_markdown(
            terminal_outcome="PASS",
            mock_log=mock_log,
            live_log=live_log,
            live_result=live_result,
            summary_json=summary,
            draft_ruling=draft,
            ccp_path=CCP_PATH,
            branch="build/coo-unsandboxed-promotion-l3",
            commit="3a31285c",
        ),
        encoding="utf-8",
    )

    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "scripts/validate_review_packet.py", str(packet)],
        cwd=Path(__file__).resolve().parents[4],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_draft_ruling_mentions_required_controls() -> None:
    text = build_draft_ruling_markdown(
        {
            "verdict": VERDICT_ACCEPT,
            "decision_status": DECISION_STATUS_NORMAL,
            "fix_plan": [],
        },
        branch="build/coo-unsandboxed-promotion-l3",
        commit="3a31285c",
    )
    assert "L0`, `L3`, and `L4`" in text
    assert "coo_shared_ingress_burnin.json" in text
    assert "hash-bound" in text
