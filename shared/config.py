import os
from dotenv import load_dotenv

load_dotenv()

# Core LLM models
MODEL = os.getenv("MODEL", "qwen2.5-coder:7b")

# Ollama endpoints
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")

# Voice
VOICE = os.getenv("VOICE", "es-ES-ElviraNeural")
RATE = os.getenv("RATE", "+5%")
PITCH = os.getenv("PITCH", "-2Hz")

# Timeouts
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# Memory
MEMORY_MAX_ENTRIES = int(os.getenv("MEMORY_MAX_ENTRIES", "200"))

# Paths
DATA_DIR = os.getenv("DATA_DIR", "data")

# Weather
WEATHER_LOCATION = os.getenv("WEATHER_LOCATION", "Madrid")

# Web server
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))

# Security
WS_API_KEY = os.getenv("WS_API_KEY", "")  # Empty = no auth

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/jarvis.log")
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "5242880"))  # 5MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "3"))
