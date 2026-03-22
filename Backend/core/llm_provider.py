"""
LLM Provider — GitHub Copilot API Integration
===============================================
Centralized LLM provider that uses GitHub Copilot's API instead of
a paid OpenAI API key.

How it works:
  1. GitHub OAuth device flow → persistent GitHub token
  2. GitHub token → short-lived Copilot API token (auto-refreshed)
  3. Copilot API is OpenAI-compatible → works with langchain ChatOpenAI

Usage:
  from llm_provider import get_llm, get_llm_status, get_provider

  llm = get_llm(temperature=0.3, streaming=True)
  status = get_llm_status()
"""

import os
import json
import time
import threading
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum

import requests as http_requests
from langchain_openai import ChatOpenAI   # imported at module load — no lazy delay

logger = logging.getLogger(__name__)


# ─── Config ──────────────────────────────────────────────────────────────────

GITHUB_CLIENT_ID = "Iv1.b507a08c87ecfe98"   # Copilot VS Code extension client ID

DEFAULT_MODEL = "gpt-4o-mini"

# ─── Available Models via GitHub Copilot API ─────────────────────────────────
# These are models accessible through the Copilot API endpoint.

AVAILABLE_MODELS = [
    # ── OpenAI ────────────────────────────────────────────────────────────
    {"id": "gpt-4o",           "name": "GPT-4o",             "provider": "OpenAI",    "tier": "flagship",   "description": "Most capable OpenAI multimodal model"},
    {"id": "gpt-4o-mini",      "name": "GPT-4o Mini",        "provider": "OpenAI",    "tier": "efficient",  "description": "Fast and affordable, great for most tasks"},
    {"id": "gpt-4.1",          "name": "GPT-4.1",            "provider": "OpenAI",    "tier": "flagship",   "description": "Latest GPT-4 series, improved coding"},
    {"id": "gpt-4.1-mini",     "name": "GPT-4.1 Mini",       "provider": "OpenAI",    "tier": "efficient",  "description": "Lightweight GPT-4.1 variant"},
    {"id": "gpt-4.1-nano",     "name": "GPT-4.1 Nano",       "provider": "OpenAI",    "tier": "nano",       "description": "Fastest and cheapest GPT-4.1"},
    {"id": "gpt-4-turbo",      "name": "GPT-4 Turbo",        "provider": "OpenAI",    "tier": "flagship",   "description": "GPT-4 with 128k context and vision"},
    {"id": "gpt-4",            "name": "GPT-4",              "provider": "OpenAI",    "tier": "flagship",   "description": "Original GPT-4 model"},
    {"id": "gpt-3.5-turbo",    "name": "GPT-3.5 Turbo",      "provider": "OpenAI",    "tier": "efficient",  "description": "Fast legacy model, still widely used"},
    {"id": "gpt-5",            "name": "GPT-5",              "provider": "OpenAI",    "tier": "premium",    "description": "Next-gen GPT model, advanced reasoning"},
    {"id": "gpt-5-mini",       "name": "GPT-5 Mini",         "provider": "OpenAI",    "tier": "efficient",  "description": "Compact GPT-5 variant, optimized for speed"},
    {"id": "o1",               "name": "o1",                 "provider": "OpenAI",    "tier": "reasoning",  "description": "Advanced reasoning model"},
    {"id": "o1-mini",          "name": "o1 Mini",            "provider": "OpenAI",    "tier": "reasoning",  "description": "Fast reasoning model"},
    {"id": "o1-preview",       "name": "o1 Preview",         "provider": "OpenAI",    "tier": "reasoning",  "description": "Preview of o1 capabilities"},
    {"id": "o3",               "name": "o3",                 "provider": "OpenAI",    "tier": "reasoning",  "description": "Next-gen reasoning model"},
    {"id": "o3-pro",           "name": "o3 Pro",             "provider": "OpenAI",    "tier": "premium",    "description": "o3 with enhanced capabilities"},
    {"id": "o3-mini",          "name": "o3 Mini",            "provider": "OpenAI",    "tier": "reasoning",  "description": "Efficient reasoning model"},
    {"id": "o4-mini",          "name": "o4 Mini",            "provider": "OpenAI",    "tier": "reasoning",  "description": "Latest efficient reasoning model"},

    # ── Anthropic ─────────────────────────────────────────────────────────
    {"id": "claude-3.5-sonnet",   "name": "Claude 3.5 Sonnet",    "provider": "Anthropic",  "tier": "flagship",   "description": "Excellent for coding and analysis"},
    {"id": "claude-3.7-sonnet",   "name": "Claude 3.7 Sonnet",    "provider": "Anthropic",  "tier": "flagship",   "description": "Latest Sonnet with extended thinking"},
    {"id": "claude-sonnet-4",     "name": "Claude Sonnet 4",      "provider": "Anthropic",  "tier": "flagship",   "description": "Most capable Sonnet generation"},
    {"id": "claude-sonnet-4.5",   "name": "Claude Sonnet 4.5",    "provider": "Anthropic",  "tier": "premium",    "description": "Enhanced reasoning and code analysis"},
    {"id": "claude-opus-4",       "name": "Claude Opus 4",        "provider": "Anthropic",  "tier": "premium",    "description": "Anthropic's most powerful model"},
    {"id": "claude-haiku-3.5",    "name": "Claude Haiku 3.5",     "provider": "Anthropic",  "tier": "efficient",  "description": "Fast and compact Claude model"},

    # ── Google ────────────────────────────────────────────────────────────
    {"id": "gemini-2.0-flash",    "name": "Gemini 2.0 Flash",     "provider": "Google",     "tier": "efficient",  "description": "Fast multimodal model from Google"},
    {"id": "gemini-2.5-flash",    "name": "Gemini 2.5 Flash",     "provider": "Google",     "tier": "efficient",  "description": "Latest Flash model, speed optimized"},
    {"id": "gemini-2.5-pro",      "name": "Gemini 2.5 Pro",       "provider": "Google",     "tier": "flagship",   "description": "Google's most capable model"},
    {"id": "gemini-3-flash",      "name": "Gemini 3 Flash",       "provider": "Google",     "tier": "efficient",  "description": "Next-gen Flash, ultra-fast responses"},

    # ── xAI (Grok) ───────────────────────────────────────────────────────
    {"id": "grok-3",              "name": "Grok 3",               "provider": "xAI",        "tier": "flagship",   "description": "xAI's flagship reasoning model"},
    {"id": "grok-3-mini",         "name": "Grok 3 Mini",          "provider": "xAI",        "tier": "efficient",  "description": "Efficient Grok variant"},

    # ── Amazon ───────────────────────────────────────────────────────────
    {"id": "amazon-nova-pro",     "name": "Amazon Nova Pro",       "provider": "Amazon",    "tier": "flagship",   "description": "Amazon's multimodal foundation model"},
]

