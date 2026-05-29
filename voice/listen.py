import speech_recognition as sr
from voice.speak import get_speaking
from config import MIC_CALIBRATION_DURATION, MIC_CALIBRATE_INTERVAL
import time

recognizer = sr.Recognizer()
_microphone = sr.Microphone()
_last_calibration = 0
_calibrated = False


def _maybe_calibrate():
    global _last_calibration, _calibrated
    now = time.time()
    if not _calibrated or (now - _last_calibration) > MIC_CALIBRATE_INTERVAL:
        with _microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=MIC_CALIBRATION_DURATION)
        _last_calibration = now
        _calibrated = True


def listen():
    if get_speaking():
        return ""

    _maybe_calibrate()

    with _microphone as source:
        print("Escuchando...")

        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 1.4
        recognizer.non_speaking_duration = 0.8

        try:
            audio = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=15
            )
        except Exception:
            return ""

    try:
        text = recognizer.recognize_google(audio, language="es-ES")
        print("Tú:", text)
        return text
    except Exception:
        print(" No entendí")
        return ""
