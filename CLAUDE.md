# Woodshed — Claude context

Self-hosted drumless practice library. Two parts: a batch pipeline that strips drums from songs using Demucs, and a local-network web player to jam along from a tablet at the kit.

## Stack

- Python 3.10+ · Demucs (stem separation) · Flask · vanilla HTML/CSS/JS
- No database — the filesystem is the library
- `input/` and `library/` are gitignored

## Running things

```bash
pip install demucs flask pytest

python3 separate.py          # strip drums from input/ -> library/
python3 separate.py --help   # show all flags
python3 server.py            # start player at http://<lan-ip>:8000
python3 -m pytest tests/ -v  # run 28 tests
```

## File map

| File | Responsibility |
|------|---------------|
| `separate.py` | Batch pipeline: find audio in `input/`, run Demucs `--two-stems=drums`, move `no_drums.wav` to `library/` |
| `server.py` | Flask app: `GET /` (UI), `GET /api/tracks` (JSON list), `GET /audio/<f>` (streaming with range support + path traversal protection) |
| `static/index.html` | Single self-contained player — all CSS/JS inline, no build step |
| `tests/test_separate.py` | 17 unit tests for separate.py pure functions and subprocess logic |
| `tests/test_server.py` | 11 tests for Flask routes (tracks, audio, security, range) |
| `tests/conftest.py` | Flask test client fixture |

## Key design decisions (keep unless asked)

- **Two-stem only.** Demucs `--two-stems=drums` outputs `drums.wav` and `no_drums.wav`. We keep only `no_drums.wav`. No per-stem mixer.
- **Offline preprocessing.** Separation runs once, output is cached in `library/`. The player just streams.
- **No tempo/pitch change.** That's for the DAW. This tool is for fast jamming.
- **Single `<audio>` element.** Flask `/audio` already returns HTTP 206 for range requests — seeking works on mobile without extra work.
- **Path traversal protection on `/audio`.** Resolves both base and target path, uses `relative_to()` to block directory escape. Extension whitelist (`.wav .mp3 .flac`) enforced before serving.

## separate.py flags

| Flag | Default | Notes |
|------|---------|-------|
| `--model` | `htdemucs_ft` | `htdemucs` is ~4x faster, slightly lower quality |
| `--mp3` | off | Output MP3 instead of WAV |
| `--force` | off | Reprocess files already in library |
| `--device` | auto | Auto-detects: MPS (Apple Silicon) > CUDA > CPU |

## Demucs output structure

Demucs writes to `.demucs_tmp/<model>/<song_stem>/no_drums.{wav,mp3}`. `separate.py` moves that file to `library/<song_stem>.{wav,mp3}` and cleans up the temp dir.

## Testing notes

- `LIBRARY_DIR` in `server.py` is a module-level `Path` — tests monkeypatch it with `tmp_path`
- Subprocess calls in `separate.py` are mocked via `unittest.mock.patch`
- No integration tests that call real Demucs (too slow, requires audio files)
- `python3 -m pytest` not `pytest` — system Python path may not include the pytest binary directly

## Candidate next steps (not yet built)

- Count-in click (1–2 bars) before playback
- A/B loop points for drilling a section
- Persist volume/loop/last-played via localStorage
- Drag-and-drop upload in UI + server-side separation trigger with progress
- Tempo display / tap-tempo readout
