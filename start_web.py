"""
Jarvis Web Server — Entry Point

Starts the FastAPI web server with WebSocket support, voice engine,
and serves the frontend UI.
"""
import sys
import os

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.api.server import run_server

if __name__ == "__main__":
    run_server()