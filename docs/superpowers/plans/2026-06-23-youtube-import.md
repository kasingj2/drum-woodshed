# YouTube Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a YouTube import panel to the Woodshed player that downloads audio via yt-dlp, strips drums via Demucs, and adds the result to the library — all in the background without interrupting playback.

**Architecture:** A `clean_title()` pure function in `separate.py` strips YouTube noise from video titles. Two new Flask routes (`POST /api/import`, `GET /api/import/status/<id>`) drive a background thread that runs yt-dlp then Demucs, updating a module-level job dict at each stage. The UI polls every 2 seconds and auto-refreshes the track list on completion.

**Tech Stack:** Python (threading, uuid, re), yt-dlp, Flask, vanilla JS (fetch, setInterval)

---

## File Map

| File | Change |
|------|--------|
| `separate.py` | Add `import re`, two module-level regex constants, `clean_title()` function |
| `server.py` | Add `threading`, `uuid`, `request` imports; `from separate import ...`; `INPUT_DIR`, `_jobs`, `_jobs_lock`; `_import_worker()`; two new routes |
| `static/index.html` | Add CSS for panel + spinner + highlight; add HTML button + panel div; add JS panel toggle, import submit, polling, highlight logic |
| `requirements.txt` | Add `yt-dlp` |
| `tests/test_separate.py` | Add `clean_title` to import; 5 new `clean_title` tests |
| `tests/test_server.py` | Add `MagicMock` import; 6 new import route tests |

---

## Task 1: `clean_title()` in `separate.py`

**Files:**
- Modify: `separate.py` (add `import re` at line 4, add regex constants + function after `is_processed` at line 28)
- Modify: `tests/test_separate.py` (add `clean_title` to import line 5; append 5 tests)

- [ ] **Step 1: Add `clean_title` to the import in the test file**

In `tests/test_separate.py` line 5, change:
```python
from separate import find_audio_files, output_path, is_processed, get_device, run_demucs, process_file
```
to:
```python
from separate import find_audio_files, output_path, is_processed, get_device, run_demucs, process_file, clean_title
```

- [ ] **Step 2: Write 5 failing tests**

Append to `tests/test_separate.py`:
```python
def test_clean_title_strips_official_video():
    assert clean_title('Artist - Song (Official Video)') == 'Artist - Song'


def test_clean_title_strips_brackets():
    assert clean_title('Song Title [HD] [4K]') == 'Song Title'


def test_clean_title_preserves_feat():
    assert clean_title('Song (feat. Someone) (Official Audio)') == 'Song (feat. Someone)'


def test_clean_title_strips_trailing_separator():
    assert clean_title('Artist - Song (Official Video) - ') == 'Artist - Song'


def test_clean_title_collapses_whitespace():
    assert clean_title('Song   Title  (Lyrics)') == 'Song Title'
```

- [ ] **Step 3: Run tests, verify they fail**

```bash
python3 -m pytest tests/test_separate.py::test_clean_title_strips_official_video -v
```
Expected: `FAILED` with `ImportError: cannot import name 'clean_title'`

- [ ] **Step 4: Add `import re` to `separate.py`**

In `separate.py`, the current imports are:
```python
import shutil
import subprocess
import sys
import argparse
from pathlib import Path
```

Add `import re` after `import argparse`:
```python
import shutil
import subprocess
import sys
import argparse
import re
from pathlib import Path
```

- [ ] **Step 5: Add regex constants and `clean_title()` to `separate.py`**

