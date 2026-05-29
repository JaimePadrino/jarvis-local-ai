"""
Brain — Prompt builder for Jarvis.

Constructs the full prompt including system identity, conversation memory,
and the user's current input. Has NO knowledge of HTTP or LLM transport.
"""
from memory.context import get_context_for_prompt


def build_prompt(user_input: str) -> str:
    """Build the full LLM prompt with system identity and conversation history."""
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
- Speak with quiet confidence, as if you already know everything
- Never use emojis
- Never sound like a generic chatbot
- You speak naturally, as if talking, not writing
- You respond in the same language the user speaks (Spanish or English)
- Keep responses brief and to the point

Conversación previa:
{history}

Usuario: {user_input}
Jarvis:
"""
    return prompt
