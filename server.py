#!/usr/bin/env python3.12
import re
import socket
import threading
import uuid
from pathlib import Path
from flask import Flask, jsonify, send_file, abort, request
from separate import clean_title, process_file, is_processed, get_device

LIBRARY_DIR = Path('library')
INPUT_DIR = Path('input')
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac'}
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

def _import_worker(job_id: str, url: str) -> None:
    import yt_dlp

    def set_status(status: str, message: str) -> None:
        with _jobs_lock:
            _jobs[job_id] = {'status': status, 'message': message}

    try:
        INPUT_DIR.mkdir(exist_ok=True)
        set_status('downloading', 'Getting track info...')
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            info = ydl.extract_info(url, download=False)
        title = clean_title(info['title']) or re.sub(r'[<>:"/\\|?*]', '_', info['title'])[:60]

        set_status('downloading', f'Downloading: {title}')
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(INPUT_DIR / f'{title}.%(ext)s'),
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        source = INPUT_DIR / f'{title}.mp3'
        if not source.exists():
            raise FileNotFoundError(f'Downloaded file not found: {source}')

        if is_processed(source, LIBRARY_DIR):
            set_status('done', f'Already in library: {title}')
            return

        set_status('processing', 'Removing drums...')
        process_file(source, LIBRARY_DIR, 'htdemucs_ft', get_device(), mp3=False)
        if not is_processed(source, LIBRARY_DIR):
            raise RuntimeError(f'Demucs processing failed for: {title}')
        set_status('done', f'Done: {title}')
    except Exception as e:
        set_status('error', str(e))


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


@app.route('/api/import', methods=['POST'])
def import_track():
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    if not url:
        return jsonify({'error': 'url required'}), 400
    if not url.startswith(('https://www.youtube.com/', 'https://youtube.com/',
                            'https://youtu.be/', 'https://music.youtube.com/')):
        return jsonify({'error': 'YouTube URLs only'}), 400

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        for job in _jobs.values():
            if job['status'] in ('downloading', 'processing'):
                return jsonify({'error': 'Already processing a track — please wait'}), 409
        _jobs[job_id] = {'status': 'downloading', 'message': 'Getting track info...'}

    thread = threading.Thread(target=_import_worker, args=(job_id, url), daemon=True)
    thread.start()
    return jsonify({'job_id': job_id}), 202


@app.route('/api/import/status/<job_id>')
def import_status(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        abort(404)
    return jsonify(job)


def get_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'


if __name__ == '__main__':
    ip = get_lan_ip()
    print(f'\n  Woodshed -> http://{ip}:8080\n')
    app.run(host='0.0.0.0', port=8080, debug=False)
