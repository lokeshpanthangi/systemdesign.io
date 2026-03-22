"""
GitHub Copilot API Client — Persistent Auth
============================================
Behaves like OpenClaw:
  - GitHub OAuth token is stored ONCE and never asked again across restarts
  - Copilot API token is silently auto-refreshed before it expires
  - No prompts after the very first login

Model: gpt-4o-mini
  (change MODEL constant below — "gpt-4.1-mini" is the newer alternative)

Usage:
  pip install requests
  python github_copilot_client.py
"""

import json
import sys
import time
import threading
from pathlib import Path
from datetime import datetime, timezone

import requests

# ─── Config ─────────────────────────────────────────────────────────────────────

GITHUB_CLIENT_ID = "Iv1.b507a08c87ecfe98"   # Copilot VS Code extension client ID

MODEL = "gpt-4o-mini"                        # Change to "gpt-4.1-mini" for newer mini

COPILOT_API_BASE = "https://api.githubcopilot.com"

# Refresh the Copilot API token this many seconds before it expires
REFRESH_BUFFER_SECONDS = 120

# Cache directory — both files live here
CACHE_DIR          = Path.home() / ".copilot_cache"
GITHUB_TOKEN_FILE  = CACHE_DIR / "github_oauth.token"   # permanent
COPILOT_TOKEN_FILE = CACHE_DIR / "copilot_api.json"     # has expiry, auto-refreshed

COPILOT_HEADERS = {
    "Editor-Version":         "vscode/1.85.0",
    "Editor-Plugin-Version":  "copilot/1.155.0",
    "User-Agent":             "GithubCopilot/1.155.0",
    "Copilot-Integration-Id": "vscode-chat",
}

CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ─── GitHub OAuth token — stored permanently, asked only once ───────────────────

def load_github_token() -> str | None:
    if GITHUB_TOKEN_FILE.exists():
        return GITHUB_TOKEN_FILE.read_text().strip() or None
    return None


def save_github_token(token: str):
    GITHUB_TOKEN_FILE.write_text(token)
    GITHUB_TOKEN_FILE.chmod(0o600)


def run_device_flow() -> str:
    """Runs the GitHub device flow. Only called on the very first ever run."""
    print("\n[auth] First-time GitHub login required.")

    resp = requests.post(
        "https://github.com/login/device/code",
        headers={"Accept": "application/json", **COPILOT_HEADERS},
        json={"client_id": GITHUB_CLIENT_ID, "scope": "read:user"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    device_code  = data["device_code"]
    user_code    = data["user_code"]
    verification = data["verification_uri"]
    interval     = data.get("interval", 5)
    expires_in   = data.get("expires_in", 900)

    print(f"\n  1. Open : {verification}")
    print(f"  2. Enter: {user_code}\n")

    deadline = time.time() + expires_in
    while time.time() < deadline:
        time.sleep(interval)
        poll = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id":   GITHUB_CLIENT_ID,
                "device_code": device_code,
                "grant_type":  "urn:ietf:params:oauth:grant-type:device_code",
            },
            timeout=15,
        ).json()

        if "access_token" in poll:
            token = poll["access_token"]
            save_github_token(token)
            print(f"[auth] GitHub login successful. Token saved to {GITHUB_TOKEN_FILE}")
            print("[auth] You will NEVER be asked to log in again.\n")
            return token

        err = poll.get("error", "")
        if err == "slow_down":
            interval += 5
        elif err in ("access_denied", "expired_token"):
            sys.exit(f"[auth] Authorization failed: {err}")

    sys.exit("[auth] Timed out waiting for GitHub authorization.")


def get_github_token() -> str:
    """
    Returns the stored GitHub OAuth token.
    Runs device flow only if no token is saved yet (first ever run).
    After that — across ALL restarts — it just reads the file silently.
    """
    token = load_github_token()
    if token:
        return token
    return run_device_flow()


# ─── Copilot API token — short-lived, refreshed silently in background ──────────

