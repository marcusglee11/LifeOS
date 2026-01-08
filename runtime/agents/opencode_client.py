"""
OpenCode Client Module
======================

Reusable client for LLM calls via OpenCode HTTP REST API.
Wraps the ephemeral server lifecycle with context manager support.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Use requests if available, otherwise provide helpful error
try:
    import requests
except ImportError:
    requests = None  # Will raise on actual use


# ============================================================================
# EXCEPTIONS
# ============================================================================

class OpenCodeError(Exception):
    """Base exception for OpenCode client errors."""
    pass


class OpenCodeServerError(OpenCodeError):
    """Server failed to start or respond."""
    pass


class OpenCodeTimeoutError(OpenCodeError):
    """Request timed out."""
    pass


class OpenCodeSessionError(OpenCodeError):
    """Failed to create session or send message."""
    pass


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class LLMCall:
    """
    Request for an LLM call.

    Attributes:
        prompt: The user prompt to send.
        model: Model identifier (OpenRouter format).
        system_prompt: Optional system prompt (currently unused by OpenCode).
    """
    prompt: str
    model: str = "openrouter/anthropic/claude-sonnet-4"
    system_prompt: Optional[str] = None


@dataclass
class LLMResponse:
    """
    Response from an LLM call.

    Attributes:
        call_id: Unique identifier for this call (UUID).
        content: The response text from the model.
        model_used: The model that was actually used.
        latency_ms: Time taken for the call in milliseconds.
        timestamp: ISO timestamp of when the call completed.
    """
    call_id: str
    content: str
    model_used: str
    latency_ms: int
    timestamp: str


# ============================================================================
# CLIENT
# ============================================================================

class OpenCodeClient:
    """
    Client for interacting with OpenCode HTTP REST API.

    Manages an ephemeral OpenCode server lifecycle and provides
    a clean interface for LLM calls with logging.

    Usage:
        with OpenCodeClient(port=62586) as client:
            response = client.call(LLMCall(prompt="Hello"))
            print(response.content)

    Or manual lifecycle:
        client = OpenCodeClient()
        client.start_server(model="openrouter/anthropic/claude-sonnet-4")
        response = client.call(LLMCall(prompt="Hello"))
        client.stop_server()
    """

    # Default paths
    LOG_DIR = "logs/agent_calls"

    def __init__(
        self,
        port: int = 62586,
        timeout: int = 120,
        api_key: Optional[str] = None,
        log_calls: bool = True,
    ):
        """
        Initialize the OpenCode client.

        Args:
            port: HTTP port for the ephemeral server.
            timeout: Request timeout in seconds.
            api_key: OpenRouter API key (falls back to env vars).
            log_calls: Whether to log calls to disk.
        """
        if requests is None:
            raise OpenCodeError("requests library required: pip install requests")

        self.port = port
        self.timeout = timeout
        self.log_calls = log_calls
        self.api_key = api_key or self._load_api_key()

        # Server state
        self._server_process: Optional[subprocess.Popen] = None
        self._config_dir: Optional[str] = None
        self._current_model: Optional[str] = None
        self._session_id: Optional[str] = None

        # Ensure log directory exists
        if self.log_calls:
            os.makedirs(self.LOG_DIR, exist_ok=True)

    @property
    def base_url(self) -> str:
        """Base URL for the OpenCode server."""
        return f"http://127.0.0.1:{self.port}"

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._server_process is not None and self._server_process.poll() is None

    # ========================================================================
    # API KEY LOADING
    # ========================================================================

    def _load_api_key(self) -> Optional[str]:
        """Load API key from environment or .env file."""
        # Try environment first
        key = os.environ.get("STEWARD_OPENROUTER_KEY")
        if key:
            return key

        key = os.environ.get("OPENROUTER_API_KEY")
        if key:
            return key

        # Try .env file
        try:
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("STEWARD_OPENROUTER_KEY="):
                        return line.split("=", 1)[1].strip()
                    if line.startswith("OPENROUTER_API_KEY="):
                        return line.split("=", 1)[1].strip()
        except FileNotFoundError:
            pass

        return None

    # ========================================================================
    # SERVER LIFECYCLE
    # ========================================================================

    def _create_isolated_config(self, model: str) -> str:
        """Create isolated config directory for ephemeral server."""
        temp_dir = tempfile.mkdtemp(prefix="opencode_client_")

        # Config subdirectory
        config_subdir = os.path.join(temp_dir, "opencode")
        os.makedirs(config_subdir, exist_ok=True)

        # Data subdirectory for auth
        data_subdir = os.path.join(temp_dir, ".local", "share", "opencode")
        os.makedirs(data_subdir, exist_ok=True)

        # Write auth.json
        if self.api_key:
            auth_data = {"openrouter": {"type": "api", "key": self.api_key}}
            with open(os.path.join(data_subdir, "auth.json"), "w") as f:
                json.dump(auth_data, f, indent=2)

        # Write config
        config_data = {"model": model, "$schema": "https://opencode.ai/config.json"}
        with open(os.path.join(config_subdir, "opencode.json"), "w") as f:
            json.dump(config_data, f, indent=2)

        return temp_dir

    def _cleanup_config(self) -> None:
        """Clean up isolated config directory."""
        if self._config_dir and os.path.exists(self._config_dir):
            try:
                shutil.rmtree(self._config_dir)
            except Exception:
                pass
            self._config_dir = None

    def start_server(self, model: str = "openrouter/anthropic/claude-sonnet-4") -> None:
        """
        Start the ephemeral OpenCode server.

        Args:
            model: Model identifier to use.

        Raises:
            OpenCodeServerError: If server fails to start.
        """
        if self.is_running:
            raise OpenCodeServerError("Server already running")

        if not self.api_key:
            raise OpenCodeServerError("No API key configured")

        self._current_model = model
        self._config_dir = self._create_isolated_config(model)

        # Build environment
        env = os.environ.copy()
        env["APPDATA"] = self._config_dir
        env["XDG_CONFIG_HOME"] = self._config_dir
        env["USERPROFILE"] = self._config_dir
        env["HOME"] = self._config_dir
        env["OPENROUTER_API_KEY"] = self.api_key
        # Block fallback to other providers
        env["OPENAI_API_KEY"] = ""
        env["ANTHROPIC_API_KEY"] = ""

        try:
            self._server_process = subprocess.Popen(
                ["opencode", "serve", "--port", str(self.port)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=(os.name == "nt"),
            )
        except Exception as e:
            self._cleanup_config()
            raise OpenCodeServerError(f"Failed to start server: {e}")

        # Wait for server to be ready
        if not self._wait_for_health():
            self.stop_server()
            raise OpenCodeServerError("Server failed to become healthy")

    def stop_server(self) -> None:
        """Stop the ephemeral OpenCode server."""
        if self._server_process:
            self._server_process.terminate()
            try:
                self._server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_process.kill()
            self._server_process = None

        self._cleanup_config()
        self._session_id = None

    def _wait_for_health(self, timeout: int = 30) -> bool:
        """Wait for server health check to pass."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(f"{self.base_url}/global/health", timeout=1)
                if resp.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================

    def _create_session(self) -> str:
        """Create a new session and return session ID."""
        try:
            resp = requests.post(
                f"{self.base_url}/session",
                json={"title": "LLM Call", "model": self._current_model},
                timeout=10,
            )
            if resp.status_code != 200:
                raise OpenCodeSessionError(f"Session creation failed: {resp.status_code}")
            return resp.json()["id"]
        except requests.RequestException as e:
            raise OpenCodeSessionError(f"Session creation failed: {e}")

    def _send_message(self, session_id: str, prompt: str) -> str:
        """Send a message and return response content."""
        try:
            resp = requests.post(
                f"{self.base_url}/session/{session_id}/message",
                json={"parts": [{"type": "text", "text": prompt}]},
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                raise OpenCodeSessionError(f"Message send failed: {resp.status_code}")

            # Parse response
            data = resp.json()
            parts = data.get("parts", [])
            content = ""
            for part in parts:
                if part.get("type") == "text":
                    content += part.get("text", "")
            return content

        except requests.Timeout:
            raise OpenCodeTimeoutError(f"Request timed out after {self.timeout}s")
        except requests.RequestException as e:
            raise OpenCodeSessionError(f"Message send failed: {e}")

    # ========================================================================
    # CALL INTERFACE
    # ========================================================================

    def call(self, request: LLMCall) -> LLMResponse:
        """
        Make an LLM call.

        Args:
            request: The LLM call request.

        Returns:
            LLMResponse with the model's response.

        Raises:
            OpenCodeError: If the call fails.
        """
        if not self.is_running:
            raise OpenCodeServerError("Server not running. Call start_server() first.")

        call_id = str(uuid.uuid4())
        start_time = time.time()

        # Create session if needed (or reuse)
        if not self._session_id:
            self._session_id = self._create_session()

        # Send message
        content = self._send_message(self._session_id, request.prompt)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        timestamp = datetime.utcnow().isoformat() + "Z"

        response = LLMResponse(
            call_id=call_id,
            content=content,
            model_used=request.model,
            latency_ms=latency_ms,
            timestamp=timestamp,
        )

        # Log the call
        if self.log_calls:
            self._log_call(request, response)

        return response

    # ========================================================================
    # LOGGING
    # ========================================================================

    def _log_call(self, request: LLMCall, response: LLMResponse) -> None:
        """Log call to disk as JSON."""
        log_entry = {
            "call_id": response.call_id,
            "timestamp": response.timestamp,
            "request": {
                "prompt": request.prompt,
                "model": request.model,
                "system_prompt": request.system_prompt,
            },
            "response": {
                "content": response.content,
                "model_used": response.model_used,
                "latency_ms": response.latency_ms,
            },
        }

        # Use timestamp-based filename for chronological ordering
        filename = f"{response.timestamp.replace(':', '-').replace('.', '-')}_{response.call_id[:8]}.json"
        filepath = os.path.join(self.LOG_DIR, filename)

        try:
            with open(filepath, "w") as f:
                json.dump(log_entry, f, indent=2, sort_keys=True)
        except Exception:
            # Don't fail on logging errors
            pass

    # ========================================================================
    # CONTEXT MANAGER
    # ========================================================================

    def __enter__(self) -> "OpenCodeClient":
        """Start server on context entry."""
        self.start_server(model="openrouter/anthropic/claude-sonnet-4")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop server on context exit."""
        self.stop_server()
