"""Application wiring and the main interaction loop."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .commands import registry
from .config import Settings
from .llm import AssistantError, ClaudeClient
from .logging_setup import setup_logging
from .scheduler import ReminderScheduler
from .storage import NoteStore, ReminderStore, TaskStore

log = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Everything command handlers may need."""

    settings: Settings
    tasks: TaskStore
    notes: NoteStore
    llm: ClaudeClient
    scheduler: ReminderScheduler


class Assistant:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        setup_logging(settings.log_level, settings.data_dir)

        data = settings.data_dir
        self.ctx = AppContext(
            settings=settings,
            tasks=TaskStore(data / "tasks.json"),
            notes=NoteStore(data / "notes.json"),
            llm=ClaudeClient(settings),
            scheduler=ReminderScheduler(
                ReminderStore(data / "reminders.json"), announce=self._announce
            ),
        )

        # Voice components are loaded only when voice mode is requested,
        # keeping text-mode startup instant.
        self._tts = None
        self._stt = None
        if settings.voice_enabled:
            from .speech import SpeechToText, TextToSpeech

            self._tts = TextToSpeech(rate=settings.tts_rate)
            self._stt = SpeechToText(
                listen_timeout=settings.stt_timeout,
                phrase_limit=settings.stt_phrase_limit,
            )
            if not self._stt.available:
                print("(Voice input unavailable — falling back to typed input.)")
            if not self._tts.available:
                print("(Voice output unavailable — responses will be text-only.)")

    # -- I/O helpers ----------------------------------------------------------

    def _announce(self, text: str) -> None:
        """Used by the background scheduler; prints and (optionally) speaks."""
        print(f"\n🔔 {text}")
        if self._tts is not None:
            self._tts.speak(text)

    def _read_input(self) -> str | None:
        """Get one user utterance (voice if available, else keyboard)."""
        if self._stt is not None and self._stt.available:
            print("🎤 Listening… (Ctrl+C to quit)")
            heard = self._stt.listen()
            if heard:
                print(f"You: {heard}")
                return heard
            if heard == "":
                return ""  # silence / not understood — just loop
            print("(Microphone trouble — type instead.)")
        try:
            return input("You: ")
        except EOFError:
            return None

    def _respond(self, text: str) -> None:
        print(f"Assistant: {text}")
        if self._tts is not None:
            self._tts.speak(text)

    # -- main loop ------------------------------------------------------------

    def run(self) -> int:
        print("Group Project Assistant ready. Type 'help' for commands, 'exit' to quit.")
        self.ctx.scheduler.start()
        try:
            while True:
                user_text = self._read_input()
                if user_text is None:
                    break
                user_text = user_text.strip()
                if not user_text:
                    continue

                result = registry.dispatch(self.ctx, user_text)
                if result is not None:  # handled locally — zero API calls
                    if result.text:
                        self._respond(result.text)
                    if result.should_exit:
                        break
                    continue

                self._ask_llm(user_text)
        except KeyboardInterrupt:
            print("\nGoodbye!")
        finally:
            self.ctx.scheduler.stop()
        return 0

    def _ask_llm(self, user_text: str) -> None:
        try:
            print("Assistant: ", end="", flush=True)
            chunks: list[str] = []
            for chunk in self.ctx.llm.ask(user_text):
                print(chunk, end="", flush=True)
                chunks.append(chunk)
            print()
            if self._tts is not None:
                self._tts.speak("".join(chunks))
        except AssistantError as exc:
            print()
            self._respond(str(exc))
        except Exception:  # noqa: BLE001 — keep the REPL alive on unexpected errors
            log.exception("Unexpected error during LLM call")
            print()
            self._respond("Something went wrong — see the log file for details.")