COPILOT_API_BASE = "https://api.githubcopilot.com"

# Refresh the Copilot API token this many seconds before it expires
REFRESH_BUFFER_SECONDS = 120

# Cache directory
CACHE_DIR = Path.home() / ".copilot_cache"
GITHUB_TOKEN_FILE = CACHE_DIR / "github_oauth.token"    # permanent
COPILOT_TOKEN_FILE = CACHE_DIR / "copilot_api.json"     # has expiry, auto-refreshed

COPILOT_HEADERS = {
    "Editor-Version":         "vscode/1.85.0",
    "Editor-Plugin-Version":  "copilot/1.155.0",
    "User-Agent":             "GithubCopilot/1.155.0",
    "Copilot-Integration-Id": "vscode-chat",
}

CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Current active model — mutable at runtime via Admin panel
_current_model: str = DEFAULT_MODEL
_model_file = CACHE_DIR / "current_model.txt"


def _load_saved_model():
    """Load the saved model preference from disk."""
    global _current_model
    if _model_file.exists():
        saved = _model_file.read_text().strip()
        if saved and any(m["id"] == saved for m in AVAILABLE_MODELS):
            _current_model = saved
            logger.info(f"[LLM] Loaded saved model preference: {saved}")


def _save_model(model_id: str):
    """Save model preference to disk."""
    _model_file.write_text(model_id)


def get_current_model() -> str:
    """Get the currently active model ID."""
    return _current_model


def set_current_model(model_id: str) -> bool:
    """Set the active model. Returns True if valid, False if model not found."""
    global _current_model
    if not any(m["id"] == model_id for m in AVAILABLE_MODELS):
        return False
    _current_model = model_id
    _save_model(model_id)
    logger.info(f"[LLM] Model changed to: {model_id}")
    return True


