import sys
import os
import threading
import webbrowser
import time
from app import app, db

def open_browser():
    """Wait for server to start then open browser"""
    time.sleep(1.5)  # Give the server a second to start
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    # Start browser thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run the Flask app
    # Note: debug=False is required for PyInstaller bundles
    app.run(host='127.0.0.1', port=5000, debug=False)
