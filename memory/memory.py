import json
import os
import threading
import time

MEMORY_FILE = "data/memory.json"
MEMORY_MAX_ENTRIES = 100
MEMORY_SAVE_INTERVAL = 30

_memory_cache = []
_cache_lock = threading.Lock()
_last_save_time = 0
_initialized = False


def _ensure_initialized():
    global _initialized, _memory_cache
    if not _initialized:
        _memory_cache = _load_from_disk()
        _initialized = True


def _load_from_disk():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def _save_to_disk():
    global _last_save_time
    os.makedirs(os.path.dirname(MEMORY_FILE) or ".", exist_ok=True)
    tmp_path = MEMORY_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(_memory_cache, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, MEMORY_FILE)
    _last_save_time = time.time()


def load_memory():
    _ensure_initialized()
    with _cache_lock:
        return list(_memory_cache)


def save_memory(memory):
    global _memory_cache
    with _cache_lock:
        _memory_cache = memory
    _save_to_disk()


def add_message(role, content):
    global _memory_cache
    _ensure_initialized()
    with _cache_lock:
        _memory_cache.append({"role": role, "content": content})
        if len(_memory_cache) > MEMORY_MAX_ENTRIES:
            _memory_cache = _memory_cache[-MEMORY_MAX_ENTRIES:]
    now = time.time()
    if now - _last_save_time >= MEMORY_SAVE_INTERVAL:
        _save_to_disk()


def get_recent_memory(limit=10):
    _ensure_initialized()
    with _cache_lock:
        return list(_memory_cache[-limit:])


def save_now():
    _ensure_initialized()
    with _cache_lock:
        _save_to_disk()
