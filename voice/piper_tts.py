import os
import tempfile
import wave
import threading

_piper_voice = None
_load_lock = threading.Lock()


def _load_voice(model_path: str):
    global _piper_voice
    if _piper_voice is not None:
        return _piper_voice

    with _load_lock:
        if _piper_voice is not None:
            return _piper_voice

        from piper import PiperVoice
        _piper_voice = PiperVoice.load(model_path)
        return _piper_voice


def generate_audio(text: str, model_path: str) -> str:
    voice = _load_voice(model_path)

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        wav_path = f.name

    with wave.open(wav_path, 'wb') as wav_file:
        voice.synthesize_wav(text, wav_file)

    return wav_path


def is_available(model_path: str) -> bool:
    return os.path.exists(model_path)
