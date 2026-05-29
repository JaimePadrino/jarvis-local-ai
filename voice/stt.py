"""
Speech-to-Text — handles microphone listening and wake word detection.

Merges the previously separate listen.py and wake_word.py into one module.
"""
import speech_recognition as sr
import logging

from voice.tts import get_speaking

log = logging.getLogger("jarvis.voice.stt")

_recognizer = sr.Recognizer()


def listen() -> str:
    """Listen for user speech and return transcribed text. Returns '' on failure."""
    if get_speaking():
        return ""

    with sr.Microphone() as source:
        log.debug("Listening...")

        _recognizer.dynamic_energy_threshold = True
        _recognizer.pause_threshold = 1.4
        _recognizer.non_speaking_duration = 0.8
        _recognizer.adjust_for_ambient_noise(source, duration=1.2)

        try:
            audio = _recognizer.listen(source, timeout=None, phrase_time_limit=None)
        except Exception:
            return ""

    try:
        text = _recognizer.recognize_google(audio, language="es-ES")
        log.info(f"Heard: {text}")
        return text
    except Exception:
        log.debug("Could not understand audio")
        return ""


def listen_for_wake_word() -> bool:
    """Listen for the 'Jarvis' wake word. Returns True if detected."""
    if get_speaking():
        return False

    with sr.Microphone() as source:
        _recognizer.dynamic_energy_threshold = True
        _recognizer.pause_threshold = 0.8
        _recognizer.non_speaking_duration = 0.5
        _recognizer.adjust_for_ambient_noise(source, duration=0.5)

        try:
            audio = _recognizer.listen(source, timeout=1, phrase_time_limit=3)
        except sr.WaitTimeoutError:
            return False
        except Exception:
            return False

    try:
        text = _recognizer.recognize_google(audio, language="es-ES").lower()
        if "jarvis" in text or "harvis" in text or "yervis" in text:
            log.info(f"Wake word detected: '{text}'")
            return True
    except Exception:
        pass

    return False
