from runtime.tools.openclaw_egress_policy import classify_payload, classify_payload_text


def test_metadata_payload_is_allowed_for_scheduled():
    payload = {
        "status": "ok",
        "summary": "probe completed",
        "sources": ["probes/burnin-probe-t-30m#run-123"],
        "counts": {"success": 1, "failure": 0},
    }
    result = classify_payload(payload)
    assert result["classification"] == "metadata_only"
    assert result["allowed_for_scheduled"] is True
    assert result["reasons"] == []


def test_payload_with_extra_content_field_is_blocked():
    payload = {
        "status": "ok",
        "summary": "probe completed",
        "sources": [],
        "counts": {},
        "content": "raw memory excerpt",
    }
    result = classify_payload(payload)
    assert result["classification"] == "contentful"
    assert result["allowed_for_scheduled"] is False
    assert any("extra_keys" in reason for reason in result["reasons"])


def test_payload_text_not_json_is_blocked():
    result = classify_payload_text("This is a plain narrative response.")
    assert result["classification"] == "contentful"
    assert result["allowed_for_scheduled"] is False
    assert "payload_not_json" in result["reasons"]


def test_multiline_summary_is_blocked():
    payload = {
        "status": "ok",
        "summary": "line 1\nline 2",
        "sources": [],
        "counts": {},
    }
    result = classify_payload(payload)
    assert result["classification"] == "contentful"
    assert result["allowed_for_scheduled"] is False
    assert "summary_not_single_line" in result["reasons"]