class CopilotTokenManager:
    """
    Manages the short-lived Copilot API token.

    On startup:
      - Tries to load a previously cached Copilot token from disk.
        If it's still valid, no network call is made (fast restart).
      - If expired or missing, fetches a new one silently.

    While running:
      - A background daemon thread wakes up REFRESH_BUFFER_SECONDS before
        expiry and silently fetches a fresh token.
      - Callers just read .token — they never see expiry or re-auth.

    This is exactly how OpenClaw handles it.
    """

    def __init__(self, github_token: str):
        self._github_token = github_token
        self._lock         = threading.Lock()
        self._token: str | None = None
        self._expires_at: float = 0

        self._load_cached()
        self._ensure_fresh()

        self._stop_event = threading.Event()
        threading.Thread(target=self._background_refresh, daemon=True).start()

    # ── Disk cache ─────────────────────────────────────────────────────────────

    def _load_cached(self):
        if not COPILOT_TOKEN_FILE.exists():
            return
        try:
            data = json.loads(COPILOT_TOKEN_FILE.read_text())
            self._token      = data["token"]
            self._expires_at = float(data["expires_at"])
        except Exception:
            pass  # corrupt or missing — will re-fetch

    def _save_cached(self):
        COPILOT_TOKEN_FILE.write_text(
            json.dumps({"token": self._token, "expires_at": self._expires_at})
        )
        COPILOT_TOKEN_FILE.chmod(0o600)

    # ── Token fetch ────────────────────────────────────────────────────────────

    def _fetch_new_token(self):
        resp = requests.get(
            "https://api.github.com/copilot_internal/v2/token",
            headers={
                "Authorization": f"token {self._github_token}",
                "Accept":        "application/json",
                **COPILOT_HEADERS,
            },
            timeout=15,
        )

        if resp.status_code == 401:
            # GitHub OAuth token was revoked by the user → clear everything
            print("\n[auth] GitHub OAuth token revoked. Clearing saved credentials...")
            GITHUB_TOKEN_FILE.unlink(missing_ok=True)
            COPILOT_TOKEN_FILE.unlink(missing_ok=True)
            sys.exit("[auth] Please re-run the script to log in again.")

        resp.raise_for_status()
        data = resp.json()

        with self._lock:
            self._token      = data["token"]
            self._expires_at = float(data.get("expires_at", time.time() + 1800))
            self._save_cached()

        exp = datetime.fromtimestamp(self._expires_at, tz=timezone.utc).strftime("%H:%M UTC")
        print(f"[auth] Copilot token refreshed silently (valid until {exp})")

    # ── Freshness check ────────────────────────────────────────────────────────

    def _is_stale(self) -> bool:
        return (
            self._token is None
            or time.time() >= (self._expires_at - REFRESH_BUFFER_SECONDS)
        )

    def _ensure_fresh(self):
        if self._is_stale():
            self._fetch_new_token()

    # ── Background thread ──────────────────────────────────────────────────────

    def _background_refresh(self):
        """
        Daemon thread — wakes up just before the token expires and refreshes it.
        User never sees any prompt or interruption.
        """
        while not self._stop_event.is_set():
            sleep_for = max(10, (self._expires_at - REFRESH_BUFFER_SECONDS) - time.time())
            self._stop_event.wait(timeout=sleep_for)
            if not self._stop_event.is_set():
                try:
                    self._fetch_new_token()
                except Exception as e:
                    print(f"\n[warn] Silent token refresh failed: {e} — retrying in 30s")
                    self._stop_event.wait(timeout=30)

    # ── Public accessor ────────────────────────────────────────────────────────

    @property
    def token(self) -> str:
        """Always returns a valid Copilot API token. Never blocks or prompts."""
        self._ensure_fresh()
        return self._token

    def stop(self):
        self._stop_event.set()


# ─── Chat Completions ────────────────────────────────────────────────────────────

def chat(
    token_manager: CopilotTokenManager,
    messages: list[dict],
    model: str = MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    stream: bool = True,
) -> str:
    headers = {
        "Authorization": f"Bearer {token_manager.token}",
        "Content-Type":  "application/json",
        **COPILOT_HEADERS,
    }
    payload = {
        "model":       model,
        "messages":    messages,
        "temperature": temperature,
        "max_tokens":  max_tokens,
        "stream":      stream,
    }

    resp = requests.post(
        f"{COPILOT_API_BASE}/chat/completions",
        headers=headers,
        json=payload,
        stream=stream,
        timeout=60,
    )
    resp.raise_for_status()

    if not stream:
        return resp.json()["choices"][0]["message"]["content"]

    full_reply = []
    print("Assistant: ", end="", flush=True)
    for line in resp.iter_lines():
        if not line:
            continue
        line = line.decode("utf-8")
        if line.startswith("data: "):
            chunk = line[6:]
            if chunk == "[DONE]":
                break
            try:
                parsed = json.loads(chunk)
                choices = parsed.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {}).get("content", "")
                if delta:
                    print(delta, end="", flush=True)
                    full_reply.append(delta)
            except (json.JSONDecodeError, KeyError):
                pass
    print()
    return "".join(full_reply)


# ─── Main ────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 56)
    print("  GitHub Copilot Python Client")
    print(f"  Model : {MODEL}")
    print(f"  Cache : {CACHE_DIR}")
    print("=" * 56 + "\n")

    github_token  = get_github_token()          # silent after first run
    token_manager = CopilotTokenManager(github_token)   # auto-refreshes forever

    conversation: list[dict] = [
        {
            "role":    "system",
            "content": "You are a helpful AI assistant. Answer clearly and concisely.",
        }
    ]

    print("Type your message. Type 'exit' or Ctrl+C to quit.\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break

            if not user_input or user_input.lower() in ("exit", "quit"):
                break

            conversation.append({"role": "user", "content": user_input})

            try:
                reply = chat(token_manager, conversation)
                conversation.append({"role": "assistant", "content": reply})
            except requests.HTTPError as e:
                print(f"\n[error] {e}")
                if e.response is not None:
                    print(f"[error] {e.response.text}")

    except KeyboardInterrupt:
        print("\nGoodbye!")
    finally:
        token_manager.stop()


if __name__ == "__main__":
    main()