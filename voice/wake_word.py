import speech_recognition as sr
import time
from config import MIC_CALIBRATION_DURATION, MIC_CALIBRATE_INTERVAL

recognizer = sr.Recognizer()
_microphone = sr.Microphone()
_last_calibration = 0
_calibrated = False

WAKE_WORD = "jarvis"


def _maybe_calibrate():
    global _last_calibration, _calibrated
    now = time.time()
    if not _calibrated or (now - _last_calibration) > MIC_CALIBRATE_INTERVAL:
        with _microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=MIC_CALIBRATION_DURATION)
        _last_calibration = now
        _calibrated = True


def listen_for_wake_word():
    _maybe_calibrate()

    with _microphone as source:
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 1.2
        recognizer.non_speaking_duration = 0.6

        try:
            audio = recognizer.listen(
                source,
                timeout=5,
                phrase_time_limit=4
            )

            text = recognizer.recognize_google(audio, language="es-ES")
            text = text.lower().strip()

            if not text:
                return False

            if len(text) > 20:
                return False

            if WAKE_WORD in text:
                return True

        except Exception:
            return False

    return False
