"""Tests for runtime/receipts/plan_core.py"""

import re

import pytest

from runtime.receipts.plan_core import (
    assert_no_floats,
    canonicalize_plan_core,
    compute_plan_core_sha256,
)
from runtime.util.canonical import canonical_json

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def test_canonicalize_deterministic(sample_plan_core_dict):
    d = sample_plan_core_dict
    b1 = canonicalize_plan_core(d)
    # Different key order dict
    d2 = dict(reversed(list(d.items())))
    b2 = canonicalize_plan_core(d2)
    assert b1 == b2


def test_canonicalize_rejects_floats():
    with pytest.raises(ValueError, match="Float"):
        assert_no_floats({"a": 1.5})


def test_canonicalize_rejects_nested_floats():
    with pytest.raises(ValueError, match="Float"):
        assert_no_floats({"a": {"b": [1, 2.0]}})


def test_compute_sha256_format(sample_plan_core_dict):
    h = compute_plan_core_sha256(sample_plan_core_dict)
    assert SHA256_PATTERN.match(h), f"Bad SHA256 format: {h!r}"


def test_compute_sha256_deterministic(sample_plan_core_dict):
    h1 = compute_plan_core_sha256(sample_plan_core_dict)
    h2 = compute_plan_core_sha256(sample_plan_core_dict)
    assert h1 == h2


def test_compute_sha256_differs_on_change(sample_plan_core_dict):
    h1 = compute_plan_core_sha256(sample_plan_core_dict)
    modified = {**sample_plan_core_dict, "plan_id": "plan-DIFFERENT"}
    h2 = compute_plan_core_sha256(modified)
    assert h1 != h2


def test_canonicalize_matches_canonical_json(sample_plan_core_dict):
    result = canonicalize_plan_core(sample_plan_core_dict)
    expected = canonical_json(sample_plan_core_dict)
    assert result == expected


def test_resolve_tree_oid_returns_40_hex(monkeypatch):
    import subprocess

    import runtime.receipts.plan_core as pc

    fake_oid = "a" * 40

    class FakeResult:
        returncode = 0
        stdout = fake_oid + "\n"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    result = pc.resolve_tree_oid("abc1234")
    assert result == fake_oid
    assert re.match(r"^[0-9a-f]{40}$", result)


def test_resolve_tree_oid_fails_closed(monkeypatch):
    import subprocess

    import runtime.receipts.plan_core as pc

    class FakeResult:
        returncode = 1
        stdout = ""
        stderr = "fatal: bad object"

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    with pytest.raises(ValueError, match="git show failed"):
        pc.resolve_tree_oid("badhash")
