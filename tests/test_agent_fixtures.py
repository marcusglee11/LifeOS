"""
Unit tests for Replay Fixtures.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1.2
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from runtime.agents.fixtures import (
    ReplayMissError,
    CachedResponse,
    ReplayFixtureCache,
    is_replay_mode,
    get_cached_response,
)
from runtime.agents.models import DEFAULT_MODEL


class TestIsReplayMode:
    """Tests for replay mode detection."""
    
    def test_not_replay_when_unset(self, monkeypatch):
        """Should return False when env var not set."""
        monkeypatch.delenv("LIFEOS_TEST_MODE", raising=False)
        assert not is_replay_mode()
    
    def test_not_replay_when_different_value(self, monkeypatch):
        """Should return False for other values."""
        monkeypatch.setenv("LIFEOS_TEST_MODE", "live")
        assert not is_replay_mode()
        
        monkeypatch.setenv("LIFEOS_TEST_MODE", "test")
        assert not is_replay_mode()
    
    def test_replay_when_set(self, monkeypatch):
        """Should return True when LIFEOS_TEST_MODE=replay."""
        monkeypatch.setenv("LIFEOS_TEST_MODE", "replay")
        assert is_replay_mode()
    
    def test_replay_case_insensitive(self, monkeypatch):
        """Should be case-insensitive."""
        monkeypatch.setenv("LIFEOS_TEST_MODE", "REPLAY")
        assert is_replay_mode()
        
        monkeypatch.setenv("LIFEOS_TEST_MODE", "Replay")
        assert is_replay_mode()


class TestCachedResponse:
    """Tests for CachedResponse dataclass."""
    
    def test_cached_response_fields(self):
        """Should have all required fields."""
        cached = CachedResponse(
            call_id_deterministic="sha256:test123",
            role="designer",
            model_version="minimax-m2.1-free",
            input_packet_hash="sha256:input",
            prompt_hash="sha256:prompt",
            response_content="test content",
            response_packet={"key": "value"},
        )
        
        assert cached.call_id_deterministic == "sha256:test123"
        assert cached.role == "designer"
        assert cached.response_content == "test content"
        assert cached.response_packet == {"key": "value"}
    
    def test_cached_response_optional_packet(self):
        """response_packet can be None."""
        cached = CachedResponse(
            call_id_deterministic="sha256:test",
            role="builder",
            model_version="model",
            input_packet_hash="sha256:in",
            prompt_hash="sha256:prompt",
            response_content="plain text response",
            response_packet=None,
        )
        
        assert cached.response_packet is None


class TestReplayFixtureCache:
    """Tests for ReplayFixtureCache."""
    
    @pytest.fixture
    def cache(self, tmp_path):
        """Create cache with temp directory."""
        return ReplayFixtureCache(str(tmp_path / "cache"))
    
    def test_put_and_get(self, cache):
        """Should store and retrieve cached responses."""
        cached = CachedResponse(
            call_id_deterministic="sha256:test123",
            role="designer",
            model_version="minimax-m2.1-free",
            input_packet_hash="sha256:input",
            prompt_hash="sha256:prompt",
            response_content="test content",
            response_packet={"key": "value"},
        )
        
        cache.put(cached)
        
        retrieved = cache.get("sha256:test123")
        assert retrieved is not None
        assert retrieved.response_content == "test content"
    
    def test_get_returns_none_for_missing(self, cache):
        """Should return None for missing call_id."""
        result = cache.get("sha256:nonexistent")
        assert result is None
    
    def test_save_fixture_creates_file(self, cache, tmp_path):
        """save_fixture should write YAML file to disk."""
        cached = CachedResponse(
            call_id_deterministic="sha256:abc123def456",
            role="designer",
            model_version="minimax-m2.1-free",
            input_packet_hash="sha256:input",
            prompt_hash="sha256:prompt",
            response_content="saved content",
            response_packet={"saved": True},
        )
        
        fixture_path = cache.save_fixture(cached)
        
        assert fixture_path.exists()
        assert fixture_path.suffix == ".yaml"
        
        # File should contain the data
        content = fixture_path.read_text(encoding="utf-8")
        assert "sha256:abc123def456" in content
        assert "saved content" in content
    
    def test_load_fixtures_from_disk(self, tmp_path):
        """load_fixtures should load all YAML files from cache dir."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        # Create fixture files
        fixture1 = cache_dir / "test1.yaml"
        fixture1.write_text("""
call_id_deterministic: "sha256:fixture1"
role: "designer"
model_version: "model1"
input_packet_hash: "sha256:in1"
prompt_hash: "sha256:p1"
response_content: "content1"
response_packet: null
""", encoding="utf-8")
        
        fixture2 = cache_dir / "test2.yaml"
        fixture2.write_text("""
call_id_deterministic: "sha256:fixture2"
role: "builder"
model_version: "model2"
input_packet_hash: "sha256:in2"
prompt_hash: "sha256:p2"
response_content: "content2"
response_packet:
  key: value
""", encoding="utf-8")
        
        cache = ReplayFixtureCache(str(cache_dir))
        count = cache.load_fixtures()
        
        assert count == 2
        
        cached1 = cache.get("sha256:fixture1")
        assert cached1 is not None
        assert cached1.role == "designer"
        
        cached2 = cache.get("sha256:fixture2")
        assert cached2 is not None
        assert cached2.response_packet == {"key": "value"}
    
    def test_load_fixtures_skips_invalid(self, tmp_path):
        """load_fixtures should skip malformed files without error."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        # Valid fixture
        valid = cache_dir / "valid.yaml"
        valid.write_text("""
