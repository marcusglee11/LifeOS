"""Tests for runtime/receipts/ulid.py"""

import re

from runtime.receipts.ulid import generate_ulid

ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
EXCLUDED_CHARS = set("ILOU")


def test_ulid_format_matches_pattern():
    ulid = generate_ulid()
    assert ULID_PATTERN.match(ulid), f"ULID {ulid!r} doesn't match pattern"


def test_ulid_uniqueness():
    ulids = {generate_ulid() for _ in range(100)}
    assert len(ulids) == 100, "Expected 100 unique ULIDs"


def test_ulid_time_sortable():
    import time

    ulid1 = generate_ulid()
    time.sleep(0.002)  # ensure ms tick
    ulid2 = generate_ulid()
    assert ulid1 < ulid2, f"Expected {ulid1!r} < {ulid2!r} (time-sortable)"


def test_ulid_crockford_alphabet():
    for _ in range(20):
        ulid = generate_ulid()
        chars = set(ulid)
        bad = chars & EXCLUDED_CHARS
        assert not bad, f"ULID {ulid!r} contains excluded chars: {bad}"
