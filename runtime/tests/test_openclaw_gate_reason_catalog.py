from pathlib import Path

from runtime.tools.openclaw_gate_reason_catalog import classify_reasons, load_catalog


def test_load_catalog_and_classify(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        '{"reasons":{"policy_assert_failed":{"severity":"drift","drift_bypassable":true},"leak_scan_failed":{"severity":"hard","drift_bypassable":false}}}\n',
        encoding="utf-8",
    )

    catalog = load_catalog(catalog_path)
    bypassable, hard, unknown = classify_reasons(
        ["policy_assert_failed", "leak_scan_failed"], catalog
    )
    assert bypassable == ["policy_assert_failed"]
    assert hard == ["leak_scan_failed"]
    assert unknown == []


def test_unknown_reason_is_hard_block(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        '{"reasons":{"policy_assert_failed":{"severity":"drift","drift_bypassable":true}}}\n',
        encoding="utf-8",
    )

    catalog = load_catalog(catalog_path)
    bypassable, hard, unknown = classify_reasons(["not_known_reason"], catalog)
    assert bypassable == []
    assert hard == ["not_known_reason"]
    assert unknown == ["not_known_reason"]
