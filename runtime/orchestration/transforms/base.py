"""
Base transform registry and interfaces for Phase 3 packet routing.
"""

import hashlib
from typing import Callable, Dict, Tuple, Any

_TRANSFORM_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_transform(name: str, version: str):
    def decorator(fn: Callable[[dict, dict], dict]):
        _TRANSFORM_REGISTRY[name] = {
            "fn": fn,
            "version": version,
        }
        return fn
    return decorator


def get_transform(name: str) -> Dict[str, Any]:
    if name not in _TRANSFORM_REGISTRY:
        raise KeyError(f"TransformNotFound: {name}")
    return _TRANSFORM_REGISTRY[name]


def hash_payload(payload: Any) -> str:
    data = repr(payload).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def execute_transform(name: str, packet: dict, context: dict | None = None) -> Tuple[dict, dict]:
    transform = get_transform(name)
    fn = transform["fn"]
    version = transform["version"]

    input_hash = hash_payload(packet)
    result = fn(packet, context or {})
    output_hash = hash_payload(result)

    evidence = {
        "transform": name,
        "version": version,
        "input_hash": input_hash,
        "output_hash": output_hash,
    }
    return result, evidence
