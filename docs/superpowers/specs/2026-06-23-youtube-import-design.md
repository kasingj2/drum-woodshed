# YouTube Import Feature — Design Spec

## Overview

Add a YouTube import flow to Woodshed: paste a URL, click Import, and a drumless WAV appears in the library automatically. The download and Demucs separation run in a background thread; the UI polls for status and updates without a page refresh.

---

## Architecture

Three components change:

| Component | Change |
|-----------|--------|
| `separate.py` | Add `clean_title(title: str) -> str` pure function |
| `server.py` | Add `INPUT_DIR`, job state dict, two new routes, background worker |
| `static/index.html` | Add "+ YouTube" header button, collapsible panel, status line, polling logic |

`requirements.txt` gains `yt-dlp`.

The source MP3 downloaded from YouTube is saved to `input/` and left there after processing — consistent with the existing drop-file workflow. The drumless output lands in `library/` as a WAV.

---

## `separate.py` — `clean_title()`

New pure function. Strips known YouTube noise from video titles using regex, preserving the core artist/song name.

**Stripped patterns** (case-insensitive, inside `()` or `[]`):
- `Official Video`, `Official Music Video`, `Official Audio`, `Official Lyric Video`
- `Lyrics`, `Lyric Video`, `Audio`
- `HD`, `HQ`, `4K`
- `Live`, `Live Performance`, `Live Version`
- `Visualizer`, `Animated Video`, `Music Video`, `MV`
- `Explicit`, `Clean Version`
- `Remastered`, `Remastered YYYY`, `YYYY Remaster`

**Preserved:** `feat.` / `ft.` / `featuring` content — this is part of the song name.

**Post-strip cleanup:** Collapse trailing separators (` - `, ` | `, ` — `), strip leading/trailing whitespace, collapse internal runs of whitespace to a single space.

**Examples:**
- `"Artist - Song Title (Official Video) [HD]"` → `"Artist - Song Title"`
- `"Song (feat. Someone) (Official Audio)"` → `"Song (feat. Someone)"`
- `"Song Title | Lyrics"` → `"Song Title"`

---

## `server.py` — New Constants and State

```python
import threading
import uuid
from separate import clean_title, process_file, is_processed, get_device

INPUT_DIR = Path('input')

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
```

Job dict entry shape: `{"status": str, "message": str}`

Valid status values: `"downloading"`, `"processing"`, `"done"`, `"error"`

Only one job is allowed to be active at a time. A second POST while a job is `downloading` or `processing` returns HTTP 409 with `{"error": "Already processing a track — please wait"}`.

---

## `server.py` — New Routes

### `POST /api/import`

**Request body:** `{"url": "<youtube-url>"}`

**Validation:**
- `url` must be present and non-empty → 400 if missing
- Must start with `https://www.youtube.com/`, `https://youtube.com/`, or `https://youtu.be/` → 400 if not a YouTube URL
- No active job running → 409 if busy

**On success:**
- Creates a new job entry in `_jobs` with status `"downloading"`
- Starts `_import_worker` in a daemon thread
- Returns `{"job_id": "<uuid>"}` with HTTP 202

### `GET /api/import/status/<job_id>`

Returns the job entry: `{"status": "...", "message": "..."}`.

Returns 404 if `job_id` is not in `_jobs`.

---

## `server.py` — Background Worker

```
_import_worker(job_id: str, url: str) -> None
```

Steps (each updates `_jobs[job_id]` under `_jobs_lock`):

1. **Get title** — `status: "downloading", message: "Getting track info..."` → call yt-dlp with `download=False` to fetch `info['title']` → run `clean_title()` on it
2. **Download** — `status: "downloading", message: "Downloading: {title}"` → yt-dlp downloads best audio as MP3 to `input/{title}.mp3` via FFmpegExtractAudio post-processor at 192kbps
3. **Skip check** — if `is_processed(source, LIBRARY_DIR)` is True, set `status: "done", message: "Already in library: {title}"` and return
4. **Separate** — `status: "processing", message: "Removing drums..."` → call `process_file(source, LIBRARY_DIR, 'htdemucs_ft', get_device(), mp3=False)`
5. **Done** — `status: "done", message: "Done: {title}"`

Any unhandled exception sets `status: "error", message: str(e)`.

---

## `static/index.html` — UI Changes

### Header

Add a `+ YouTube` button to the right of the filter input. Clicking it toggles a panel below the header. While the panel is open, the button label changes to `✕ Close`. While a job is active, the button stays visible as `✕ Close` but is greyed and pointer-events disabled — the user can see the panel is busy but cannot close it mid-import.

### YouTube Panel

Sits between the header and the track list. Hidden by default, shown when the button is toggled.

**Panel contents:**
- URL `<input>` (full width minus Import button)
- `Import` button

While a job is active: input and Import button are disabled/dimmed, the Close button is also disabled.

### Status Line

Appears below the URL row inside the panel while a job is running or has just completed/errored. Empty when no job is active.

| Status | Style | Text example |
|--------|-------|--------------|
| `downloading` | Grey text + grey spinner | `Downloading: Never Gonna Give You Up` |
| `processing` | Orange text + orange spinner | `Removing drums — Never Gonna Give You Up` |
| `done` | Green text, no spinner | `✓ Done: Never Gonna Give You Up` |
| `error` | Red text, no spinner | `Error: <message from server>` |

### Polling

When a job is active, the UI polls `GET /api/import/status/<job_id>` every 2 seconds.

- On `done`: stop polling → re-fetch `/api/tracks` to refresh the list → briefly highlight the new track green → auto-close the panel after 1.5 seconds
- On `error`: stop polling → leave panel open with red error text so the user can retry
- On `downloading` / `processing`: continue polling

### Track List Auto-Refresh

On job completion, call the existing `loadLibrary()` function. The new track appears at its sorted position. To identify it: snapshot the track list before re-fetching, diff against the new list after re-fetch, and apply a green highlight CSS class to any tracks that are new. Remove the class after 2 seconds.

---

## `requirements.txt`

Add `yt-dlp`.

---

## Testing

### `tests/test_separate.py` — `clean_title()` tests (5 new tests)

- Strips `(Official Video)` → bare title
- Strips `[HD]` and `[4K]` brackets
- Preserves `(feat. Artist)` content
- Strips trailing separator after bracket removal (e.g. `" - "` left over)
- Collapses internal whitespace

### `tests/test_server.py` — import route tests (5 new tests)

- `POST /api/import` with empty body → 400
- `POST /api/import` with non-YouTube URL → 400
- `POST /api/import` with valid YouTube URL → 202 + `job_id` (thread mocked to no-op)
- `GET /api/import/status/<unknown-id>` → 404
- `GET /api/import/status/<known-id>` → 200 with correct job state (job seeded directly into `_jobs`)

The background worker (`_import_worker`) is not unit tested — it shells out to yt-dlp and Demucs. The yt-dlp download is a thin wrapper; the Demucs half is covered by existing `process_file` tests.

---

## Out of Scope

- Queue of multiple imports (one at a time only)
- Progress percentage or time estimate
- Cancelling an in-progress import
- Playlist or batch YouTube import
- Choosing model or output format per import (always `htdemucs_ft`, always WAV)
