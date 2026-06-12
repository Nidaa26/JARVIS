"""Text-to-speech with per-platform backends and graceful degradation.

Backend selection order:
- macOS:   built-in ``say`` command (zero dependencies)
- Windows: ``pyttsx3`` (SAPI5) if installed, else built-in PowerShell SAPI
- Linux:   ``pyttsx3`` (espeak) if installed
- fallback: silent (text is always printed by the app regardless)
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys

log = logging.getLogger(__name__)


class _Backend:
    name = "null"

    def speak(self, text: str) -> None:  # pragma: no cover - interface
        pass


class _SayBackend(_Backend):
    """macOS built-in `say`."""

    name = "macos-say"

    def __init__(self, rate: int) -> None:
        self._rate = rate

    def speak(self, text: str) -> None:
        subprocess.run(["say", "-r", str(self._rate), text], check=False)


class _Pyttsx3Backend(_Backend):
    """Cross-platform pyttsx3 (SAPI5 on Windows, espeak on Linux)."""

    name = "pyttsx3"

    def __init__(self, rate: int) -> None:
        import pyttsx3

        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", rate)

    def speak(self, text: str) -> None:
        self._engine.say(text)
        self._engine.runAndWait()


class _PowerShellBackend(_Backend):
    """Windows built-in SAPI via PowerShell — no Python packages needed."""

    name = "powershell-sapi"

    def speak(self, text: str) -> None:
        safe = text.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "(New-Object System.Speech.Synthesis.SpeechSynthesizer)"
            f".Speak('{safe}')"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


class TextToSpeech:
    """Facade that picks the best available backend at construction time."""

    def __init__(self, rate: int = 185) -> None:
        self._backend = self._select_backend(rate)
        log.info("TTS backend: %s", self._backend.name)

    @property
    def available(self) -> bool:
        return self._backend.name != "null"

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def speak(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        try:
            self._backend.speak(text)
        except Exception:  # noqa: BLE001 — voice failure must never crash the app
            log.exception("TTS backend %s failed; continuing in text mode", self._backend.name)
            self._backend = _Backend()

    @staticmethod
    def _select_backend(rate: int) -> _Backend:
        if sys.platform == "darwin" and shutil.which("say"):
            return _SayBackend(rate)
        try:
            return _Pyttsx3Backend(rate)
        except Exception:  # pyttsx3 missing or no audio device
            log.debug("pyttsx3 unavailable", exc_info=True)
        if sys.platform == "win32" and shutil.which("powershell"):
            return _PowerShellBackend()
        log.warning("No text-to-speech backend available; responses will be text-only.")
        return _Backend()
