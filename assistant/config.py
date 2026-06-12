"""Centralised, environment-driven configuration.

Every tunable value lives here instead of being hardcoded around the
codebase. Values are read from environment variables (a local ``.env``
file is loaded automatically when python-dotenv is installed).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # optional dependency — the app works without it
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

_TRUTHY = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings for the assistant."""

    # --- Claude API ---
    model: str = field(default_factory=lambda: os.getenv("ASSISTANT_MODEL", "claude-opus-4-8"))
    max_tokens: int = field(default_factory=lambda: _env_int("ASSISTANT_MAX_TOKENS", 8000))
    # "low" keeps spoken answers fast; raise to "high" for harder questions.
    effort: str = field(default_factory=lambda: os.getenv("ASSISTANT_EFFORT", "low"))
    api_max_retries: int = field(default_factory=lambda: _env_int("ASSISTANT_API_RETRIES", 3, 0))
    request_timeout: float = field(
        default_factory=lambda: float(os.getenv("ASSISTANT_REQUEST_TIMEOUT", "120"))
    )

    # --- Conversation ---
    # Maximum number of messages (user + assistant) kept in the rolling
    # history sent with each request. Smaller = faster + cheaper.
    history_limit: int = field(default_factory=lambda: _env_int("ASSISTANT_HISTORY_LIMIT", 20))

    # --- Voice ---
    voice_enabled: bool = field(default_factory=lambda: _env_bool("ASSISTANT_VOICE", False))
    tts_rate: int = field(default_factory=lambda: _env_int("ASSISTANT_TTS_RATE", 185))
    stt_timeout: float = field(default_factory=lambda: float(os.getenv("ASSISTANT_STT_TIMEOUT", "6")))
    stt_phrase_limit: float = field(
        default_factory=lambda: float(os.getenv("ASSISTANT_STT_PHRASE_LIMIT", "15"))
    )

    # --- Storage / logging ---
    data_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("ASSISTANT_DATA_DIR", Path.home() / ".group-project-assistant")
        )
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    @property
    def api_key(self) -> str | None:
        """Read lazily so the key never sits on the settings object dump."""
        return os.getenv("ANTHROPIC_API_KEY")


SYSTEM_PROMPT = """\
You are an Assistant, a friendly and efficient helper for someone working on a project. You answer questions, help plan and break down
work, draft text, and explain concepts.

Guidelines:
- Keep answers brief and conversational; they may be read aloud.
- Lead with the answer, then add only essential detail.
- Use plain text (no markdown tables or code fences) unless the user asks
  for code.
"""
