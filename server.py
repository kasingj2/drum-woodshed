#!/usr/bin/env python3
from pathlib import Path
from flask import Flask, jsonify, send_file

LIBRARY_DIR = Path('library')
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac'}

app = Flask(__name__, static_folder='static', static_url_path='')


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/api/tracks')
def tracks():
    if not LIBRARY_DIR.exists():
        return jsonify([])
    files = sorted(
        f.name for f in LIBRARY_DIR.iterdir()
        if f.suffix.lower() in AUDIO_EXTENSIONS
    )
    return jsonify(files)


@app.route('/audio/<path:filename>')
def audio(filename):
    return send_file(LIBRARY_DIR / filename, conditional=True)
