"""
Text-to-Speech — handles all voice output using edge-tts.

Provides thread-safe speaking with a simple lock to prevent overlapping audio.
"""
import asyncio
import edge_tts
import tempfile
import os
import threading
import logging
from playsound import playsound

from shared.config import VOICE

log = logging.getLogger("jarvis.voice.tts")

_speaking = False
_lock = threading.Lock()


def set_speaking(state: bool):
    global _speaking
    _speaking = state


def get_speaking() -> bool:
    return _speaking


def clean_text(text: str) -> str:
    return text.replace("\n", " ").strip()


async def _speak_async(text: str):
    """Generate and play TTS audio."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        filename = f.name

    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(filename)

    playsound(filename)
    try:
        os.remove(filename)
    except Exception:
        pass


def _run(text: str):
    """Internal TTS runner with lock protection."""
    if not _lock.acquire(timeout=30):
        log.warning("TTS lock timeout, skipping")
        return

    set_speaking(True)
    log.info(f"TTS starting: {text[:50]}...")
    try:
        asyncio.run(_speak_async(text))
        log.info("TTS completed")
    except Exception as e:
        log.error(f"TTS error: {e}")
    finally:
        set_speaking(False)
        _lock.release()


def speak(text: str):
    """Speak text aloud in a background thread. Non-blocking."""
    text = clean_text(text)
    if not text:
        return
    print("Jarvis:", text)
    threading.Thread(target=_run, args=(text,), daemon=True).start()
