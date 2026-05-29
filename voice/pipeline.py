"""
Voice Pipeline — orchestrates the wake word → listen → AI → speak loop.

This module contains the background threads that power Jarvis's voice interaction.
It replaces the old main.py's conversation logic with clean separation of concerns.
"""
import time
import logging

from backend.core.brain import build_prompt
from backend.core.llm import ask_ai
from memory.store import add_message
from voice.tts import speak
from voice.stt import listen, listen_for_wake_word

log = logging.getLogger("jarvis.voice.pipeline")

running = True
active = False

# Callbacks for GUI/Web to mirror voice events
_callbacks = {
    "on_user": None,
    "on_jarvis": None,
    "on_status": None,
}


def set_callbacks(on_user=None, on_jarvis=None, on_status=None):
    """Register callbacks to receive voice pipeline events."""
    _callbacks["on_user"] = on_user
    _callbacks["on_jarvis"] = on_jarvis
    _callbacks["on_status"] = on_status


def _emit(kind: str, text: str):
    """Safely emit a callback event."""
    cb = _callbacks.get(kind)
    if cb:
        try:
            cb(text)
        except Exception:
            pass


def handle_user_input(user: str, speak_response: bool = True) -> str:
    """
    Process a user message through the full AI pipeline.
    Used by both voice and typed input.
    """
    user = (user or "").strip()
    if not user:
        return ""

    _emit("on_status", "Processing…")
    _emit("on_user", user)

    add_message("Usuario", user)

    prompt = build_prompt(user)
    response = ask_ai(prompt)

    add_message("Jarvis", response)

    _emit("on_jarvis", response)
    if speak_response:
        speak(response)
    _emit("on_status", "Idle")
    return response


def wake_listener():
    """Background thread: continuously listen for the 'Jarvis' wake word."""
    global active, running

    while running:
        try:
            if listen_for_wake_word():
                active = True
                speak("Sí")
                _emit("on_status", "Listening…")
        except Exception as e:
            _emit("on_status", f"Voice error: {e}")
            time.sleep(0.8)
        time.sleep(0.1)


def conversation_loop():
    """Background thread: when active, listen for commands and process them."""
    global active, running

    while running:
        try:
            if not active:
                time.sleep(0.2)
                continue

            user = listen()

            if not user:
                continue

            user_lower = user.lower()

            if "salir" in user_lower:
                speak("Volviendo a modo espera")
                active = False
                _emit("on_status", "Idle")
                continue

            handle_user_input(user, speak_response=True)
        except Exception as e:
            _emit("on_status", f"Voice error: {e}")
            time.sleep(0.8)
