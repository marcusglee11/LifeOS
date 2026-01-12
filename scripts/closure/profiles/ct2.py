
def validate_profile(manifest, zf):
    failures = []
    evidence = manifest.get("evidence", [])
    
    # Check for evidence map
    has_map = any(ev.get("role") == "inventory" or "evidence_map" in ev.get("path", "") for ev in evidence)
    
    if not has_map:
        failures.append({
            "code": "CT2_EVIDENCE_MAP_MISSING",
            "message": "CT2 Activation requires an evidence map or inventory",
            "path": "evidence"
        })
        
    return failures
