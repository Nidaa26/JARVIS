"""Speech-to-text using the optional SpeechRecognition package.

If SpeechRecognition / PyAudio are not installed (or no microphone is
present) the assistant transparently falls back to typed input.




"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class SpeechToText:
    def __init__(self, listen_timeout: float = 6.0, phrase_limit: float = 15.0) -> None:
        self._timeout = listen_timeout
        self._phrase_limit = phrase_limit
        self._recognizer = None
        self._mic = None
        try:
            import speech_recognition as sr

            self._sr = sr
            self._recognizer = sr.Recognizer()
            self._mic = sr.Microphone()
            with self._mic as source:  # one-time ambient noise calibration
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except ImportError:
            log.info("SpeechRecognition not installed; voice input unavailable.")
        except OSError:
            log.warning("No microphone found; voice input unavailable.")
            self._recognizer = None

    @property
    def available(self) -> bool:
        return self._recognizer is not None

    def listen(self) -> str | None:
        """Capture one utterance. Returns text, '' on silence, None on failure."""
        if not self.available:
            return None
        try:
            with self._mic as source:
                audio = self._recognizer.listen(
                    source, timeout=self._timeout, phrase_time_limit=self._phrase_limit
                )
            return self._recognizer.recognize_google(audio)
        except self._sr.WaitTimeoutError:
            return ""
        except self._sr.UnknownValueError:
            return ""
        except self._sr.RequestError as exc:
            log.warning("Speech recognition service error: %s", exc)
            return None
        except OSError as exc:
            log.warning("Microphone error: %s", exc)
            return None
