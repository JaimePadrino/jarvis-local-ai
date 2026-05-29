from vision.screen_analyzer import capture_screen
import pytesseract
from ai.brain import ask_ai
from config import TESSERACT_PATH

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def analyze_screen_with_ai():

    img = capture_screen()

    text = pytesseract.image_to_string(img)

    prompt = f"""
Eres Jarvis, un asistente personal inteligente estilo Iron Man.

El usuario quiere que NO describas como un informe, sino que hables de forma natural, útil y proactiva.

Analiza la pantalla del usuario:

TEXTO DETECTADO:
{text}

Responde con este estilo:

- Di qué ve el usuario de forma natural (ej: "Veo que estás en YouTube")
- Explica brevemente lo que parece estar haciendo
- DA UNA RECOMENDACIÓN útil relacionada con lo que está viendo
- Sé breve, directo y útil como un asistente real

Ejemplos:
"Veo que estás en YouTube, si quieres puedo recomendarte vídeos similares."

"Estás programando en Python, puedo ayudarte a mejorar el código."

Ahora responde:
"""

    response = ask_ai(prompt)

    return response
