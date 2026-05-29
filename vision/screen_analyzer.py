import mss
import numpy as np
from PIL import Image
import pytesseract
from config import TESSERACT_PATH

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def capture_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)

        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return img


def analyze_screen():

    img = capture_screen()

    text = pytesseract.image_to_string(img)

    lines = text.split("\n")

    clean_lines = []

    for line in lines:
        line = line.strip()

        if len(line) < 3:
            continue

        if line.lower() in ["", " ", None]:
            continue

        clean_lines.append(line)

    clean_text = "\n".join(clean_lines)

    if not clean_text.strip():
        return "No veo información clara en pantalla."

    return clean_text[:800]