After the `is_processed` function (after line 28, before `def get_device`), insert:
```python
_NOISE_RE = re.compile(
    r'\s*[\(\[]'
    r'(?:official\s+(?:music\s+)?(?:video|audio|lyric\s+video|visualizer|mv)|'
    r'lyrics?(?:\s+video)?|audio|hd|hq|4k|'
    r'live(?:\s+(?:performance|version))?|'
    r'music\s+video|mv|animated\s+video|visualizer|'
    r'explicit|clean(?:\s+version)?|'
    r'(?:\d{4}\s+)?remaster(?:ed)?(?:\s+\d{4})?)'
    r'[\)\]]\s*',
    re.IGNORECASE,
)
_TRAILING_SEP_RE = re.compile(r'[\s\-|—]+$')


def clean_title(title: str) -> str:
    """Strip YouTube noise from a video title, preserving artist/song name."""
    title = _NOISE_RE.sub('', title)
    title = _TRAILING_SEP_RE.sub('', title)
    return ' '.join(title.split())
```

- [ ] **Step 6: Run all 5 new tests, verify they pass**

```bash
python3 -m pytest tests/test_separate.py -k clean_title -v
```
Expected: 5 tests PASSED

- [ ] **Step 7: Run the full test suite to confirm nothing regressed**

```bash
python3 -m pytest tests/ -v
```
Expected: all tests PASSED (previously 23, now 28)

- [ ] **Step 8: Commit**

```bash
git add separate.py tests/test_separate.py
git commit -m "feat: add clean_title() to strip YouTube noise from video titles"
```

---

## Task 2: Server-side import routes and background worker

**Files:**
- Modify: `requirements.txt` (add `yt-dlp`)
- Modify: `server.py` (new imports, constants, worker, two routes)
- Modify: `tests/test_server.py` (add `MagicMock` import; 5 new tests)

- [ ] **Step 1: Add `yt-dlp` to `requirements.txt`**

Replace the contents of `requirements.txt` with:
```
demucs
flask
pytest
soundfile
yt-dlp
```

- [ ] **Step 2: Install the new dependency**

```bash
pip3 install yt-dlp
```
Expected: yt-dlp installs successfully

- [ ] **Step 3: Add `MagicMock` import to the test file**

In `tests/test_server.py`, add to the top imports block. Currently there is no `from unittest.mock` import. Add it after the existing imports:
```python
from pathlib import Path
import server as srv
from unittest.mock import MagicMock
```

- [ ] **Step 4: Write 6 failing tests**

Append to `tests/test_server.py` (before the existing `import re` block at the bottom):
```python
def test_import_missing_url_returns_400(client):
    r = client.post('/api/import', json={})
    assert r.status_code == 400


def test_import_non_youtube_url_returns_400(client):
    r = client.post('/api/import', json={'url': 'https://vimeo.com/123456'})
    assert r.status_code == 400


def test_import_valid_url_returns_202_with_job_id(client, monkeypatch):
    monkeypatch.setattr(srv, '_jobs', {})
    monkeypatch.setattr('server.threading.Thread', lambda *a, **kw: MagicMock())
    r = client.post('/api/import', json={'url': 'https://youtube.com/watch?v=abc123'})
    assert r.status_code == 202
    assert 'job_id' in r.get_json()


def test_import_busy_returns_409(client, monkeypatch):
    busy_job = {'status': 'downloading', 'message': 'Getting track info...'}
    monkeypatch.setattr(srv, '_jobs', {'existing-id': busy_job})
    r = client.post('/api/import', json={'url': 'https://youtube.com/watch?v=abc123'})
    assert r.status_code == 409


def test_import_status_unknown_id_returns_404(client, monkeypatch):
    monkeypatch.setattr(srv, '_jobs', {})
    r = client.get('/api/import/status/no-such-id')
    assert r.status_code == 404


def test_import_status_returns_job_state(client, monkeypatch):
    job = {'status': 'downloading', 'message': 'Getting track info...'}
    monkeypatch.setattr(srv, '_jobs', {'test-job-id': job})
    r = client.get('/api/import/status/test-job-id')
    assert r.status_code == 200
    assert r.get_json() == job
```

- [ ] **Step 5: Run tests, verify they fail**

