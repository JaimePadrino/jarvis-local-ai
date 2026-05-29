MODEL = "qwen2.5-coder:7b"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_STREAM_URL = "http://localhost:11434/api/generate"
VOICE = "es-ES-AlvaroNeural"
RATE = "+5%"
PITCH = "-2Hz"
OLLAMA_TIMEOUT = 60
TTS_TIMEOUT = 15
TTS_MAX_RETRIES = 2
TTS_MAX_VOICES = 3
TTS_CACHE_SIZE = 50
MEMORY_MAX_ENTRIES = 100
MEMORY_SAVE_INTERVAL = 30
WEATHER_REFRESH_INTERVAL = 600
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
MIC_CALIBRATION_DURATION = 1.2
MIC_CALIBRATE_INTERVAL = 30

# TTS Engine Priority: piper,pyttsx3,edge
TTS_ENGINE = "piper,pyttsx3,edge"
PIPER_MODEL_PATH = "data/voices/es_ES-sharvard-medium.onnx"
