import os
import re
import time
import asyncio
import tempfile
import hashlib
import queue
import threading

import pygame

from config import TTS_ENGINE, PIPER_MODEL_PATH, VOICE, RATE, PITCH, TTS_MAX_RETRIES, TTS_CACHE_SIZE
from voice.tts_lock import tts_process_lock
import voice.piper_tts as piper_tts

# Initialize pygame mixer once
if pygame.mixer.get_init() is None:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)

# --- State ---
_speaking = False
_tts_listeners = []
_tts_queue = queue.Queue()
_worker_thread = None
_stop_worker = threading.Event()

# --- Edge-TTS in-memory LRU cache ---
_edge_cache = {}
_edge_cache_order = []


def _get_edge_cache_key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _get_cached_edge_path(text: str):
    key = _get_edge_cache_key(text)
    if key in _edge_cache:
        _edge_cache_order.remove(key)
        _edge_cache_order.append(key)
        return _edge_cache[key]
    return None


def _add_edge_cache(text: str, path: str):
    key = _get_edge_cache_key(text)
    if key in _edge_cache:
        _edge_cache_order.remove(key)
    elif len(_edge_cache) >= TTS_CACHE_SIZE:
        oldest = _edge_cache_order.pop(0)
        del _edge_cache[oldest]
    _edge_cache[key] = path
    _edge_cache_order.append(key)


# --- Public API ---

def clean_text(text: str) -> str:
    """Strip markdown, URLs and collapse whitespace."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_]{1,2}", "", text)
    text = re.sub(r"`+", "", text)
    text = " ".join(text.split())
    return text.strip()


def get_speaking() -> bool:
    return _speaking


def set_speaking(value: bool):
    global _speaking
    _speaking = value
    for listener in _tts_listeners:
        try:
            listener(value)
        except Exception:
            pass


def set_tts_listeners(on_error=None, on_state=None):
    global _tts_listeners
    _tts_listeners = []
    if on_error:
        _tts_listeners.append(on_error)
    if on_state:
        _tts_listeners.append(on_state)


def speak(text: str):
    text = text.strip() if text else ""
    if not text:
        return
    print("Jarvis:", text)
    _tts_queue.put(text)


# --- Internal playback helpers ---

def _play_wav(wav_path: str):
    pygame.mixer.music.load(wav_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)


# --- TTS engines ---

def _speak_piper(text: str) -> bool:
    if not piper_tts.is_available(PIPER_MODEL_PATH):
        return False
    try:
        wav_path = piper_tts.generate_audio(text, PIPER_MODEL_PATH)
        with tts_process_lock():
            set_speaking(True)
            _play_wav(wav_path)
        set_speaking(False)
        try:
            os.remove(wav_path)
        except Exception:
            pass
        return True
    except Exception:
        return False


def _speak_pyttsx3(text: str) -> bool:
    try:
        import pyttsx3
    except Exception:
        return False
    try:
        engine = pyttsx3.init()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        engine.save_to_file(text, wav_path)
        engine.runAndWait()
        with tts_process_lock():
            set_speaking(True)
            _play_wav(wav_path)
        set_speaking(False)
        try:
            os.remove(wav_path)
        except Exception:
            pass
        return True
    except Exception:
        return False


async def _edge_tts_generate(text: str, output_path: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice=VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(output_path)


def _speak_edge(text: str) -> bool:
    cached = _get_cached_edge_path(text)
    wav_path = cached
    try:
        if cached is None:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            asyncio.run(_edge_tts_generate(text, wav_path))
            _add_edge_cache(text, wav_path)
        with tts_process_lock():
            set_speaking(True)
            _play_wav(wav_path)
        set_speaking(False)
        return True
    except Exception:
        if cached is None and wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass
        return False


def _speak(text: str):
    text = clean_text(text)
    if not text:
        return
    engines = [e.strip() for e in TTS_ENGINE.split(",") if e.strip()]
    for engine in engines:
        success = False
        for _ in range(TTS_MAX_RETRIES):
            if engine == "piper":
                success = _speak_piper(text)
            elif engine == "pyttsx3":
                success = _speak_pyttsx3(text)
            elif engine == "edge":
                success = _speak_edge(text)
            if success:
                break
        if success:
            break


# --- Queue worker ---

def _tts_queue_worker():
    while not _stop_worker.is_set():
        try:
            text = _tts_queue.get(timeout=0.1)
        except queue.Empty:
            continue
        try:
            _speak(text)
        except Exception:
            pass
        finally:
            _tts_queue.task_done()


def _ensure_worker():
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        _stop_worker.clear()
        _worker_thread = threading.Thread(target=_tts_queue_worker, daemon=True)
        _worker_thread.start()


_ensure_worker()