def get_available_models() -> list:
    """Get all available models grouped by provider."""
    return AVAILABLE_MODELS


# Load saved model on module import
_load_saved_model()


# ─── Connection Status ───────────────────────────────────────────────────────

class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    AUTH_REQUIRED = "auth_required"
    REFRESHING = "refreshing"
    ERROR = "error"


# ─── GitHub OAuth Token — Permanent Storage ──────────────────────────────────

def _load_github_token() -> str | None:
    if GITHUB_TOKEN_FILE.exists():
        return GITHUB_TOKEN_FILE.read_text().strip() or None
    return None


def _save_github_token(token: str):
    GITHUB_TOKEN_FILE.write_text(token)
    try:
        GITHUB_TOKEN_FILE.chmod(0o600)
    except Exception:
        pass  # Windows may not support chmod


# ─── Device Flow (for first-time auth or re-auth) ────────────────────────────

class DeviceFlowSession:
    """Tracks an in-progress device flow authentication."""

    def __init__(self):
        self.device_code: str = ""
        self.user_code: str = ""
        self.verification_uri: str = ""
        self.interval: int = 5
        self.expires_at: float = 0
        self.completed: bool = False
        self.error: str = ""
        self.token: str = ""

    def start(self) -> Dict[str, Any]:
        """Begin the GitHub device flow. Returns user_code + verification_uri."""
        resp = http_requests.post(
            "https://github.com/login/device/code",
            headers={"Accept": "application/json", **COPILOT_HEADERS},
            json={"client_id": GITHUB_CLIENT_ID, "scope": "read:user"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        self.device_code = data["device_code"]
        self.user_code = data["user_code"]
        self.verification_uri = data["verification_uri"]
        self.interval = data.get("interval", 5)
        self.expires_at = time.time() + data.get("expires_in", 900)
        self.completed = False
        self.error = ""
        self.token = ""

        return {
            "user_code": self.user_code,
            "verification_uri": self.verification_uri,
            "expires_in": data.get("expires_in", 900),
        }

    def poll(self) -> Dict[str, Any]:
        """Poll GitHub for device flow completion."""
        if self.completed:
            return {"status": "completed", "message": "Already authenticated"}

        if time.time() >= self.expires_at:
            self.error = "expired"
            return {"status": "expired", "message": "Device flow expired. Start again."}

        try:
            poll_resp = http_requests.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                json={
                    "client_id": GITHUB_CLIENT_ID,
                    "device_code": self.device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                timeout=15,
            ).json()

            if "access_token" in poll_resp:
                self.token = poll_resp["access_token"]
                self.completed = True
                _save_github_token(self.token)
                return {"status": "completed", "message": "Authentication successful!"}

            err = poll_resp.get("error", "")
            if err == "authorization_pending":
                return {"status": "pending", "message": "Waiting for user to authorize..."}
            elif err == "slow_down":
                self.interval += 5
                return {"status": "pending", "message": "Rate limited, slowing down..."}
            elif err in ("access_denied", "expired_token"):
                self.error = err
                return {"status": "error", "message": f"Authorization failed: {err}"}
            else:
                return {"status": "pending", "message": f"Status: {err or 'waiting'}..."}

        except Exception as e:
            return {"status": "error", "message": str(e)}


# ─── Copilot Token Manager ──────────────────────────────────────────────────

class CopilotTokenManager:
    """
    Manages the short-lived Copilot API token.

    - Loads cached token from disk on startup
    - Auto-refreshes via daemon thread before expiry
    - Thread-safe property access
    """

    def __init__(self, github_token: str):
        self._github_token = github_token
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at: float = 0
        self._status: ConnectionStatus = ConnectionStatus.DISCONNECTED
        self._last_error: str = ""
        self._last_refresh: float = 0

        # Load cached token from disk (instant, no network call)
        self._load_cached()

        # If we have a valid cached token, mark as connected right away
        if self._token and not self._is_stale():
            self._status = ConnectionStatus.CONNECTED
            logger.info("[LLM] Using cached Copilot token (still valid)")
        else:
            # Token is stale or missing — background thread will fetch it
            logger.info("[LLM] Copilot token needs refresh (will fetch in background)")

        self._stop_event = threading.Event()
        # Background thread handles initial fetch + ongoing refreshes
        threading.Thread(target=self._background_refresh, daemon=True).start()

    # ── Disk cache ────────────────────────────────────────────────────────

    def _load_cached(self):
        if not COPILOT_TOKEN_FILE.exists():
            return
        try:
            data = json.loads(COPILOT_TOKEN_FILE.read_text())
            self._token = data["token"]
            self._expires_at = float(data["expires_at"])
        except Exception:
            pass

    def _save_cached(self):
        COPILOT_TOKEN_FILE.write_text(
            json.dumps({"token": self._token, "expires_at": self._expires_at})
        )
        try:
            COPILOT_TOKEN_FILE.chmod(0o600)
        except Exception:
            pass

    # ── Token fetch ───────────────────────────────────────────────────────

    def _fetch_new_token(self):
        self._status = ConnectionStatus.REFRESHING

        resp = http_requests.get(
            "https://api.github.com/copilot_internal/v2/token",
            headers={
                "Authorization": f"token {self._github_token}",
                "Accept": "application/json",
                **COPILOT_HEADERS,
            },
            timeout=15,
        )

        if resp.status_code == 401:
            self._status = ConnectionStatus.AUTH_REQUIRED
            self._last_error = "GitHub token revoked or expired"
            GITHUB_TOKEN_FILE.unlink(missing_ok=True)
            COPILOT_TOKEN_FILE.unlink(missing_ok=True)
            logger.error("[LLM] GitHub OAuth token revoked — re-auth required")
            raise Exception("GitHub OAuth token revoked. Re-authentication required.")

        resp.raise_for_status()
        data = resp.json()

        with self._lock:
            self._token = data["token"]
            self._expires_at = float(data.get("expires_at", time.time() + 1800))
            self._save_cached()
            self._status = ConnectionStatus.CONNECTED
            self._last_error = ""
            self._last_refresh = time.time()

        exp = datetime.fromtimestamp(self._expires_at, tz=timezone.utc).strftime("%H:%M UTC")
        logger.info(f"[LLM] Copilot token refreshed (valid until {exp})")

    # ── Freshness check ──────────────────────────────────────────────────

    def _is_stale(self) -> bool:
        return (
            self._token is None
            or time.time() >= (self._expires_at - REFRESH_BUFFER_SECONDS)
        )

    def _ensure_fresh(self):
        if self._is_stale():
            self._fetch_new_token()

    # ── Background thread ────────────────────────────────────────────────

    def _background_refresh(self):
        # If token is stale or missing, fetch immediately on thread start
        if self._is_stale():
            try:
                self._fetch_new_token()
            except Exception as e:
                self._status = ConnectionStatus.ERROR
                self._last_error = str(e)
                logger.warning(f"[LLM] Initial token fetch failed: {e} — retrying in 30s")
                self._stop_event.wait(timeout=30)

        # Ongoing refresh loop
        while not self._stop_event.is_set():
            sleep_for = max(10, (self._expires_at - REFRESH_BUFFER_SECONDS) - time.time())
            self._stop_event.wait(timeout=sleep_for)
            if not self._stop_event.is_set():
                try:
                    self._fetch_new_token()
                except Exception as e:
                    self._status = ConnectionStatus.ERROR
                    self._last_error = str(e)
                    logger.warning(f"[LLM] Silent token refresh failed: {e} — retrying in 30s")
                    self._stop_event.wait(timeout=30)

    # ── Public interface ─────────────────────────────────────────────────

    @property
    def token(self) -> str:
        """Always returns a valid Copilot API token."""
        self._ensure_fresh()
        return self._token

    @property
    def status(self) -> ConnectionStatus:
        return self._status

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def last_refresh(self) -> float:
        return self._last_refresh

    @property
    def expires_at(self) -> float:
        return self._expires_at

    def update_github_token(self, new_token: str):
        """Update the GitHub token (after re-auth) and refresh Copilot token."""
        self._github_token = new_token
        self._fetch_new_token()

    def force_refresh(self):
        """Force a token refresh."""
        self._fetch_new_token()

    def stop(self):
        self._stop_event.set()


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton Provider
# ═══════════════════════════════════════════════════════════════════════════════

_token_manager: Optional[CopilotTokenManager] = None
_device_flow: Optional[DeviceFlowSession] = None
_init_lock = threading.Lock()


def initialize_provider() -> Dict[str, Any]:
    """
    Initialize the LLM provider on app startup.
    Returns status info.
    """
    global _token_manager

    github_token = _load_github_token()
    if not github_token:
        logger.info("[LLM] No GitHub token found — auth required")
        return {
            "status": ConnectionStatus.AUTH_REQUIRED,
            "message": "GitHub authentication required. Use the Admin panel to authenticate."
        }

    try:
        with _init_lock:
            _token_manager = CopilotTokenManager(github_token)
        logger.info("[LLM] Provider initialized successfully")
        return {
            "status": ConnectionStatus.CONNECTED,
            "message": "Connected to GitHub Copilot API"
        }
    except Exception as e:
        logger.error(f"[LLM] Provider initialization failed: {e}")
        return {
            "status": ConnectionStatus.ERROR,
            "message": str(e)
        }


def get_provider() -> Optional[CopilotTokenManager]:
    """Get the current token manager (may be None if not initialized)."""
    return _token_manager


def get_device_flow() -> DeviceFlowSession:
    """Get or create the device flow session."""
    global _device_flow
    if _device_flow is None:
        _device_flow = DeviceFlowSession()
    return _device_flow


def complete_device_flow():
    """Called after device flow completes to initialize the provider.
    
    Runs in a background thread so the HTTP response returns immediately.
    """
    global _token_manager, _device_flow

    if _device_flow and _device_flow.completed and _device_flow.token:
        token = _device_flow.token
        _device_flow = None  # Reset for next time

        def _init_in_background():
            global _token_manager
            try:
                if _token_manager:
                    _token_manager.update_github_token(token)
                else:
                    _token_manager = CopilotTokenManager(token)
                logger.info("[LLM] Provider initialized after device flow")
            except Exception as e:
                logger.error(f"[LLM] Provider init after device flow failed: {e}")

        threading.Thread(target=_init_in_background, daemon=True).start()


def get_llm_status() -> Dict[str, Any]:
    """Get current LLM connection status."""
    if _token_manager is None:
        github_token = _load_github_token()
        return {
            "status": ConnectionStatus.AUTH_REQUIRED if not github_token else ConnectionStatus.DISCONNECTED,
            "model": _current_model,
            "provider": "GitHub Copilot API",
            "message": "Not initialized. Use Admin panel to connect.",
            "has_github_token": github_token is not None,
            "last_refresh": None,
            "token_expires_at": None,
        }

    status = _token_manager.status
    last_refresh = _token_manager.last_refresh
    expires_at = _token_manager.expires_at

    return {
        "status": status,
        "model": _current_model,
        "provider": "GitHub Copilot API",
        "message": _token_manager.last_error if status == ConnectionStatus.ERROR else "Connected",
        "has_github_token": True,
        "last_refresh": datetime.fromtimestamp(last_refresh, tz=timezone.utc).isoformat() if last_refresh else None,
        "token_expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat() if expires_at else None,
    }


def get_llm(
    temperature: float = 0.3,
    streaming: bool = False,
    model: str = None,
) -> ChatOpenAI:
    """
    Get a ChatOpenAI instance configured for GitHub Copilot API.

    ChatOpenAI is imported at module load (top of file) — no cold-start delay.
    A fresh instance is returned each call so token + model changes are picked up.

    Args:
        temperature: LLM temperature (0-1)
        streaming:   Whether to enable streaming
        model:       Model name override (default: active model)

    Returns:
        ChatOpenAI instance configured for Copilot API

    Raises:
        RuntimeError: If provider is not initialized or auth is required
    """
    if _token_manager is None:
        raise RuntimeError(
            "LLM provider not initialized. "
            "Please authenticate via the Admin panel first."
        )

    if _token_manager.status == ConnectionStatus.AUTH_REQUIRED:
        raise RuntimeError(
            "GitHub re-authentication required. "
            "Please re-authenticate via the Admin panel."
        )

    model_name = model or _current_model

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        streaming=streaming,
        openai_api_key=_token_manager.token,
        openai_api_base=COPILOT_API_BASE,
        default_headers=COPILOT_HEADERS,
    )
