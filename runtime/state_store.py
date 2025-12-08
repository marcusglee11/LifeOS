import json
import os
import hashlib
from typing import Dict, Any

class StateStore:
    def __init__(self, storage_path: str = "persistence"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def write_state(self, key: str, state: Dict[str, Any]):
        path = os.path.join(self.storage_path, f"{key}.json")
        with open(path, "w") as f:
            json.dump(state, f, sort_keys=True)

    def read_state(self, key: str) -> Dict[str, Any]:
        path = os.path.join(self.storage_path, f"{key}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"State key {key} not found")
        with open(path, "r") as f:
            return json.load(f)

    def create_snapshot(self, key: str) -> str:
        # returns hash of state
        state = self.read_state(key)
        serialized = json.dumps(state, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()