import zipfile
import os

def zip_files(zip_name, items):
    print(f"Creating {zip_name}...")
    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as z:
            for src, arc_name in items:
                if os.path.isdir(src):
                    for root, dirs, files in os.walk(src):
                        if '__pycache__' in root: continue
                        for f in files:
                            fp = os.path.join(root, f)
                            rel = os.path.relpath(fp, src)
                            z.write(fp, os.path.join(arc_name, rel))
                elif os.path.exists(src):
                    z.write(src, arc_name)
                else:
                    print(f"Warning: Missing {src}")
    except Exception as e:
        print(f"Failed to create {zip_name}: {e}")

# 1. Context Pack
context_items = [
    ("docs/99_archive/legacy_structures/Governance/Council_Protocol_v1.0.md", "Council_Protocol_v1.0.md"),
    ("docs/99_archive/AI_Council_Procedural_Spec_v1.0.md", "AI_Council_Procedural_Spec_v1.0.md"),
    ("docs/01_governance/ALIGNMENT_REVIEW_TEMPLATE_v1.0.md", "Reviewer_Output_Template.md"),
    ("docs/09_prompts/v1.2/reviewer_architect_v1.2.md", "reviewer_architect_v1.2.md"),
    ("docs/09_prompts/v1.2/reviewer_risk_adversarial_v1.2.md", "reviewer_risk_adversarial_v1.2.md"),
    ("docs/09_prompts/v1.2/reviewer_testing_v1.2.md", "reviewer_testing_v1.2.md"),
    ("docs/09_prompts/v1.2/reviewer_governance_v1.2.md", "reviewer_governance_v1.2.md"),
    ("docs/01_governance/Antigravity_Council_Review_Packet_Spec_v1.1.md", "Antigravity_Council_Review_Packet_Spec_v1.1.md")
]
zip_files("artifacts/bundles/COUNCIL_CONTEXT_PACK_v1.zip", context_items)

# 2. Impl Packet
impl_items = [
    ("runtime/governance", "governance"),
    ("config/policy", "policy_config"),
    ("runtime/tests/orchestration/loop/test_policy.py", "tests/test_policy.py"),
    ("runtime/tests/test_tool_policy.py", "tests/test_tool_policy.py"),
    ("artifacts/bundles/policy_engine_test_evidence.log", "evidence/policy_engine_test_evidence.log")
]
zip_files("artifacts/bundles/COUNCIL_PACKET_Policy_Engine_Impl_v1.zip", impl_items)
print("Packets created.")
