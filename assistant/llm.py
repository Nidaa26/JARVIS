""" Responsibilities:

- maintain a rolling conversation history (trimmed to a configurable size)
- stream responses for fast time-to-first-word
- mark the system prompt for prompt caching
- translate SDK exceptions into one friendly :class:`AssistantError`

"""

from __future__ import annotations

import logging
from typing import Iterator

from .config import SYSTEM_PROMPT, Settings

log = logging.getLogger(__name__)


class AssistantError(Exception):
    """A user-facing error with a friendly message."""


class ClaudeClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._history: list[dict] = []
        self._client = None  # created lazily to keep startup fast

    # -- public API ----------------------------------------------------------

    def ask(self, user_text: str) -> Iterator[str]:
        """Send ``user_text`` with history; yield response text chunks."""
        import anthropic  # deferred import: ~200ms saved when only using local commands

        client = self._get_client(anthropic)
        messages = self._trimmed_history() + [{"role": "user", "content": user_text}]

        try:
            with client.messages.stream(
                model=self._settings.model,
                max_tokens=self._settings.max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
                thinking={"type": "adaptive"},
                output_config={"effort": self._settings.effort},
            ) as stream:
                for chunk in stream.text_stream:
                    yield chunk
                final = stream.get_final_message()
        except anthropic.AuthenticationError as exc:
            raise AssistantError(
                "Authentication failed. Check that ANTHROPIC_API_KEY is set correctly."
            ) from exc
        except anthropic.RateLimitError as exc:
            raise AssistantError("Rate limited by the API. Wait a moment and try again.") from exc
        except anthropic.APIConnectionError as exc:
            raise AssistantError("Could not reach the Claude API. Check your network.") from exc
        except anthropic.APIStatusError as exc:
            log.error("API error %s: %s", exc.status_code, exc.message)
            raise AssistantError(f"The Claude API returned an error ({exc.status_code}).") from exc

        if final.stop_reason == "refusal":
            raise AssistantError("I can't help with that request.")

        reply = "".join(b.text for b in final.content if b.type == "text")
        self._history.append({"role": "user", "content": user_text})
        self._history.append({"role": "assistant", "content": reply})
        log.debug(
            "tokens in=%s out=%s cached=%s",
            final.usage.input_tokens,
            final.usage.output_tokens,
            final.usage.cache_read_input_tokens,
        )

    def clear_history(self) -> None:
        self._history.clear()

    @property
    def history_length(self) -> int:
        return len(self._history)

    # -- internals -----------------------------------------------------------

    def _get_client(self, anthropic_module):
        if self._client is None:
            if not self._settings.api_key:
                raise AssistantError(
                    "ANTHROPIC_API_KEY is not set. Add it to your .env file or environment."
                )
            self._client = anthropic_module.Anthropic(
                max_retries=self._settings.api_max_retries,
                timeout=self._settings.request_timeout,
            )
        return self._client

    def _trimmed_history(self) -> list[dict]:
        """Last N messages, guaranteed to start with a user turn."""
        history = self._history[-self._settings.history_limit :]
        while history and history[0]["role"] != "user":
            history = history[1:]
        return history