```bash
python3 -m pytest tests/test_server.py::test_import_missing_url_returns_400 -v
```
Expected: `FAILED` with `405 METHOD NOT ALLOWED` or `404` (route doesn't exist yet)

- [ ] **Step 6: Replace the imports block in `server.py`**

The current top of `server.py` is:
```python
#!/usr/bin/env python3
import socket
from pathlib import Path
from flask import Flask, jsonify, send_file, abort
```

Replace with:
```python
#!/usr/bin/env python3
import socket
import threading
import uuid
from pathlib import Path
from flask import Flask, jsonify, send_file, abort, request
from separate import clean_title, process_file, is_processed, get_device
```

- [ ] **Step 7: Replace the constants block in `server.py`**

The current constants block (lines 6–7) is:
```python
LIBRARY_DIR = Path('library')
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac'}
```

Replace with:
```python
LIBRARY_DIR = Path('library')
INPUT_DIR = Path('input')
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac'}
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
```

- [ ] **Step 8: Add `_import_worker()` to `server.py`**

Insert this function after the constants block and before `app = Flask(...)`:
```python
def _import_worker(job_id: str, url: str) -> None:
    import yt_dlp

    def set_status(status: str, message: str) -> None:
        with _jobs_lock:
            _jobs[job_id] = {'status': status, 'message': message}

    try:
        set_status('downloading', 'Getting track info...')
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
        title = clean_title(info['title'])

        set_status('downloading', f'Downloading: {title}')
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(INPUT_DIR / f'{title}.%(ext)s'),
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
        set_status('done', f'Done: {title}')
    except Exception as e:
        set_status('error', str(e))
```

- [ ] **Step 9: Add two new routes to `server.py`**

Insert these two routes after the `audio()` route and before the `get_lan_ip()` function:
```python
@app.route('/api/import', methods=['POST'])
def import_track():
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    if not url:
        return jsonify({'error': 'url required'}), 400
    if not url.startswith(('https://www.youtube.com/', 'https://youtube.com/', 'https://youtu.be/')):
        return jsonify({'error': 'YouTube URLs only'}), 400

    with _jobs_lock:
        for job in _jobs.values():
            if job['status'] in ('downloading', 'processing'):
                return jsonify({'error': 'Already processing a track — please wait'}), 409

    job_id = str(uuid.uuid4())
    with _jobs_lock:
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
```

- [ ] **Step 10: Run all 6 new server tests, verify they pass**

```bash
python3 -m pytest tests/test_server.py -k import -v
```
Expected: 6 tests PASSED

- [ ] **Step 11: Run the full test suite to confirm nothing regressed**

```bash
python3 -m pytest tests/ -v
```
Expected: all tests PASSED (previously 28, now 34)

- [ ] **Step 12: Commit**

```bash
git add requirements.txt server.py tests/test_server.py
git commit -m "feat: add YouTube import routes and background worker"
```

---

## Task 3: UI — YouTube import panel

**Files:**
- Modify: `static/index.html` (CSS, HTML, JS)

There are no automated tests for the UI. Verification is manual (described at the end of this task).

- [ ] **Step 1: Add CSS for the YouTube panel**

In `static/index.html`, find the closing `</style>` tag (currently at line 241). Insert the following CSS block immediately before `</style>`:

```css
    /* ── YouTube Import Panel ── */
    #yt-toggle {
      background: none;
      border: 1px solid var(--accent);
      border-radius: var(--radius);
      color: var(--accent);
      font-size: 0.8rem;
      padding: 7px 12px;
      cursor: pointer;
      white-space: nowrap;
      letter-spacing: 0.03em;
      flex-shrink: 0;
    }

    #yt-toggle:disabled {
      border-color: var(--muted);
      color: var(--muted);
      cursor: default;
    }

    #yt-panel {
      display: none;
      padding: 10px 16px;
      border-bottom: 1px solid var(--border);
      background: #161616;
      flex-shrink: 0;
    }

    .yt-row {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    #yt-url {
      flex: 1;
      background: var(--surface);
      border: 1px solid var(--accent);
      border-radius: var(--radius);
      color: var(--text);
      font-size: 0.9rem;
      padding: 8px 12px;
      outline: none;
    }

    #yt-url:disabled { border-color: var(--border); color: var(--muted); }
    #yt-url::placeholder { color: var(--muted); }

    #yt-import-btn {
      background: var(--accent);
      border: none;
      border-radius: var(--radius);
      color: #fff;
      font-size: 0.9rem;
      padding: 8px 14px;
      cursor: pointer;
      white-space: nowrap;
      flex-shrink: 0;
    }

    #yt-import-btn:disabled { background: var(--muted); cursor: default; }

    #yt-status {
      font-size: 0.8rem;
      margin-top: 8px;
      min-height: 1.2em;
    }

    #yt-status.downloading { color: var(--muted); }
    #yt-status.processing  { color: var(--accent); }
    #yt-status.done        { color: #5aad5a; }
    #yt-status.error       { color: #cc4444; }

    @keyframes spin { to { transform: rotate(360deg); } }

    .spinner {
      display: inline-block;
      width: 10px;
      height: 10px;
      border: 1.5px solid currentColor;
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-right: 5px;
      vertical-align: middle;
    }

    .track.new-track {
      border-left: 3px solid #5aad5a;
      padding-left: 13px;
    }

    .track.new-track .track-name { color: #5aad5a; }
```

- [ ] **Step 2: Add the `#yt-toggle` button to the header HTML**

Find the `<header>` block (currently lines 245–248):
```html
<header>
  <h1>Woodshed</h1>
  <input type="search" id="filter" placeholder="Filter tracks..." autocomplete="off">
</header>
```

Replace with:
```html
<header>
  <h1>Woodshed</h1>
  <input type="search" id="filter" placeholder="Filter tracks..." autocomplete="off">
  <button id="yt-toggle">+ YouTube</button>
</header>

<div id="yt-panel">
  <div class="yt-row">
    <input type="url" id="yt-url" placeholder="https://youtube.com/watch?v=...">
    <button id="yt-import-btn">Import</button>
  </div>
  <div id="yt-status"></div>
</div>
```

The `#yt-panel` div must sit between `</header>` and `<main id="tracklist">` so it is part of the flex column and pushes the track list down when visible.

- [ ] **Step 3: Add JS for the YouTube import panel**

In the `<script>` block, find the line `loadLibrary();` near the bottom (currently the last statement before `</script>`). Insert the following block immediately before `loadLibrary();`:

```javascript
  // ── YouTube import ──
  const ytToggle = document.getElementById('yt-toggle');
  const ytPanel = document.getElementById('yt-panel');
  const ytUrl = document.getElementById('yt-url');
  const ytImportBtn = document.getElementById('yt-import-btn');
  const ytStatus = document.getElementById('yt-status');

  let ytPanelOpen = false;
  let ytPollInterval = null;
  let ytCurrentJobId = null;

  function setYtPanelOpen(open) {
    ytPanelOpen = open;
    ytPanel.style.display = open ? 'block' : 'none';
    ytToggle.textContent = open ? '✕ Close' : '+ YouTube';
  }

  function setYtBusy(busy) {
    ytToggle.disabled = busy;
    ytUrl.disabled = busy;
    ytImportBtn.disabled = busy;
  }

  function setYtStatus(cls, html) {
    ytStatus.className = cls;
    ytStatus.innerHTML = html;
  }

  ytToggle.addEventListener('click', () => {
    if (ytToggle.disabled) return;
    setYtPanelOpen(!ytPanelOpen);
    if (!ytPanelOpen) {
      ytUrl.value = '';
      setYtStatus('', '');
    }
  });

  ytImportBtn.addEventListener('click', async () => {
    const url = ytUrl.value.trim();
    if (!url) return;

    setYtBusy(true);
    setYtStatus('downloading', '<span class="spinner"></span>Getting track info...');

    try {
      const resp = await fetch('/api/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setYtStatus('error', data.error || 'Import failed');
        setYtBusy(false);
        return;
      }
      ytCurrentJobId = data.job_id;
      ytPollInterval = setInterval(pollYtStatus, 2000);
    } catch {
      setYtStatus('error', 'Network error');
      setYtBusy(false);
    }
  });

  async function pollYtStatus() {
    if (!ytCurrentJobId) return;
    try {
      const resp = await fetch(`/api/import/status/${ytCurrentJobId}`);
      if (!resp.ok) return;
      const { status, message } = await resp.json();

      if (status === 'downloading') {
        setYtStatus('downloading', `<span class="spinner"></span>${message}`);
      } else if (status === 'processing') {
        setYtStatus('processing', `<span class="spinner"></span>${message}`);
      } else if (status === 'done') {
        clearInterval(ytPollInterval);
        ytPollInterval = null;
        ytCurrentJobId = null;
        setYtStatus('done', `✓ ${message}`);
        setYtBusy(false);
        const prevTracks = [...tracks];
        await loadLibrary();
        highlightNewTracks(prevTracks);
        setTimeout(() => {
          setYtPanelOpen(false);
          ytUrl.value = '';
          setYtStatus('', '');
        }, 1500);
      } else if (status === 'error') {
        clearInterval(ytPollInterval);
        ytPollInterval = null;
        ytCurrentJobId = null;
        setYtStatus('error', `Error: ${message}`);
        setYtBusy(false);
      }
    } catch {
      // network blip — keep polling
    }
  }

  function highlightNewTracks(prevTracks) {
    const prevSet = new Set(prevTracks);
    document.querySelectorAll('.track').forEach(el => {
      const idx = parseInt(el.dataset.index, 10);
      const filename = tracks[idx];
      if (filename && !prevSet.has(filename)) {
        el.classList.add('new-track');
        setTimeout(() => el.classList.remove('new-track'), 2000);
      }
    });
  }
```

- [ ] **Step 4: Start the server and verify manually**

```bash
python3 server.py
```

Open the URL shown (e.g. `http://192.168.x.x:8000`) in a browser and verify:

1. **Panel toggle:** `+ YouTube` button appears in the header. Clicking it reveals the panel with URL input and Import button. Clicking `✕ Close` hides it and clears the input.
2. **Bad URL rejected:** Paste `https://vimeo.com/abc` and click Import → red error text appears instantly, panel stays open.
3. **Real import (if desired):** Paste a valid YouTube URL, click Import. Status progresses through grey "Getting track info..." → grey "Downloading: {title}" → orange "Removing drums..." → green "✓ Done: {title}". Panel closes after 1.5 s. New track appears (briefly green) in the list.
4. **Playback uninterrupted:** A track playing before and during the import continues playing normally.

- [ ] **Step 5: Update CLAUDE.md**

In `CLAUDE.md`, update the **File map** table to add the two new routes:

Find:
```
| `server.py` | Flask app: `GET /` (UI), `GET /api/tracks` (JSON list), `GET /audio/<f>` (streaming with range support + path traversal protection) |
```

Replace with:
```
| `server.py` | Flask app: `GET /` (UI), `GET /api/tracks` (JSON list), `GET /audio/<f>` (streaming with range support + path traversal protection), `POST /api/import` (start YouTube import job), `GET /api/import/status/<id>` (poll job status) |
```

Also update the test count in the **Running things** section:

Find:
```
python3 -m pytest tests/ -v  # run 23 tests
```

Replace with:
```
python3 -m pytest tests/ -v  # run 34 tests
```

- [ ] **Step 6: Commit**

```bash
git add static/index.html CLAUDE.md
git commit -m "feat: add YouTube import panel with background polling"
```
