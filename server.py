#!/usr/bin/env python3
import socket
from pathlib import Path
from flask import Flask, jsonify, send_file, abort

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
    base = LIBRARY_DIR.resolve()
    target = (base / filename).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        abort(404)
    if target.suffix.lower() not in AUDIO_EXTENSIONS or not target.is_file():
        abort(404)
    return send_file(target, conditional=True)


def get_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'


if __name__ == '__main__':
    ip = get_lan_ip()
    print(f'\n  Woodshed -> http://{ip}:8000\n')
    app.run(host='0.0.0.0', port=8000, debug=False)
