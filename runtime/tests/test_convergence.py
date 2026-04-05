"""
Tests for council convergence detection.
"""

from runtime.orchestration.council.convergence import (
    _extract_tokens,
    _jaccard_similarity,
    compute_convergence,
)

# ---------------------------------------------------------------------------
# _extract_tokens
# ---------------------------------------------------------------------------


class TestExtractTokens:
    def test_string(self):
        tokens = _extract_tokens("The architecture is sound and secure")
        assert "architecture" in tokens
        assert "sound" in tokens
        assert "secure" in tokens

    def test_dict(self):
        tokens = _extract_tokens(
            {
                "verdict": "Accept",
                "claims": [
                    {"text": "No security issues found"},
                    {"text": "Architecture follows patterns"},
                ],
            }
        )
        assert "accept" in tokens
        assert "security" in tokens
        assert "architecture" in tokens

    def test_skips_underscore_keys(self):
        tokens = _extract_tokens(
            {
                "verdict": "Accept",
                "_actual_model": "claude-sonnet-4-5",
                "_internal": {"debug": "info"},
            }
        )
        assert "accept" in tokens
        assert "claude" not in tokens
        assert "debug" not in tokens

    def test_empty_returns_empty(self):
        assert _extract_tokens(None) == set()
        assert _extract_tokens({}) == set()
        assert _extract_tokens("") == set()

    def test_nested_lists(self):
        tokens = _extract_tokens([["security", "review"], ["architecture"]])
        assert "security" in tokens
        assert "architecture" in tokens


# ---------------------------------------------------------------------------
# _jaccard_similarity
# ---------------------------------------------------------------------------


class TestJaccardSimilarity:
    def test_identical_sets(self):
        s = {"a", "b", "c"}
        assert _jaccard_similarity(s, s) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        a = {"a", "b", "c"}
        b = {"b", "c", "d"}
        # intersection={b,c}=2, union={a,b,c,d}=4 → 0.5
        assert _jaccard_similarity(a, b) == 0.5

    def test_both_empty(self):
        assert _jaccard_similarity(set(), set()) == 1.0

    def test_one_empty(self):
        assert _jaccard_similarity({"a"}, set()) == 0.0


# ---------------------------------------------------------------------------
# compute_convergence
# ---------------------------------------------------------------------------


class TestComputeConvergence:
    def test_identical_outputs(self):
        results = {
            "Architecture": {"verdict": "Accept", "claims": ["sound design"]},
            "Security": {"verdict": "Accept", "claims": ["sound design"]},
        }
        conv = compute_convergence(results)
        assert conv.convergent is True
        assert conv.score == 1.0
        assert conv.lens_count == 2

    def test_completely_different_outputs(self):
        results = {
            "Architecture": {"verdict": "Accept", "claims": ["modular patterns"]},
            "Security": {"verdict": "Reject", "findings": ["critical vulnerability XSS"]},
        }
        conv = compute_convergence(results)
        assert conv.convergent is False
        assert conv.score < 0.5

    def test_partial_agreement(self):
        results = {
            "Architecture": {"verdict": "Accept", "notes": "code follows patterns, tests pass"},
            "Security": {"verdict": "Accept", "notes": "code follows security patterns, no issues"},
            "Governance": {"verdict": "Accept", "notes": "code follows governance patterns"},
        }
        conv = compute_convergence(results)
        # Should have moderate-to-high similarity (shared words like "code", "follows", "patterns")
        assert conv.score > 0.3
        assert conv.lens_count == 3
        assert len(conv.pairwise) == 3  # 3 pairs from 3 lenses

    def test_single_lens(self):
        results = {"Architecture": {"verdict": "Accept"}}
        conv = compute_convergence(results)
        assert conv.convergent is True
        assert conv.score == 1.0

    def test_waived_lenses_excluded(self):
        results = {
            "Architecture": {"verdict": "Accept"},
            "Security": None,  # waived
        }
        conv = compute_convergence(results)
        assert conv.lens_count == 1
        assert conv.convergent is True

    def test_custom_threshold(self):
        results = {
            "Architecture": {"verdict": "Accept", "text": "looks good"},
            "Security": {"verdict": "Accept", "text": "looks fine"},
        }
        # With a very high threshold, even similar outputs may not converge
        compute_convergence(results, threshold=0.99)
        conv_loose = compute_convergence(results, threshold=0.1)
        assert conv_loose.convergent is True
        # The strict one may or may not converge depending on exact similarity

    def test_empty_results(self):
        conv = compute_convergence({})
        assert conv.convergent is True
        assert conv.lens_count == 0

    def test_to_dict(self):
        results = {
            "Architecture": {"verdict": "Accept"},
            "Security": {"verdict": "Accept"},
        }
        conv = compute_convergence(results)
        d = conv.to_dict()
        assert "score" in d
        assert "convergent" in d
        assert "pairwise" in d
        assert "threshold" in d

    def test_pairwise_keys(self):
        results = {
            "Architecture": {"text": "analysis"},
            "Governance": {"text": "analysis"},
            "Security": {"text": "different review"},
        }
        conv = compute_convergence(results)
        # Pairwise keys should be sorted alphabetically
        assert "Architecture|Governance" in conv.pairwise
        assert "Architecture|Security" in conv.pairwise
        assert "Governance|Security" in conv.pairwise
