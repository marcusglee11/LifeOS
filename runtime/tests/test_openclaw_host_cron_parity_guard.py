from pathlib import Path

from runtime.tools.openclaw_host_cron_parity_guard import evaluate, parse_managed_entries


def test_parse_and_evaluate_multi_instance_passes(tmp_path: Path) -> None:
    crontab = """
# OPENCLAW_PARITY_BEGIN instance=coo job=curated_sync
*/30 * * * * /home/tester/.openclaw/bin/openclaw_shared_memory_sync_wrapper.sh --instance coo
# OPENCLAW_PARITY_END
# OPENCLAW_PARITY_BEGIN instance=jarda job=raw_sync
*/15 * * * * /home/tester/.openclaw/bin/openclaw_shared_memory_sync_wrapper.sh --instance jarda
# OPENCLAW_PARITY_END
""".strip()

    entries, parse_violations = parse_managed_entries(crontab)
    assert parse_violations == []

    profile = {
        "instance_id": "coo",
        "parity_jobs": [
            {
                "instance_id": "coo",
                "job_type": "curated_sync",
                "schedule": "*/30 * * * *",
                "wrapper_path": "/home/tester/.openclaw/bin/openclaw_shared_memory_sync_wrapper.sh",
            },
            {
                "instance_id": "jarda",
                "job_type": "raw_sync",
                "schedule": "*/15 * * * *",
                "wrapper_path": "/home/tester/.openclaw/bin/openclaw_shared_memory_sync_wrapper.sh",
            },
        ],
    }
    result = evaluate(entries, profile)
    assert result["pass"] is True


def test_duplicate_key_fails() -> None:
    crontab = """
# OPENCLAW_PARITY_BEGIN instance=coo job=curated_sync
*/30 * * * * /home/tester/.openclaw/bin/openclaw_shared_memory_sync_wrapper.sh --instance coo
# OPENCLAW_PARITY_END
# OPENCLAW_PARITY_BEGIN instance=coo job=curated_sync
*/30 * * * * /home/tester/.openclaw/bin/openclaw_shared_memory_sync_wrapper.sh --instance coo
# OPENCLAW_PARITY_END
""".strip()

    entries, parse_violations = parse_managed_entries(crontab)
    assert parse_violations == []
    result = evaluate(entries, {"instance_id": "coo", "parity_jobs": []})
    assert result["pass"] is False
    assert any("duplicate_entry_key" in v for v in result["violations"])


def test_schedule_mismatch_fails() -> None:
    crontab = """
# OPENCLAW_PARITY_BEGIN instance=coo job=curated_sync
*/15 * * * * /home/tester/.openclaw/bin/openclaw_shared_memory_sync_wrapper.sh --instance coo
# OPENCLAW_PARITY_END
""".strip()

    entries, parse_violations = parse_managed_entries(crontab)
    assert parse_violations == []
    profile = {
        "instance_id": "coo",
        "parity_jobs": [
            {
                "instance_id": "coo",
                "job_type": "curated_sync",
                "schedule": "*/30 * * * *",
                "wrapper_path": "/home/tester/.openclaw/bin/openclaw_shared_memory_sync_wrapper.sh",
            }
        ],
    }
    result = evaluate(entries, profile)
    assert result["pass"] is False
    assert any("schedule_mismatch" in v for v in result["violations"])
