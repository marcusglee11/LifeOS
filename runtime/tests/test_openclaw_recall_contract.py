from runtime.tools.openclaw_recall_contract import (
    build_contract_response,
    is_recall_intent,
    parse_sources,
)


def test_recall_intent_detected():
    assert is_recall_intent("what did we decide last week?")
    assert is_recall_intent("please recall the decision")
    assert not is_recall_intent("say hello")


def test_sources_parsed_from_memory_search_output():
    output = """
0.854 memory/daily/2026-02-10.md:1-5
snippet text
0.458 MEMORY.md:1-10
"""
    sources = parse_sources(output)
    assert sources == ["memory/daily/2026-02-10.md:1-5", "MEMORY.md:1-10"]


def test_contract_response_includes_sources_for_recall_with_hits():
    output = "0.854 memory/daily/2026-02-10.md:1-5\n"
    result = build_contract_response("what did we decide last week?", output)
    assert result["recall_intent"] is True
    assert result["hit_count"] == 1
    assert "Sources:" in result["response"]
    assert "memory/daily/2026-02-10.md:1-5" in result["response"]


def test_contract_response_fails_closed_for_no_hits():
    result = build_contract_response("what did we decide last week?", "")
    assert result["recall_intent"] is True
    assert result["hit_count"] == 0
    assert result["response"] == "No grounded memory found. Which timeframe or document should I check?"
