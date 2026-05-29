from ai.brain import ask_ai
from memory.memory import add_message
from voice.listen import listen
from voice.speak import speak
from voice.wake_word import listen_for_wake_word
from vision.vision_ai import analyze_screen_with_ai
from tools.web_search import search_web

from datetime import datetime
import requests
import threading
import time

running = True
active = False
_processing = False

_callbacks = {
    "on_user": None,
    "on_jarvis": None,
    "on_status": None,
}

_weather_cache = None
_weather_last_fetch = 0


def set_callbacks(on_user=None, on_jarvis=None, on_status=None):
    _callbacks["on_user"] = on_user
    _callbacks["on_jarvis"] = on_jarvis
    _callbacks["on_status"] = on_status


def _emit(kind, text):
    cb = _callbacks.get(kind)
    if cb:
        try:
            cb(text)
        except Exception:
            pass


def decide_action(user):
    user_lower = user.lower()

    if "pantalla" in user_lower:
        return "screen"

    if any(word in user_lower for word in ["busca", "buscar", "google", "investiga"]):
        return "web"

    return "chat"


def get_datetime():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def get_weather():
    global _weather_cache, _weather_last_fetch
    now = time.time()
    if _weather_cache and (now - _weather_last_fetch) < 600:
        return _weather_cache
    try:
        response = requests.get("https://wttr.in/Madrid?format=3", timeout=8)
        _weather_cache = response.text
        _weather_last_fetch = now
        return _weather_cache
    except Exception:
        return "No disponible"


def get_context():
    return f"""
Fecha y hora actual: {get_datetime()}
Clima actual: {get_weather()}
"""


def handle_user_input(user: str, speak_response: bool = True):
    user = (user or "").strip()
    if not user:
        return ""

    _emit("on_status", "Processing…")
    _emit("on_user", user)

    user_lower = user.lower()
    action = decide_action(user)

    if action == "screen":
        result = analyze_screen_with_ai()
        _emit("on_jarvis", result)
        if speak_response:
            speak(result)
        _emit("on_status", "Idle")
        return result

    if action == "web":
        query = user_lower
        query = query.replace("busca", "").replace("buscar", "").replace("investiga", "").strip()

        if speak_response:
            speak("Buscando en internet")

        results = search_web(query)

        prompt = f"""
Resume esta información de internet de forma clara:

{results}
"""
        response = ask_ai(prompt)
        _emit("on_jarvis", response)
        if speak_response:
            speak(response)
        _emit("on_status", "Idle")
        return response

    add_message("Usuario", user)

    context = get_context()
    prompt = f"""
Eres Jarvis, un asistente inteligente.

INFORMACIÓN DEL MUNDO REAL:
{context}

USUARIO:
{user}

Responde de forma natural, útil y precisa.
"""
    response = ask_ai(prompt)
    add_message("Jarvis", response)

    _emit("on_jarvis", response)
    if speak_response:
        speak(response)
    _emit("on_status", "Idle")
    return response


def wake_listener():
    global active, running, _processing

    while running:
        try:
            if not _processing and listen_for_wake_word():
                active = True
                _processing = False
                speak("Sí")
                _emit("on_status", "Listening…")
        except Exception as e:
            _emit("on_status", f"Voice error: {e}")
            time.sleep(0.8)
        time.sleep(0.1)


def conversation_loop():
    global active, running, _processing

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
                _processing = False
                _emit("on_status", "Idle")
                continue

            _processing = True
            handle_user_input(user, speak_response=True)
            _processing = False
        except Exception as e:
            _emit("on_status", f"Voice error: {e}")
            _processing = False
            time.sleep(0.8)


def main():
    print("Jarvis en segundo plano...")

    t1 = threading.Thread(target=wake_listener, daemon=True)
    t2 = threading.Thread(target=conversation_loop, daemon=True)

    t1.start()
    t2.start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
