"""
OpenCode Client Module
======================

Reusable client for LLM calls via OpenCode HTTP REST API.
Wraps the ephemeral server lifecycle with context manager support.

================================================================================
HOW TO CHANGE MODELS / PROVIDERS (READ THIS FIRST)
================================================================================

If you need to switch to a different model or provider, follow these steps:

1.  **Edit `config/models.yaml`**:
    - Set the model ID in `default_chain` (e.g., `"claude-sonnet-4"`, `"gpt-4o"`).
    - Set the endpoint URL in the `zen.base_url` field.
    - The first model in `default_chain` is always used.

2.  **Set the API Key in `.env`**:
    - Add/update the key that matches your provider:
      - Zen/Anthropic: `ZEN_API_KEY=sk-...`
      - OpenRouter: `STEWARD_OPENROUTER_KEY=sk-or-...`
      - OpenAI: `OPENAI_API_KEY=sk-...`
    - This client prioritizes: ZEN_API_KEY > STEWARD_OPENROUTER_KEY > OPENROUTER_API_KEY.

3.  **IMPORTANT: Zen Endpoint Specifics**:
    - The Zen endpoint (`https://opencode.ai/zen/v1/messages`) uses the Anthropic protocol.
    - The `opencode` CLI may **reject model IDs it doesn't recognize**. If you see
      "ProviderModelNotFoundError", this client has a direct REST fallback for
      Zen + Minimax. For other models, you may need to use a recognized alias
      or extend the fallback logic below (search for "SPECIAL CASE: Zen").

4.  **Verification**:
    - Run `python scripts/verify_opencode_connectivity.py` to test.
    - Check `logs/agent_calls/` for the `model_used` field in the JSON logs.

================================================================================
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

# Import canonical defaults from single source of truth
try:
    from runtime.agents.models import (
        DEFAULT_MODEL,
        DEFAULT_ENDPOINT,
        API_KEY_FALLBACK_CHAIN,
        get_api_key,
    )
except ImportError:
    DEFAULT_MODEL = "minimax-m2.1-free"
    DEFAULT_ENDPOINT = "https://opencode.ai/zen/v1/messages"
    API_KEY_FALLBACK_CHAIN = ["ZEN_STEWARD_KEY", "ZEN_API_KEY", "STEWARD_OPENROUTER_KEY", "OPENROUTER_API_KEY"]
    def get_api_key():
        for k in API_KEY_FALLBACK_CHAIN:
            v = os.environ.get(k)
            if v:
                return v
        return None


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
        role: Agent role making the call (for usage tracking).
    """
    prompt: str
    model: str = DEFAULT_MODEL
    system_prompt: Optional[str] = None
    role: str = "unknown"


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
        upstream_base_url: Optional[str] = None,
        log_calls: bool = True,
        role: str = "unknown",
    ):
        """
        Initialize the OpenCode client.

        Args:
            port: HTTP port for the ephemeral server.
            timeout: Request timeout in seconds.
            api_key: OpenRouter API key (falls back to role-based key).
            upstream_base_url: Custom base URL for the LLM endpoint.
            log_calls: Whether to log calls to disk.
            role: Agent role for per-agent key selection.
        """
        if requests is None:
            raise OpenCodeError("requests library required: pip install requests")

        self.port = port
        self.timeout = timeout
        self.log_calls = log_calls
        self.role = role
        self.api_key = api_key or self._load_api_key_for_role(role)
        self.upstream_base_url = upstream_base_url

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

    def _load_api_key_for_role(self, role: str) -> Optional[str]:
        """
        Load API key for a specific agent role.
        
        Priority:
        1. Role-specific key from models.yaml config (via environment)
        2. Legacy fallback keys (ZEN_API_KEY, STEWARD_OPENROUTER_KEY)
        3. .env file parsing
        """
        # Try to load from models.py config
        try:
            from runtime.agents.models import get_agent_config
            agent_config = get_agent_config(role)
            key = os.environ.get(agent_config.api_key_env)
            if key:
                return key
        except Exception:
            pass  # Fall through to legacy loading

        # Legacy fallback: check well-known env vars (uses canonical chain)
        for env_var in API_KEY_FALLBACK_CHAIN:
            key = os.environ.get(env_var)
            if key:
                return key

        # Try .env file
        try:
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        var, val = line.split("=", 1)
                        # Check for role-specific key first
                        role_upper = role.upper().replace("_", "_")
                        if var == f"ZEN_{role_upper}_KEY" or var == f"OPENROUTER_{role_upper}_KEY":
                            return val.strip()
                        # Then check legacy keys
                        if var in ["ZEN_API_KEY", "STEWARD_OPENROUTER_KEY", "OPENROUTER_API_KEY"]:
                            return val.strip()
        except FileNotFoundError:
            pass

        return None

    def _load_api_key(self) -> Optional[str]:
        """Legacy method - calls _load_api_key_for_role with 'unknown'."""
        return self._load_api_key_for_role("unknown")


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
            auth_data = {
                "zen": {"type": "api", "key": self.api_key},
                "openrouter": {"type": "api", "key": self.api_key}
            }
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

    def start_server(self, model: Optional[str] = None) -> None:
        """
        Start the ephemeral OpenCode server.

        Args:
            model: Model identifier to use (defaults to self.default_model or grok).
        """
        if self.is_running:
            raise OpenCodeServerError("Server already running")

        # Determine model
        model = model or os.environ.get("STEWARD_MODEL", "minimax-m2.1-free")
        
        if not self.api_key:
            raise OpenCodeServerError("No API key configured (STEWARD_OPENROUTER_KEY or OPENROUTER_API_KEY required)")

        self._current_model = model
        self._config_dir = self._create_isolated_config(model)

        # Build environment
        env = os.environ.copy()
        env["APPDATA"] = self._config_dir
        env["XDG_CONFIG_HOME"] = self._config_dir
        env["USERPROFILE"] = self._config_dir
        env["HOME"] = self._config_dir
        env["OPENROUTER_API_KEY"] = self.api_key
        if self.upstream_base_url:
            env["OPENROUTER_BASE_URL"] = self.upstream_base_url
            # Also set generic BASE_URL if supported by simple-proxy or similar
            env["BASE_URL"] = self.upstream_base_url
        
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
                raise OpenCodeSessionError(f"Session creation failed: {resp.status_code} - {resp.text}")
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
                raise OpenCodeSessionError(f"Message send failed: {resp.status_code} - {resp.text}")

            # Parse response
            try:
                data = resp.json()
            except json.JSONDecodeError:
                raise OpenCodeSessionError(f"Message send failed: Invalid JSON response from server. Body: {resp.text[:500]}")
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
        Make an LLM call using 'opencode run' CLI for maximum reliability.

        Args:
            request: The LLM call request.

        Returns:
            LLMResponse with the model's response.

        Raises:
            OpenCodeError: If the call fails.
        """
        # Use model as specified (no forced openrouter/ prefix for Zen)
        model = request.model
        if not model:
            model = self._current_model or os.environ.get("STEWARD_MODEL", "minimax-m2.1-free")

        call_id = str(uuid.uuid4())
        start_time = time.time()

        # Build command for subprocess
        # We use 'run' instead of 'serve' + REST because it's more robust on Windows
        # and guarantees the model/key usage requested by the user.
        cmd = ["opencode", "run", "-m", model, request.prompt]

        # Build environment
        env = os.environ.copy()
        if self.api_key:
            env["OPENROUTER_API_KEY"] = self.api_key
            env["ZEN_API_KEY"] = self.api_key
            env["ANTHROPIC_API_KEY"] = self.api_key

        if self.upstream_base_url:
            env["OPENROUTER_BASE_URL"] = self.upstream_base_url
            env["BASE_URL"] = self.upstream_base_url
            env["ANTHROPIC_BASE_URL"] = self.upstream_base_url

            # SPECIAL CASE: Zen endpoint is Anthropic-compatible but CLI blocks minimax model name.
            # We use direct REST if detecting Zen + Minimax.
            if "opencode.ai/zen" in self.upstream_base_url.lower() and "minimax" in model.lower():
                # print(f"DEBUG: Triggering direct Zen fallback for {model} at {self.upstream_base_url}")
                try:
                    import requests
                    headers = {
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    }
                    payload = {
                        "model": "minimax-m2.1-free",
                        "messages": [{"role": "user", "content": request.prompt}],
                        "max_tokens": 4096,
                        "temperature": 0.7
                    }
                    
                    # Ensure URL is the base /messages endpoint
                    zen_url = self.upstream_base_url
                    if not zen_url.endswith("/messages"):
                        zen_url = zen_url.rstrip("/") + "/messages"
                    
                    response = requests.post(zen_url, headers=headers, json=payload, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        text = ""
                        for content_part in data.get("content", []):
                            if content_part.get("type") == "text":
                                text += content_part.get("text")
                        
                        return LLMResponse(
                            call_id=call_id,
                            content=text,
                            model_used=f"ZEN:{data.get('model', model)}",
                            latency_ms=int((time.time() - start_time) * 1000),
                            timestamp=datetime.now().isoformat()
                        )
                except Exception as e:
                    if self.log_calls:
                        print(f"Direct Zen call failed: {e}")

        try:
            # Execute opencode run
            # Note: we don't use 'serve' REST API here as it has been flaky with 
            # certain model IDs and streaming responses.
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                shell=(os.name == "nt"),
            )

            if result.returncode != 0:
                error_output = result.stderr or result.stdout
                raise OpenCodeError(f"opencode run failed with exit code {result.returncode}: {error_output}")

            content = result.stdout.strip()
            
            # [Fix] Strip potential ANSI escape codes or logo if present
            # For opencode 1.1.4, 'run' typically outputs just the response 
            # but if it has a logo, we should be careful.
            if "READY" in content and len(content) > 100: # Heuristic
                # If there's a lot of noise, try to find the actual response
                # But for now, we assume 'run' is clean based on CLI tests.
                pass

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            timestamp = datetime.utcnow().isoformat() + "Z"

            response = LLMResponse(
                call_id=call_id,
                content=content,
                model_used=model,
                latency_ms=latency_ms,
                timestamp=timestamp,
            )

            # Log the call
            if self.log_calls:
                self._log_call(request, response)

            return response

        except subprocess.TimeoutExpired:
            raise OpenCodeTimeoutError(f"opencode run timed out after {self.timeout}s")
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise OpenCodeError(f"Failed to execute opencode run: {e}")

    # ========================================================================
    # LOGGING
    # ========================================================================

    def _log_call(self, request: LLMCall, response: LLMResponse) -> None:
        """Log call to disk as JSON."""
        log_entry = {
            "call_id": response.call_id,
            "timestamp": response.timestamp,
            "role": request.role,
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
        self.start_server()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop server on context exit."""
        self.stop_server()
