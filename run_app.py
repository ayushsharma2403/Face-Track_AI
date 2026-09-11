import os
import sys

# Ensure running in project venv if executed globally
base_dir = os.path.dirname(os.path.abspath(__file__))
candidates = [
    os.path.join(base_dir, '.venv_cam', 'Scripts', 'python.exe'),
    os.path.join(base_dir, '.venv', 'Scripts', 'python.exe')
]
for exe in candidates:
    if os.path.exists(exe):
        try:
            import cv2
            import flask
        except (ImportError, AttributeError):
            os.execv(exe, [exe, os.path.join(base_dir, 'app.py')])

from app import app

if __name__ == '__main__':
    print("Starting Face-Track AI server on http://127.0.0.1:5000")
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
