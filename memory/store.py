"""
Memory Store — owns the conversation cache, disk I/O, and message management.

This is the single source of truth for conversation data.
All text processing utilities (tokenization, topic extraction) live here
because they are required by add_message.
"""
import json
import os
import re
import threading
import logging
from datetime import datetime

import requests

from shared.config import MEMORY_MAX_ENTRIES

log = logging.getLogger("jarvis.memory.store")

MEMORY_FILE = "data/memory.json"

_cache = []
_cache_lock = threading.Lock()
_initialized = False

# ──────────────────────────────────────────
# Text processing utilities
# ──────────────────────────────────────────

_SPANISH_STOPWORDS = frozenset([
    "a", "al", "ante", "abajo", "aquel", "aquella", "aquellas", "aquellos",
    "arriba", "asi", "aun", "aunque", "bien", "como", "con", "conmigo",
    "consigo", "contigo", "contra", "cual", "cuando", "de", "del", "desde",
    "donde", "el", "ella", "ellas", "ello", "ellos", "en", "entre", "era",
    "eran", "es", "esa", "esas", "ese", "eses", "esta", "estaba", "estado",
    "estados", "estar", "estas", "este", "esto", "estos", "estoy", "estan",
    "fin", "fue", "fueron", "ha", "haber", "habia", "han", "hasta", "hay",
    "la", "las", "le", "les", "lo", "los", "me", "mi", "mientras", "mio",
    "mis", "mismo", "mucho", "muy", "mas", "mi", "mia", "mias", "mio", "mios",
    "nos", "nosotras", "nosotros", "nuestra", "nuestras", "nuestro", "nuestros",
    "no", "o", "os", "para", "pero", "poco", "por", "porque", "que", "quien",
    "quienes", "se", "si", "sin", "sobre", "su", "sus", "suya", "suyas",
    "suyo", "suyos", "tal", "tambien", "tan", "te", "ti", "tiene", "tienen",
    "todo", "todos", "tu", "tus", "tu", "tuya", "tuyas", "tuyo", "tuyos",
    "un", "una", "unas", "uno", "unos", "usted", "ustedes", "ya", "yo",
    "y", "e", "ni", "o", "u",
])

_GREETING_PATTERNS = re.compile(
    r'^(hola|buenos?\s+di[as]|buenas?\s+(tardes|noches)|hey|que\s+tal|qu[eé]\s+tal|'
    r'saludos|buenas|hi|hello|yo\s+estoy\s+\w+|estoy\s+\w+)$',
    re.IGNORECASE
)

_QUESTION_PATTERNS = re.compile(
    r'^(qu[eé]|c[oó]mo|cu[aá]ndo|d[oó]nde|por\s+qu[eé]|cu[aá]l|cu[aá]nto|'
    r'puedes|sabes|conoces|es\s+\w+\s*\?|hay\s+)\b',
    re.IGNORECASE
)

_COMMAND_PATTERNS = re.compile(
    r'^(busca|buscar|investiga|abre|cierra|crea|elimina|borra|muestra|analiza|'
    r'dime|di\s+|haz|quiero\s+que|necesito\s+que|pon|configura|ajusta)\b',
    re.IGNORECASE
)

_FACT_PATTERNS = re.compile(
    r'^(mi\s+nombre\s+es|me\s+llamo|soy\s+\w+|trabajo\s+en|estudio\s+en|'
    r'vivo\s+en|tengo\s+\d|me\s+gusta|prefiero|mi\s+\w+\s+es)\b',
    re.IGNORECASE
)


def tokenize(text: str) -> list[str]:
    """Tokenize text into meaningful words, removing stopwords."""
    words = re.findall(r'[a-záéíóúñü]+', text.lower())
    return [w for w in words if w not in _SPANISH_STOPWORDS and len(w) > 2]