call_id_deterministic: "sha256:valid"
role: "designer"
model_version: "model"
input_packet_hash: "sha256:in"
prompt_hash: "sha256:p"
response_content: "valid"
""", encoding="utf-8")
        
        # Invalid fixture (not yaml)
        invalid = cache_dir / "invalid.yaml"
        invalid.write_text("not: valid: yaml: syntax::::", encoding="utf-8")
        
        # Missing required field
        missing = cache_dir / "missing.yaml"
        missing.write_text("role: designer", encoding="utf-8")
        
        cache = ReplayFixtureCache(str(cache_dir))
        count = cache.load_fixtures()
        
        # Should load valid fixture only
        assert count == 1
        assert cache.get("sha256:valid") is not None


class TestGetCachedResponse:
    """Tests for get_cached_response function."""
    
    def test_returns_cached_if_exists(self, tmp_path):
        """Should return cached response when present."""
        cache_dir = tmp_path / "cache"
        cache = ReplayFixtureCache(str(cache_dir))
        
        cached = CachedResponse(
            call_id_deterministic="sha256:exists",
            role="designer",
            model_version="model",
            input_packet_hash="sha256:in",
            prompt_hash="sha256:p",
            response_content="cached",
            response_packet=None,
        )
        cache.put(cached)
        
        result = get_cached_response("sha256:exists", cache)
        
        assert result.response_content == "cached"
    
    def test_raises_replay_miss_error(self, tmp_path):
        """Should raise ReplayMissError when cache miss."""
        cache = ReplayFixtureCache(str(tmp_path / "empty_cache"))
        
        with pytest.raises(ReplayMissError) as exc_info:
            get_cached_response("sha256:missing", cache)
        
        assert "sha256:missing" in str(exc_info.value)
        assert exc_info.value.call_id_deterministic == "sha256:missing"


class TestReplayMissError:
    """Tests for ReplayMissError exception."""
    
    def test_error_message(self):
        """Should have informative message."""
        error = ReplayMissError("sha256:test123")
        
        assert "sha256:test123" in str(error)
        assert "replay mode" in str(error).lower()
        assert "cached response" in str(error).lower()
    
    def test_call_id_attribute(self):
        """Should store call_id_deterministic."""
        error = ReplayMissError("sha256:abc")
        assert error.call_id_deterministic == "sha256:abc"
