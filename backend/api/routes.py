"""
REST API Routes — HTTP endpoints for stats, weather, memory.

Separated from the WebSocket server for clarity.
"""
import asyncio
import logging

from fastapi import APIRouter

from backend.services.stats import get_stats
from backend.services.weather import get_weather
from memory.store import get_recent_memory, clear_memory
from memory.search import search_memory

log = logging.getLogger("jarvis.backend.api.routes")

router = APIRouter()


@router.get("/api/stats")
async def api_stats():
    loop = asyncio.get_event_loop()
    stats = await loop.run_in_executor(None, get_stats)
    from backend.api.server import get_uptime
    return {**stats, "uptime": get_uptime()}


@router.get("/api/weather")
async def api_weather():
    loop = asyncio.get_event_loop()
    w = await loop.run_in_executor(None, get_weather)
    return {"text": w.get("text", ""), "details": w.get("details", {})}


@router.get("/api/search")
async def api_search(q: str = "", limit: int = 10):
    if not q:
        return {"results": []}
    return {"results": search_memory(q, limit=limit)}


@router.get("/api/memory")
async def api_memory(limit: int = 20):
    return {"messages": get_recent_memory(limit=limit)}


@router.post("/api/clear_memory")
async def api_clear_memory():
    clear_memory()
    return {"status": "ok"}
