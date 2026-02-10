"""
StateStore - Persistent key-value state storage.

Fail-Closed Boundary:
All filesystem errors (OSError) and JSON errors (JSONDecodeError) are wrapped
into StateStoreError. Callers can rely on deterministic error handling.

See: docs/02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md
"""
import json
import os
import hashlib
from typing import Dict, Any


class StateStoreError(Exception):
    """
    Base exception for StateStore operations.

    Wraps filesystem errors (OSError) and JSON errors (JSONDecodeError)
    to provide fail-closed boundary for state persistence.

    See: docs/02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md
    """
    pass


class StateStoreNotFound(StateStoreError, FileNotFoundError):
    """
    Raised when state key is not found.

    Inherits from both StateStoreError (for StateStore-specific handling)
    and FileNotFoundError (for backwards compatibility with code expecting
    FileNotFoundError).
    """
    pass


class StateStore:
    def __init__(self, storage_path: str = "persistence"):
        """Initialize StateStore with fail-closed boundary."""
        self.storage_path = storage_path
        try:
            os.makedirs(storage_path, exist_ok=True)
        except OSError as e:
            raise StateStoreError(f"Failed to create storage directory '{storage_path}': {e}")

    def write_state(self, key: str, state: Dict[str, Any]):
        """Write state to disk. Fail-closed: raises StateStoreError on filesystem errors."""
        path = os.path.join(self.storage_path, f"{key}.json")
        try:
            with open(path, "w") as f:
                json.dump(state, f, sort_keys=True)
        except OSError as e:
            raise StateStoreError(f"Failed to write state '{key}': {e}")

    def read_state(self, key: str) -> Dict[str, Any]:
        """Read state from disk. Fail-closed: raises StateStoreError on filesystem/JSON errors."""
        path = os.path.join(self.storage_path, f"{key}.json")
        if not os.path.exists(path):
            raise StateStoreNotFound(f"State key '{key}' not found at {path}")
        try:
            with open(path, "r") as f:
                return json.load(f)
        except OSError as e:
            raise StateStoreError(f"Failed to read state '{key}': {e}")
        except json.JSONDecodeError as e:
            raise StateStoreError(f"Invalid JSON in state '{key}': {e}")

    def create_snapshot(self, key: str) -> str:
        """Create SHA256 hash of state. Fail-closed: raises StateStoreError if state unreadable."""
        try:
            state = self.read_state(key)  # Already wraps errors
            serialized = json.dumps(state, sort_keys=True).encode("utf-8")
            return hashlib.sha256(serialized).hexdigest()
        except StateStoreError:
            raise  # Propagate wrapped errors from read_state