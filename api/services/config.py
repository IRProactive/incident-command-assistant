"""
Runtime-configurable settings for the guidance layer, settable from the
frontend's Settings panel without a container restart or rebuild.

Held in memory only — not persisted to disk or the database. That's a
deliberate choice: an API key entered through the UI would otherwise sit
in plaintext in the SQLite file or the mounted volume. The tradeoff is
that it's cleared on every restart. For a deployment where re-entering
the key each restart is unacceptable friction, set ANTHROPIC_API_KEY
(and LLM_PROVIDER=anthropic) as environment variables in
docker-compose.yml instead — those seed the initial in-memory value and
the UI can still override them for the running session.
"""
import os
from threading import Lock

_lock = Lock()
_state = {
    "provider": os.getenv("LLM_PROVIDER", "none"),
    "api_key": os.getenv("ANTHROPIC_API_KEY") or None,
    "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
}

SUPPORTED_PROVIDERS = ("none", "anthropic")


def get_provider() -> str:
    with _lock:
        return _state["provider"]


def get_api_key() -> str | None:
    with _lock:
        return _state["api_key"]


def get_model() -> str:
    with _lock:
        return _state["model"]


def set_llm_config(provider: str, api_key: str | None = None, model: str | None = None) -> None:
    with _lock:
        _state["provider"] = provider
        # Only overwrite the key if the caller actually sent one — an
        # empty/omitted field on a settings update shouldn't silently
        # wipe a key that was set via env var or an earlier UI save.
        if api_key:
            _state["api_key"] = api_key
        if model:
            _state["model"] = model


def status() -> dict:
    with _lock:
        return {
            "provider": _state["provider"],
            "model": _state["model"],
            "api_key_configured": bool(_state["api_key"]),
        }
