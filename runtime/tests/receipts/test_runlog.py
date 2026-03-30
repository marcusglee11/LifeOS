"""Tests for runtime/receipts/runlog.py"""

import json

from runtime.receipts.runlog import RunLogEmitter


def test_emit_auto_seq():
    emitter = RunLogEmitter(phase_order=["init", "build"])
    e1 = emitter.emit("init", "s1", "start")
    e2 = emitter.emit("build", "s2", "end")
    assert e1.seq == 0
    assert e2.seq == 1


def test_emit_validates_required_fields():
    emitter = RunLogEmitter(phase_order=["init"])
    # This should not raise -- valid emit
    emitter.emit("init", "s1", "start")


def test_events_sorted_by_phase_order():
    emitter = RunLogEmitter(phase_order=["alpha", "beta", "gamma"])
    # Emit in reverse order
    emitter.emit("gamma", "s3", "event")
    emitter.emit("alpha", "s1", "event")
    emitter.emit("beta", "s2", "event")
    events = emitter.events()
    phases = [e.phase for e in events]
    assert phases == ["alpha", "beta", "gamma"], f"Expected phase order, got: {phases}"


def test_events_sorted_full_key():
    emitter = RunLogEmitter(phase_order=["p1", "p2"])
    emitter.emit("p2", "b", "e", attempt_num=1)
    emitter.emit("p1", "b", "e", attempt_num=0)
    emitter.emit("p1", "a", "e", attempt_num=0)
    events = emitter.events()
    keys = [(e.phase, e.step_id, e.attempt_num) for e in events]
    assert keys == [("p1", "a", 0), ("p1", "b", 0), ("p2", "b", 1)]


def test_write_jsonl_valid_lines(tmp_path):
    emitter = RunLogEmitter(phase_order=["init"])
    emitter.emit("init", "s1", "start")
    emitter.emit("init", "s2", "end")
    path = tmp_path / "runlog.jsonl"
    emitter.write_jsonl(path)
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert "phase" in obj
        assert "step_id" in obj
        assert "event_type" in obj


def test_deterministic_content_strips_timestamps():
    emitter = RunLogEmitter(phase_order=["init"])
    emitter.emit("init", "s1", "start")
    content = emitter.deterministic_content()
    for item in content:
        assert "timestamp" not in item


def test_deterministic_content_identical():
    def make_emitter():
        emitter = RunLogEmitter(phase_order=["init", "build"])
        emitter.emit("init", "s1", "start")
        emitter.emit("build", "s2", "compile")
        return emitter

    e1 = make_emitter()
    e2 = make_emitter()
    assert e1.deterministic_content() == e2.deterministic_content()


def test_empty_emitter_writes_empty_file(tmp_path):
    emitter = RunLogEmitter(phase_order=["init"])
    path = tmp_path / "empty.jsonl"
    emitter.write_jsonl(path)
    content = path.read_text()
    assert content == ""
