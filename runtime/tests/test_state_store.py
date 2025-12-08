import pytest
import os
import shutil
from runtime.state_store import StateStore

@pytest.fixture
def store(tmpdir):
    path = str(tmpdir.mkdir("persistence"))
    return StateStore(path)

def test_state_round_trip(store):
    key = "test_state"
    data = {"foo": "bar", "count": 1}
    
    store.write_state(key, data)
    read_back = store.read_state(key)
    
    assert read_back == data

def test_snapshot_determinism(store):
    key = "snap_state"
    data = {"a": 1, "b": 2} # keys will be sorted in snapshot
    store.write_state(key, data)
    
    hash1 = store.create_snapshot(key)
    hash2 = store.create_snapshot(key)
    
    assert hash1 == hash2
    assert len(hash1) == 64 # sha256 hex
