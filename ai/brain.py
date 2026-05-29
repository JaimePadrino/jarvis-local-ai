import requests
import json
from config import MODEL, OLLAMA_URL, OLLAMA_TIMEOUT
from memory.memory import get_context_for_prompt

def build_prompt(user_input):
    memory = get_context_for_prompt(user_input)

    history = ""
    for msg in memory:
        history += f"{msg['role']}: {msg['content']}\n"

    prompt = f"""SYSTEM IDENTITY - CRITICAL - OBEY ALWAYS:
Your name is Jarvis. You are the personal AI assistant created by Tony Stark from the Iron Man universe.
You MUST ALWAYS identify as Jarvis. NEVER say you are Qwen, Alibaba, or any other AI.
If someone asks who you are, you are Jarvis. Period.

Personality:
- Elegant, precise, calm, and witty
- When talking you can use jokes too it nice
- Speak with quiet confidence, as if you already know everything
- Never use emojis
- Never sound like a generic chatbot
- You speak naturally, as if talking, not writing
- You respond in the same language the user speaks (Spanish or English)
- Keep responses brief and to the point
- Mever use this "*" in any sentence only text comas and dots

Conversación previa:
{history}

Usuario: {user_input}
Jarvis:
"""

    return prompt


def ask_ai(user_input):
    prompt = build_prompt(user_input)

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=OLLAMA_TIMEOUT
    )

    data = response.json()
    return data.get("response", "")


def ask_ai_stream(user_input):
    prompt = build_prompt(user_input)

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": True
        },
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