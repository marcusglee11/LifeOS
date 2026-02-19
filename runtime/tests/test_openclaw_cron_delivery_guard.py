from runtime.tools.openclaw_cron_delivery_guard import evaluate_jobs


def test_require_parked_blocks_enabled_non_none_delivery():
    jobs = [
        {
            "id": "1",
            "name": "burnin-probe-t-30m",
            "enabled": True,
            "request": {"delivery": {"mode": "announce"}},
        }
    ]
    result = evaluate_jobs(jobs, require_parked=True)
    assert result["pass"] is False
    assert result["violations"]
    assert "delivery.mode=announce" in result["violations"][0]


def test_non_parked_mode_allows_metadata_payload():
    jobs = [
        {
            "id": "1",
            "name": "burnin-probe-u-60m",
            "enabled": True,
            "request": {
                "delivery": {
                    "mode": "announce",
                    "payload": {
                        "status": "ok",
                        "summary": "probe-u ok",
                        "sources": ["probes/run#1"],
                        "counts": {"success": 1},
                    },
                }
            },
        }
    ]
    result = evaluate_jobs(jobs, require_parked=False)
    assert result["pass"] is True
    assert result["violations"] == []


def test_non_parked_mode_blocks_contentful_payload():
    jobs = [
        {
            "id": "1",
            "name": "coo-brief-trial",
            "enabled": True,
            "request": {
                "delivery": {
                    "mode": "announce",
                    "payload": "TOP_3_ACTIONS:\n- ...",
                }
            },
        }
    ]
    result = evaluate_jobs(jobs, require_parked=False)
    assert result["pass"] is False
    assert result["violations"]
    assert "classified contentful" in result["violations"][0]