def extract_topics(text: str) -> list[str]:
    """Extract topic tags from text for scoring and search."""
    tokens = tokenize(text)
    topics = []
    seen = set()

    if _GREETING_PATTERNS.match(text.strip()):
        topics.append("greetings")
        seen.add("greetings")
    if _QUESTION_PATTERNS.match(text.strip()):
        topics.append("questions")
        seen.add("questions")
    if _COMMAND_PATTERNS.match(text.strip()):
        topics.append("commands")
        seen.add("commands")
    if _FACT_PATTERNS.match(text.strip()):
        topics.append("personal_facts")
        seen.add("personal_facts")

    for token in tokens:
        if token not in seen:
            topics.append(token)
            seen.add(token)

    return topics[:10]


def _score_importance(role: str, content: str, topics: list[str]) -> int:
    """Score a message's importance for memory retention."""
    if role == "Usuario":
        stripped = content.strip().lower()
        if len(stripped) <= 3 or stripped in ("hola", "hey", "mmmm", "vale", "si", "no"):
            return 1
        if "personal_facts" in topics:
            return 5
        if "commands" in topics:
            return 4
        if "questions" in topics:
            return 3
        return 2
    else:
        if "personal_facts" in topics:
            return 5
        if len(content) > 100:
            return 3
        if len(content) <= 20:
            return 1
        return 2


def get_embedding(text: str) -> list[float] | None:
    """Get embedding vector from Ollama for semantic search."""
    try:
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("embedding")
    except Exception as e:
        log.debug(f"Embedding unavailable: {e}")
        return None


# ──────────────────────────────────────────
# Disk I/O
# ──────────────────────────────────────────

def _load_from_disk() -> list:
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def _save_to_disk():
    os.makedirs(os.path.dirname(MEMORY_FILE) or ".", exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(_cache, f, indent=2, ensure_ascii=False)


def _migrate_entries():
    """Add missing fields to old memory entries."""
    global _cache
    changed = False
    for entry in _cache:
        if "timestamp" not in entry:
            entry["timestamp"] = "unknown"
            changed = True
        if "topics" not in entry:
            entry["topics"] = extract_topics(entry.get("content", ""))
            changed = True
        if "importance" not in entry:
            entry["importance"] = _score_importance(
                entry.get("role", "Usuario"),
                entry.get("content", ""),
                entry.get("topics", [])
            )
            changed = True
    if changed:
        _save_to_disk()


def _ensure_init():
    global _cache, _initialized
    if not _initialized:
        _cache = _load_from_disk()
        _migrate_entries()
        _initialized = True


# ──────────────────────────────────────────
# Public API
# ──────────────────────────────────────────

def add_message(role: str, content: str):
    """Add a message to the conversation memory."""
    _ensure_init()
    topics = extract_topics(content)
    importance = _score_importance(role, content, topics)
    entry = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "topics": topics,
        "importance": importance,
    }

    embedding = get_embedding(content)
    if embedding:
        entry["embedding"] = embedding

    with _cache_lock:
        _cache.append(entry)
        if len(_cache) > MEMORY_MAX_ENTRIES:
            _cache[:] = _keep_important(_cache)
        _save_to_disk()


def get_recent_memory(limit: int = 10) -> list:
    """Return the most recent messages."""
    _ensure_init()
    with _cache_lock:
        return list(_cache[-limit:])


def clear_memory():
    """Wipe all conversation memory."""
    global _cache
    with _cache_lock:
        _cache = []
    _save_to_disk()


def get_all_entries() -> list:
    """Return all entries (used by search module)."""
    _ensure_init()
    return _cache


def get_cache_lock() -> threading.Lock:
    """Return the cache lock (used by search module for thread safety)."""
    return _cache_lock


def _keep_important(entries: list) -> list:
    """Prune memory, keeping the most important entries."""
    if len(entries) <= MEMORY_MAX_ENTRIES:
        return entries
    scored = []
    n = len(entries)
    for i, entry in enumerate(entries):
        recency = (i + 1) / n
        importance = entry.get("importance", 2) / 5.0
        scored.append((entry, recency * 0.4 + importance * 0.6))
    scored.sort(key=lambda x: x[1], reverse=True)
    kept_entries = [s[0] for s in scored[:MEMORY_MAX_ENTRIES]]
    kept_entries.sort(key=lambda e: entries.index(e))
    return kept_entries
