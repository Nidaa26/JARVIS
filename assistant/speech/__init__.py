"""Voice I/O: text-to-speech and speech-to-text with graceful fallbacks."""

from .stt import SpeechToText
from .tts import TextToSpeech

__all__ = ["SpeechToText", "TextToSpeech"]
