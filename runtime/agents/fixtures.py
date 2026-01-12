"""
Replay Fixtures - Deterministic test fixtures for agent calls.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1.2
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


class ReplayMissError(Exception):
    """
    Raised when LIFEOS_TEST_MODE=replay and no cached response exists.
    
    Per v0.3 spec §5.1.2: In replay mode, do not fall through to live call.
    """
    
    def __init__(self, call_id_deterministic: str):
        self.call_id_deterministic = call_id_deterministic
        super().__init__(
            f"Replay mode: no cached response for call_id={call_id_deterministic}. "
            "Live API calls are disabled in replay mode."
        )


@dataclass
class CachedResponse:
    """Fixture format per v0.3 spec §5.1.2."""
    
    call_id_deterministic: str
    role: str
    model_version: str
    input_packet_hash: str
    prompt_hash: str
    response_content: str
    response_packet: Optional[dict]


class ReplayFixtureCache:
    """
    Replay fixture cache for deterministic testing.
    
    Per v0.3 spec §5.1.2:
    - Response cache keyed by call_id_deterministic
    - When LIFEOS_TEST_MODE=replay, return cached response
    - If not found, raise ReplayMissError (no live fallback)
    """
    
    def __init__(self, cache_dir: str = "logs/agent_calls/cache"):
        self.cache_dir = Path(cache_dir)
        self._cache: dict[str, CachedResponse] = {}
    
    def load_fixtures(self) -> int:
        """
        Load all fixtures from cache directory.
        
        Returns count of loaded fixtures.
        """
        if not self.cache_dir.exists():
            return 0
        
        count = 0
        for fixture_path in self.cache_dir.glob("*.yaml"):
            try:
                with open(fixture_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "call_id_deterministic" in data:
                        cached = CachedResponse(
                            call_id_deterministic=data["call_id_deterministic"],
                            role=data.get("role", ""),
                            model_version=data.get("model_version", ""),
                            input_packet_hash=data.get("input_packet_hash", ""),
                            prompt_hash=data.get("prompt_hash", ""),
                            response_content=data.get("response_content", ""),
                            response_packet=data.get("response_packet"),
                        )
                        self._cache[cached.call_id_deterministic] = cached
                        count += 1
            except Exception:
                pass  # Skip invalid fixtures
        
        return count
    
    def get(self, call_id_deterministic: str) -> Optional[CachedResponse]:
        """Get cached response by deterministic call ID."""
        return self._cache.get(call_id_deterministic)
    
    def put(self, response: CachedResponse) -> None:
        """Store a response in the cache."""
        self._cache[response.call_id_deterministic] = response
    
    def save_fixture(self, response: CachedResponse) -> Path:
        """
        Save a response as a YAML fixture file.
        
        Returns the path to the saved fixture.
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Use first 16 chars of call_id hash as filename
        call_hash = response.call_id_deterministic.replace("sha256:", "")[:16]
        fixture_path = self.cache_dir / f"{call_hash}.yaml"
        
        data = {
            "call_id_deterministic": response.call_id_deterministic,
            "role": response.role,
            "model_version": response.model_version,
            "input_packet_hash": response.input_packet_hash,
            "prompt_hash": response.prompt_hash,
            "response_content": response.response_content,
            "response_packet": response.response_packet,
        }
        
        with open(fixture_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False)
        
        self.put(response)
        return fixture_path


def is_replay_mode() -> bool:
    """Check if LIFEOS_TEST_MODE=replay is set."""
    return os.environ.get("LIFEOS_TEST_MODE", "").lower() == "replay"


def get_cached_response(
    call_id_deterministic: str,
    cache: Optional[ReplayFixtureCache] = None,
) -> CachedResponse:
    """
    Get cached response, raising ReplayMissError if not found.
    
    Per v0.3 spec §5.1.2:
    - If LIFEOS_TEST_MODE=replay and cache miss: raise ReplayMissError
    - Do NOT fall through to live call
    """
    if cache is None:
        cache = ReplayFixtureCache()
        cache.load_fixtures()
    
    cached = cache.get(call_id_deterministic)
    if cached is None:
        raise ReplayMissError(call_id_deterministic)
    
    return cached
