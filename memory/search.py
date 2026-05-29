"""
Memory Search — semantic and keyword search over conversation history.
"""
import time
import logging
from datetime import datetime

from memory.store import (
    tokenize,
    get_embedding,
    get_all_entries,
    get_cache_lock,
    get_recent_memory,
)

log = logging.getLogger("jarvis.memory.search")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_memory(query: str, limit: int = 10) -> list:
    """Search conversation memory using keyword + semantic matching."""
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return get_recent_memory(limit)

    query_embedding = get_embedding(query)

    now = time.time()
    scored = []

    lock = get_cache_lock()
    entries = get_all_entries()

    with lock:
        for entry in entries:
            entry_tokens = set(entry.get("topics", []))
            content_tokens = set(tokenize(entry.get("content", "")))
            all_entry_tokens = entry_tokens | content_tokens
            overlap = len(query_tokens & all_entry_tokens)

            if overlap == 0 and not query_embedding:
                continue

            ts = entry.get("timestamp", "unknown")
            if ts != "unknown":
                try:
                    entry_time = datetime.fromisoformat(ts).timestamp()
                    age_hours = (now - entry_time) / 3600
                    recency_weight = max(0.1, 1.0 / (1.0 + age_hours * 0.05))
                except Exception:
                    recency_weight = 0.3
            else:
                recency_weight = 0.3

            importance_weight = entry.get("importance", 2) / 5.0

            if query_embedding and "embedding" in entry:
                semantic_score = cosine_similarity(query_embedding, entry["embedding"])
                score = semantic_score * 0.7 + overlap * 0.1 + importance_weight * 0.2
            else:
                score = overlap * (recency_weight * 0.5 + importance_weight * 0.5)

            scored.append((entry, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [entry for entry, _ in scored[:limit]]
