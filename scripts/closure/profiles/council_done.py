
from .step_gate_closure import validate_profile as base_validate

# Re-export strict class?
# No, we just implement validate_profile

def validate_profile(manifest, zf):
    failures = []
    # 1. Must have a Ruling artifact
    evidence = manifest.get("evidence", [])
    has_ruling = False
    for ev in evidence:
        path = ev.get("path", "")
        if "Ruling" in path and path.endswith(".md"):
            has_ruling = True
            break
    
    if not has_ruling:
        failures.append({
            "code": "COUNCIL_RULING_MISSING",
            "message": "Bundle must contain a Council Ruling artifact (*Ruling*.md)",
            "path": "evidence"
        })
        
    return failures
