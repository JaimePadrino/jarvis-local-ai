"""
Memory Context — builds the conversation context window for LLM prompts.

Combines recent messages with semantically relevant older messages.
"""
from memory.store import get_recent_memory
from memory.search import search_memory


def get_context_for_prompt(user_input: str, limit: int = 10) -> list:
    """Build a context window combining recent and relevant memory entries."""
    recent_count = min(3, limit)
    search_count = limit - recent_count

    recent = get_recent_memory(recent_count)
    relevant = search_memory(user_input, limit=search_count + recent_count)

    seen_ids = set()
    combined = []

    for entry in recent:
        entry_id = (entry.get("role", ""), entry.get("content", ""))
        if entry_id not in seen_ids:
            combined.append(entry)
            seen_ids.add(entry_id)

    for entry in relevant:
        entry_id = (entry.get("role", ""), entry.get("content", ""))
        if entry_id not in seen_ids:
            combined.append(entry)
            seen_ids.add(entry_id)

    return combined[:limit]
