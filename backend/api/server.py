"""
Jarvis Web Server — FastAPI application with WebSocket support.

This is the main API layer. It:
- Serves the frontend static files
- Handles WebSocket chat (streaming LLM responses)
- Broadcasts system stats to connected clients
- Starts voice engine threads on startup
"""
import os
import sys
import time
import json
import asyncio
import threading
import tempfile
import logging

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.logging import setup_logging
setup_logging()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from shared.config import MODEL, OLLAMA_URL, OLLAMA_TIMEOUT, WEB_HOST, WEB_PORT, WS_API_KEY
from backend.core.brain import build_prompt
from backend.core.llm import ask_ai_stream_async
from backend.api.routes import router
from backend.services.stats import get_stats
from backend.services.weather import get_weather
from memory.store import add_message
from voice.tts import speak as tts_speak

import httpx

log = logging.getLogger("jarvis.backend.api.server")

app = FastAPI(title="J.A.R.V.I.S", version="3.0")

# Mount REST routes
app.include_router(router)

# Static files — served from frontend/static/
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_static_dir = os.path.join(_project_root, "frontend", "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

_start_time = time.time()
_connected_clients: set[WebSocket] = set()
_main_loop = None


def get_uptime() -> int:
    """Return server uptime in seconds."""
    return int(time.time() - _start_time)


# ──────────────────────────────────────────
# HTML index
# ──────────────────────────────────────────
@app.get("/")
async def index():
    html_path = os.path.join(_static_dir, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


# ──────────────────────────────────────────
# WebSocket
# ──────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    if WS_API_KEY:
        try:
            auth_msg = await asyncio.wait_for(ws.receive_text(), timeout=5)
            auth_data = json.loads(auth_msg)
            if auth_data.get("api_key") != WS_API_KEY:
                await ws.send_json({"type": "error", "content": "Unauthorized"})
                await ws.close()
                return
        except Exception:
            await ws.send_json({"type": "error", "content": "Auth timeout"})
            await ws.close()
            return

    _connected_clients.add(ws)
    log.info("WebSocket client connected")

    try:
        await ws.send_json({"type": "status", "content": "Connected"})

        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            content = msg.get("content", "").strip()

            if not content:
                continue

            await ws.send_json({"type": "status", "content": "Processing..."})

            try:
                add_message("Usuario", content)

                prompt = build_prompt(content)
                full_response = ""

                async for token in ask_ai_stream_async(prompt):
                    full_response += token
                    await ws.send_json({"type": "token", "content": token})

                add_message("Jarvis", full_response)
                await ws.send_json({"type": "response", "content": full_response})

                if full_response.strip():
                    threading.Thread(target=tts_speak, args=(full_response,), daemon=True).start()

                await ws.send_json({"type": "status", "content": "Idle"})

            except Exception as e:
                log.error(f"Error processing message: {e}")
                try:
                    await ws.send_json({"type": "error", "content": str(e)})
                    await ws.send_json({"type": "status", "content": "Idle"})
                except Exception:
                    pass

    except WebSocketDisconnect:
        log.info("WebSocket client disconnected")
    except Exception as e:
        log.error(f"WebSocket error: {e}")
    finally:
        _connected_clients.discard(ws)


# ──────────────────────────────────────────
# Background broadcasting
# ──────────────────────────────────────────
async def _broadcast_stats():
    """Periodically push system stats to all connected WebSocket clients."""
    while True:
        try:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(None, get_stats)
            weather = await loop.run_in_executor(None, get_weather)
            msg = {
                "type": "stats",
                **stats,
                "uptime": get_uptime(),
                "weather_text": weather.get("text", ""),
                "weather_details": weather.get("details", {}),
            }
            for client in list(_connected_clients):
                try:
                    await client.send_json(msg)
                except Exception:
                    _connected_clients.discard(client)
        except Exception as e:
            log.debug(f"Broadcast error: {e}")
        await asyncio.sleep(3)


async def _broadcast_event(msg: dict):
    """Send a message to all connected clients (used by voice pipeline callbacks)."""
    for client in list(_connected_clients):
        try:
            await client.send_json(msg)
        except Exception:
            _connected_clients.discard(client)


# ──────────────────────────────────────────
# Startup
# ──────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global _main_loop
    _main_loop = asyncio.get_event_loop()

    # Clean stale TTS lock from crashed sessions
    lock_path = os.path.join(tempfile.gettempdir(), "jarvis_tts.lock")
    if os.path.exists(lock_path):
        try:
            os.remove(lock_path)
            log.info("Removed stale TTS lock file")
        except Exception:
            pass

    asyncio.create_task(_broadcast_stats())

    # Start voice engine (optional — won't crash if no mic)
    try:
        from voice.pipeline import set_callbacks, wake_listener, conversation_loop

        def on_user(text):
            asyncio.run_coroutine_threadsafe(
                _broadcast_event({"type": "user", "content": text}), _main_loop
            )

        def on_jarvis(text):
            asyncio.run_coroutine_threadsafe(
                _broadcast_event({"type": "response", "content": text}), _main_loop
            )

        def on_status(status):
            asyncio.run_coroutine_threadsafe(
                _broadcast_event({"type": "status", "content": status}), _main_loop
            )

        set_callbacks(on_user=on_user, on_jarvis=on_jarvis, on_status=on_status)
        threading.Thread(target=wake_listener, daemon=True).start()
        threading.Thread(target=conversation_loop, daemon=True).start()
        log.info("Voice engine threads started")
    except Exception as e:
        log.warning(f"Voice engine unavailable (no microphone?): {e}")

    log.info("Jarvis web server started")


def run_server():
    """Entry point to start the Jarvis web server."""
    import uvicorn
    print(f"JARVIS Web Interface starting on http://localhost:{WEB_PORT}")
    print(f"Access from other devices: http://<your-ip>:{WEB_PORT}")
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT, log_level="warning")
