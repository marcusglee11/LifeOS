"""
Tests for provider health monitoring.
"""

from unittest.mock import MagicMock, patch

from runtime.agents.health import (
    HealthReport,
    LatencyTracker,
    ProviderStatus,
    check_all_providers,
    check_api_provider,
    check_cli_provider,
)
from runtime.agents.models import (
    CLIProviderConfig,
    ModelConfig,
)

# ---------------------------------------------------------------------------
# ProviderStatus / HealthReport
# ---------------------------------------------------------------------------


class TestProviderStatus:
    def test_available(self):
        s = ProviderStatus(name="zen", available=True, latency_ms=50)
        assert s.available is True

    def test_unavailable_with_error(self):
        s = ProviderStatus(name="codex", available=False, error="not found")
        assert s.available is False
        assert s.error == "not found"


class TestHealthReport:
    def test_all_healthy(self):
        report = HealthReport(
            providers=[
                ProviderStatus(name="zen", available=True),
                ProviderStatus(name="codex", available=True),
            ],
            all_healthy=True,
        )
        assert report.available_providers == ["zen", "codex"]
        assert report.unavailable_providers == []

    def test_partial_health(self):
        report = HealthReport(
            providers=[
                ProviderStatus(name="zen", available=True),
                ProviderStatus(name="codex", available=False, error="missing"),
            ],
            all_healthy=False,
        )
        assert report.available_providers == ["zen"]
        assert report.unavailable_providers == ["codex"]


# ---------------------------------------------------------------------------
# LatencyTracker
# ---------------------------------------------------------------------------


class TestLatencyTracker:
    def test_record_and_average(self):
        tracker = LatencyTracker(window=3)
        tracker.record("zen", 100)
        tracker.record("zen", 200)
        tracker.record("zen", 300)
        assert tracker.average("zen") == 200.0

    def test_sliding_window(self):
        tracker = LatencyTracker(window=2)
        tracker.record("zen", 100)
        tracker.record("zen", 200)
        tracker.record("zen", 300)  # pushes out 100
        assert tracker.average("zen") == 250.0

    def test_unknown_provider_returns_none(self):
        tracker = LatencyTracker()
        assert tracker.average("nonexistent") is None

    def test_fastest(self):
        tracker = LatencyTracker()
        tracker.record("zen", 200)
        tracker.record("codex", 100)
        tracker.record("gemini", 150)
        assert tracker.fastest() == "codex"

    def test_fastest_empty(self):
        tracker = LatencyTracker()
        assert tracker.fastest() is None

    def test_all_averages(self):
        tracker = LatencyTracker()
        tracker.record("zen", 100)
        tracker.record("codex", 200)
        avgs = tracker.all_averages()
        assert avgs == {"zen": 100.0, "codex": 200.0}


# ---------------------------------------------------------------------------
# check_cli_provider
# ---------------------------------------------------------------------------


class TestCheckCLIProvider:
    @patch("shutil.which", return_value="/usr/bin/codex")
    def test_available(self, mock_which):
        cfg = CLIProviderConfig(binary="codex", enabled=True)
        status = check_cli_provider("codex", cfg)
        assert status.available is True
        assert status.name == "codex"
        assert status.error == ""

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        cfg = CLIProviderConfig(binary="codex", enabled=True)
        status = check_cli_provider("codex", cfg)
        assert status.available is False
        assert "not found" in status.error


# ---------------------------------------------------------------------------
# check_api_provider
# ---------------------------------------------------------------------------


class TestCheckAPIProvider:
    @patch("httpx.Client")
    def test_reachable(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.head.return_value = MagicMock(status_code=200)
        mock_client_cls.return_value = mock_client

        status = check_api_provider("zen", "https://opencode.ai/zen/v1/messages")
        assert status.available is True
        assert status.name == "zen"

    @patch("httpx.Client")
    def test_unreachable(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.head.side_effect = Exception("connection refused")
        mock_client_cls.return_value = mock_client

        status = check_api_provider("zen", "https://unreachable.example.com")
        assert status.available is False
        assert "connection refused" in status.error


# ---------------------------------------------------------------------------
# check_all_providers
# ---------------------------------------------------------------------------


class TestCheckAllProviders:
    @patch("runtime.agents.health.check_api_provider")
    @patch("runtime.agents.health.check_cli_provider")
    def test_all_healthy(self, mock_cli, mock_api):
        mock_api.return_value = ProviderStatus(name="zen", available=True, latency_ms=50)
        mock_cli.return_value = ProviderStatus(name="codex", available=True, latency_ms=10)

        config = ModelConfig(
            default_chain=["claude-sonnet-4-5"],
            base_url="https://opencode.ai/zen/v1/messages",
            cli_providers={
                "codex": CLIProviderConfig(binary="codex", enabled=True),
            },
        )
        report = check_all_providers(config=config)

        assert report.all_healthy is True
        assert len(report.providers) == 2
        assert report.recommended_fallbacks == ["codex", "zen"]  # sorted by latency

    @patch("runtime.agents.health.check_api_provider")
    @patch("runtime.agents.health.check_cli_provider")
    def test_partial_failure(self, mock_cli, mock_api):
        mock_api.return_value = ProviderStatus(name="zen", available=True, latency_ms=50)
        mock_cli.return_value = ProviderStatus(name="codex", available=False, error="missing")

        config = ModelConfig(
            default_chain=["claude-sonnet-4-5"],
            base_url="https://opencode.ai/zen/v1/messages",
            cli_providers={
                "codex": CLIProviderConfig(binary="codex", enabled=True),
            },
        )
        report = check_all_providers(config=config)

        assert report.all_healthy is False
        assert report.available_providers == ["zen"]
        assert report.unavailable_providers == ["codex"]

    def test_disabled_cli_not_checked(self):
        config = ModelConfig(
            default_chain=["claude-sonnet-4-5"],
            base_url="",  # no API endpoint
            cli_providers={
                "codex": CLIProviderConfig(binary="codex", enabled=False),
            },
        )
        report = check_all_providers(config=config)
        # Disabled providers should not be checked
        assert len(report.providers) == 0
        assert report.all_healthy is True
