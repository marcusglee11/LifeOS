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
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Use requests if available, otherwise provide helpful error
try:
    import requests
except ImportError:
    requests = None  # Will raise on actual use

# Import config-driven defaults from single source of truth
try:
    from runtime.agents.models import (
        get_default_endpoint,
        get_api_key_fallback_chain,
        get_api_key,
        load_model_config,
    )
    _HAS_MODELS_MODULE = True
except ImportError:
    _HAS_MODELS_MODULE = False

    def get_default_endpoint() -> str:
        return "https://opencode.ai/zen/v1/messages"

    def get_api_key_fallback_chain() -> list:
        return ["ZEN_STEWARD_KEY", "ZEN_API_KEY", "OPENROUTER_API_KEY"]

    def get_api_key() -> Optional[str]:
        for k in get_api_key_fallback_chain():
            v = os.environ.get(k)
            if v:
                return v
        return None

    def load_model_config():
        return None


def _get_openrouter_base_url() -> str:
    """Get OpenRouter base URL from config or fallback."""
    if _HAS_MODELS_MODULE:
        try:
            config = load_model_config()
            # Check for openrouter config in the raw yaml
            import yaml
            from pathlib import Path
            config_path = Path("config/models.yaml")
            if config_path.exists():
                with open(config_path, "r") as f:
                    data = yaml.safe_load(f)
                    openrouter = data.get("openrouter", {})
                    base_url = openrouter.get("base_url", "")
                    if base_url:
                        # Ensure it ends with /chat/completions for API calls
                        if not base_url.endswith("/chat/completions"):
                            return base_url.rstrip("/") + "/chat/completions"
                        return base_url
        except Exception:
            pass
    return "https://openrouter.ai/api/v1/chat/completions"


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
    model: Optional[str] = "auto"  # "auto" triggers config-driven resolution
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
        self.upstream_base_url = upstream_base_url or get_default_endpoint()

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

    def _get_key_from_env_file(self, var_name: str) -> Optional[str]:
        """
        Robustly parse .env file for a variable.
        Handles:
        - Comments (#)
        - Quoted values ("value", 'value')
        - Whitespace around =
        """
        env_path = os.path.join(os.getcwd(), ".env")
        if not os.path.exists(env_path):
            return None
            
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == var_name:
                            v = v.strip()
                            # Handle quotes
                            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                                v = v[1:-1]
                            return v
        except Exception:
            pass
        return None

    def _load_api_key_for_role(self, role: str, provider: str = "openrouter") -> Optional[str]:
        """
        Load the API key for a specific role and provider.
        
        Priority:
        1. os.environ[SPECIFIC_VAR]
        2. .env file [SPECIFIC_VAR]
        3. os.environ[GENERIC_VAR]
        4. .env file [GENERIC_VAR]
        """
        # 1. Determine Var Name from Config
        env_var_name = None
        try:
            from runtime.agents.models import get_agent_config
            agent_config = get_agent_config(role)
            if agent_config:
                if provider == "zen":
                    # For Zen, we trust the primary key env unless explicitly overridden
                    env_var_name = agent_config.api_key_env
                elif agent_config.fallback:
                    for fb in agent_config.fallback:
                        if fb.get("provider") == provider:
                            env_var_name = fb.get("api_key_env")
                            break
        except ImportError:
            pass

        if not env_var_name:
            if provider == "zen":
                 env_var_name = f"ZEN_{role.upper()}_KEY"
            else:
                 env_var_name = f"OPENROUTER_{role.upper()}_KEY"
        
        # 2. Try Specific Key
        key = self._get_key_from_source(env_var_name)
        if key: return key

        # 3. Fallback to Generic
        if provider == "zen":
             return self._get_key_from_source("ZEN_API_KEY")
        else:
             return self._get_key_from_source("OPENROUTER_API_KEY")

    def _get_key_from_source(self, env_var_name: str) -> Optional[str]:
        """Try os.environ then .env."""
        if not env_var_name: return None
        val = os.environ.get(env_var_name)
        if val and val.strip(): return val.strip()
        return self._get_key_from_env_file(env_var_name)

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

        # Check API key first (more fundamental than model)
        if not self.api_key:
            raise OpenCodeServerError("No API key configured (STEWARD_OPENROUTER_KEY or OPENROUTER_API_KEY required)")

        # Determine model
        model = model or os.environ.get("STEWARD_MODEL")
        if not model:
            raise OpenCodeServerError("No model specified for server.")

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
            # Only set base URL for server if it's NOT the Zen special case
            # (Zen special case is handled in call() via direct REST or env override)
            # Actually, server might need it for session creation if using REST?
            # But we only use 'opencode run' now. 'serve' + REST is legacy/flaky.
            # We'll set it anyway, but call() override is what matters.
            env["OPENROUTER_BASE_URL"] = self.upstream_base_url
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
        Make an LLM call with automatic fallback support.
        """
        # 1. Determine Primary Model
        primary_model = request.model
        if not primary_model:
            primary_model = self._current_model or os.environ.get("STEWARD_MODEL")
            if not primary_model:
                raise ValueError("Model must be specified in request or configuration.")

        # 2. Build Attempt Chain
        # Start with primary (load provider from config)
        primary_provider = None
        try:
            from runtime.agents.models import get_agent_config
            agent_config = get_agent_config(self.role)
            if agent_config:
                primary_provider = agent_config.provider
        except (ImportError, Exception):
            pass

        attempts = [{"model": primary_model, "provider": primary_provider}]

        # Add fallbacks from config
        try:
            from runtime.agents.models import get_agent_config
            agent_config = get_agent_config(self.role)
            if agent_config and agent_config.fallback:
                for fb in agent_config.fallback:
                    attempts.append({
                        "model": fb.get("model"),
                        "provider": fb.get("provider")
                    })
        except ImportError:
            # If models module issue, allow pass
            pass
        except Exception:
            # If config load fails, proceed with primary only
            pass

        # 3. Execute Chain
        last_error = None
        for i, attempt in enumerate(attempts):
            model = attempt["model"]
            is_fallback = (i > 0)
            
            # Trace log
            if "repro" in sys.argv[0] or "verify" in sys.argv[0]:
                print(f"  [TRACE] Attempt {i+1}/{len(attempts)}: {model} {'(Fallback)' if is_fallback else '(Primary)'}")

            try:
                return self._execute_attempt(model, request, provider=attempt.get("provider"))
            except Exception as e:
                # Log warning but continue
                print(f"  [WARNING] Call to {model} failed: {e}")
                last_error = e
                continue
        
        # If all failed
        raise last_error or OpenCodeError("All execution attempts failed")

    def _execute_attempt(self, model: str, request: LLMCall, provider: Optional[str] = None) -> LLMResponse:
        """Execute a single LLM attempt with specific model and dynamic key swapping."""
        call_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Build environment for this attempt
        env = os.environ.copy()
        
        # Base Key Injection
        if self.api_key:
            env["OPENROUTER_API_KEY"] = self.api_key
            env["ZEN_API_KEY"] = self.api_key
            env["ANTHROPIC_API_KEY"] = self.api_key
            
        # SWAP LOGIC: Determine correct key & provider for THIS model
        # Expanded for new OpenCode/Gemini models
        # P1: Option C - If provider is explicitly 'opencode-openai', treat as plugin (skip Zen REST)
        is_plugin = provider and "opencode-openai" in provider
        is_zen_model = not is_plugin and any(k in model.lower() for k in ["minimax", "zen", "opencode", "gemini"])
        key_status = "Using Primary Key"
        
        if not is_zen_model:
            # Targeted swap to OpenRouter key if needed
            or_key = self._load_api_key_for_role(self.role, provider="openrouter")
            if or_key:
                if or_key != self.api_key:
                    env["OPENROUTER_API_KEY"] = or_key
                    key_status = f"SWAPPED to OpenRouter Key ({or_key[:10]}...)"
                else:
                     key_status = "Primary is already OpenRouter Key"
            else:
                key_status = "FAILED TO SWAP (No OpenRouter key found)"
        
        # Verbose Trace
        if "repro" in sys.argv[0] or "verify" in sys.argv[0]:
            print(f"  [TRACE] Role: {self.role} | Model: {model} | {key_status}")
            if "SWAP" in key_status and "FAILED" not in key_status:
                 print(f"  [TRACE] Injecting OPENROUTER_API_KEY into subprocess environment")

        # 1. SPECIAL CASE: OpenRouter Direct REST (Standard OpenAI)
        # We use this because `opencode run` CLI ignores injected environment variables
        # if a local .env exists, which breaks multi-key support.
        is_openrouter_model = model.startswith("openrouter/") or "openrouter" in self.upstream_base_url.lower()
        
        if is_openrouter_model:
            # Always attempt to load the specific key for this role first
            or_key = self._load_api_key_for_role(self.role, provider="openrouter")
            
            # If not found or empty, check if we have a generic one in env
            # (But only if we didn't find a specific one)
            if not or_key and "OPENROUTER_API_KEY" in env:
                or_key = env["OPENROUTER_API_KEY"]
                
            if or_key:
                or_key = or_key.strip()
                headers = {
                    "Authorization": f"Bearer {or_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://opencode.ai", # Required by OpenRouter for ranking
                    "X-Title": "LifeOS OpenCode Client"
                }
                
                # Get OpenRouter endpoint from config (single source of truth)
                or_url = _get_openrouter_base_url()
                # Override if custom base URL provided
                if self.upstream_base_url and "openrouter" in self.upstream_base_url:
                    or_url = self.upstream_base_url
                    if not or_url.endswith("/chat/completions"):
                        or_url = or_url.rstrip("/") + "/chat/completions"
                
                # Strip internal 'openrouter/' prefix for the raw API call
                api_model = model
                if api_model.startswith("openrouter/"):
                    api_model = api_model.replace("openrouter/", "", 1)

                messages = []
                if request.system_prompt:
                    messages.append({"role": "system", "content": request.system_prompt})
                messages.append({"role": "user", "content": request.prompt})

                payload = {
                    "model": api_model, 
                    "messages": messages,
                }
                
                try:
                    import requests
                    response = requests.post(or_url, headers=headers, json=payload, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        data = response.json()
                        text = ""
                        for choice in data.get("choices", []):
                            delta = choice.get("message", {}).get("content", "")
                            if delta:
                                text += delta
                                
                        llm_response = LLMResponse(
                            call_id=call_id,
                            content=text,
                            model_used=f"OR:{data.get('model', model)}",
                            latency_ms=int((time.time() - start_time) * 1000),
                            timestamp=datetime.now().isoformat()
                        )
                        
                        # Log the call
                        if self.log_calls:
                            self._log_call(request, llm_response)
                        
                        return llm_response
                    else:
                         logger.debug(f"OpenRouter REST Failed: Status {response.status_code}, Body: {response.text}")
                except Exception as e:
                    logger.debug(f"OpenRouter REST Exception: {e}")
                    pass

        # 2. SPECIAL CASE: Zen Direct REST (Minimax)
        # Using self.upstream_base_url logic from verified blocks
        is_zen_config_url = self.upstream_base_url and "opencode.ai/zen" in self.upstream_base_url.lower()
        
        if is_zen_model and is_zen_config_url:
             # Load Zen API Key specific
             zen_key = self._load_api_key_for_role(self.role, provider="zen")
             if zen_key:
                 zen_key = zen_key.strip()
                 headers = {
                    "x-api-key": zen_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                 }
                 # SPECIAL CASE: Gemini on Zen (Google Style)
                 if "gemini" in model.lower():
                     # Use Google Generative Language API format
                     # Zen endpoint likely mirrors Google's requirement for key in query param or x-goog-api-key
                     # Try removing :generateContent in case Zen appends it
                     zen_url = f"https://opencode.ai/zen/v1/models/gemini-3-flash:generateContent?key={zen_key}"
                     
                     # Google payload format
                     # user -> user, system -> (not robustly supported in v1beta/v1 for all models, passing as system_instruction if needed or prepending)
                     # For Flash, system_instruction is supported but simplified here to prepending for robustness via Zen?
                     # Let's try standard contents.
                     
                     contents = []
                     if request.system_prompt:
                         contents.append({"role": "user", "parts": [{"text": f"System: {request.system_prompt}"}]})
                         contents.append({"role": "model", "parts": [{"text": "Understood."}]})
                     
                     contents.append({"role": "user", "parts": [{"text": request.prompt}]})
                     
                     payload = {
                         "contents": contents,
                         "generationConfig": {
                             "temperature": 0.7,
                             "maxOutputTokens": 4096
                         }
                     }
                     
                     # Headers: Send all variants to be safe
                     headers = {
                        "x-api-key": zen_key,
                        "x-goog-api-key": zen_key,
                        "Authorization": f"Bearer {zen_key}",
                        "Content-Type": "application/json"
                     }

                     try:
                         import requests
                         response = requests.post(zen_url, headers=headers, json=payload, timeout=self.timeout)
                         
                         if response.status_code == 200:
                             data = response.json()
                             # Parse Google response
                             # candidates[0].content.parts[0].text
                             text = ""
                             candidates = data.get("candidates", [])
                             if candidates:
                                 parts = candidates[0].get("content", {}).get("parts", [])
                                 for part in parts:
                                     text += part.get("text", "")
                             
                             llm_response = LLMResponse(
                                 call_id=call_id,
                                 content=text,
                                 model_used=f"ZEN:{model}",
                                 latency_ms=int((time.time() - start_time) * 1000),
                                 timestamp=datetime.now().isoformat()
                             )
                             if self.log_calls:
                                 self._log_call(request, llm_response)
                             return llm_response
                         else:
                             logger.debug(f"Zen/Gemini REST Failed: Status {response.status_code}, Body: {response.text}")
                     except Exception as e:
                         logger.debug(f"Zen/Gemini REST Exception: {e}")
                         pass

                 else:
                     # Standard Anthropic Style (Minimax/Claude)
                     zen_model = model.replace("minimax/", "").replace("zen/", "").replace("opencode/", "")
                     
                     payload = {
                        "model": zen_model, 
                        "messages": [{"role": "user", "content": request.prompt}],
                        "max_tokens": 4096,
                        "temperature": 0.7
                     }
                     if request.system_prompt:
                         payload["system"] = request.system_prompt
                     
                     try:
                         import requests
                         # Ensure URL is correct.
                         zen_url = self.upstream_base_url
                         if "/messages" not in zen_url and "/models/" not in zen_url:
                             zen_url = zen_url.rstrip("/") + "/messages"
                         
                         response = requests.post(zen_url, headers=headers, json=payload, timeout=self.timeout)
                         
                         if response.status_code == 200:
                             data = response.json()
                             text = ""
                             for content_part in data.get("content", []):
                                 if content_part.get("type") == "text":
                                     text += content_part.get("text")
                             
                             llm_response = LLMResponse(
                                 call_id=call_id,
                                 content=text,
                                 model_used=f"ZEN:{data.get('model', model)}",
                                 latency_ms=int((time.time() - start_time) * 1000),
                                 timestamp=datetime.now().isoformat()
                             )
                             
                             # Log the call
                             if self.log_calls:
                                 self._log_call(request, llm_response)
                             
                             return llm_response
                         else:
                             logger.debug(f"Zen REST Failed: Status {response.status_code}, Body: {response.text}")
                     except Exception as e:
                         logger.debug(f"Zen REST Exception: {e}")
                         pass
        
        # 2. Standard CLI Execution
        cmd = ["opencode", "run", "-m", model, request.prompt]
        
        # Smart Base URL logic for CLI
        if self.upstream_base_url:
            is_zen_url = "opencode.ai/zen" in self.upstream_base_url.lower()
            if is_zen_url:
                if is_zen_model:
                     env["OPENROUTER_BASE_URL"] = self.upstream_base_url
                     env["BASE_URL"] = self.upstream_base_url
                     env["ANTHROPIC_BASE_URL"] = self.upstream_base_url
                else:
                    # Fallback clearing of Zen URL to avoid routing Grok to Zen
                    pass
            else:
                # Custom non-Zen URL
                env["OPENROUTER_BASE_URL"] = self.upstream_base_url
                env["BASE_URL"] = self.upstream_base_url
                env["ANTHROPIC_BASE_URL"] = self.upstream_base_url

        # Execute
        try:
            # Simulate 'y' inputs for tool confirmation prompts (send multiple just in case)
            result = subprocess.run(
                cmd, 
                env=env, 
                capture_output=True, 
                text=True, 
                input="y\ny\ny\ny\ny\n", # Auto-approve tool calls
                timeout=self.timeout,
                shell=(os.name == "nt"),
            )
            
            if result.returncode != 0:
                error_output = result.stderr or result.stdout
                raise OpenCodeError(f"opencode run failed with exit code {result.returncode}: {error_output}")

            content = result.stdout.strip()
            if not content:
                 # Debugging info
                err_msg = result.stderr.strip() if result.stderr else "No stderr output"
                # Check for known "UndefinedProviderError" signature in stderr just in case
                if "UndefinedProviderError" in err_msg:
                     raise OpenCodeError(f"CLI Provider Error: {err_msg}")
                raise OpenCodeError(f"CLI returned empty content (Silent Failure). Stderr: {err_msg}")

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
        except Exception as e:
            # Don't fail on logging errors
            logger.debug(f"Failed to write call log to {filepath}: {e}")

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
