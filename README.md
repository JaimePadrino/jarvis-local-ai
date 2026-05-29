# Jarvis AI Assistant

Jarvis is a local AI assistant built with Python using:

* Ollama
* Qwen2.5-Coder:7B
* Voice synthesis
* Memory system
* Simple GUI

The assistant can talk, remember conversations, and interact through a graphical interface.

## Features

* Local AI assistant
* Voice output in Spanish
* Conversation memory
* Simple GUI
* Powered by Qwen2.5-Coder:7B
* Runs locally with Ollama

## Requirements

Before running the project, you need to install:

* Python 3.10+
* Ollama

Download Ollama here:

https://ollama.com

Then install the required model:

```bash
ollama pull qwen2.5-coder:7b
```

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
```

Enter the project folder:

```bash
cd YOUR_REPOSITORY
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running Jarvis

Start the assistant with:

```bash
start_jarvis.bat or start_jarvis.vbs
```

## Voice Configuration

Inside `config.py`:

```python
VOICE = "VOICE"
```

Change the value of `VOICE` to use another language or voice.

## Technologies Used

* Python
* Ollama
* Qwen2.5-Coder:7B
* Edge-TTS
* Tkinter / Custom GUI

## Notes

This project runs fully locally.

Make sure Ollama is running before starting Jarvis.

## Future Goals

* Better memory system
* Microphone input
* More tools and automation
* Smarter context handling
* Better GUI design

## License

MIT License
