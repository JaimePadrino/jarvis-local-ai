"""
LLM Client — handles all communication with Ollama.

Provides synchronous, synchronous-streaming, and async-streaming interfaces.
This module has NO knowledge of prompts or memory — it just sends text to the LLM.
"""
import json
import logging

import requests
import httpx

from shared.config import MODEL, OLLAMA_URL, OLLAMA_TIMEOUT

log = logging.getLogger("jarvis.backend.core.llm")


def ask_ai(prompt: str) -> str:
    """Synchronous, non-streaming call to Ollama. Returns full response text."""
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False},
        timeout=OLLAMA_TIMEOUT
    )
    data = response.json()
    return data.get("response", "")


def ask_ai_stream(prompt: str):
    """Synchronous generator that yields tokens one by one."""
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": True},
        stream=True,
        timeout=OLLAMA_TIMEOUT
    )
    for line in response.iter_lines():
        if line:
            try:
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    yield token
            except Exception:
                pass


async def ask_ai_stream_async(prompt: str):
    """Async generator that yields tokens. For use in FastAPI/async contexts."""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": True},
            timeout=httpx.Timeout(OLLAMA_TIMEOUT, connect=10.0)
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "error" in data:
                        raise Exception(data["error"])
                    token = data.get("response", "")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    pass
