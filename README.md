# Drum Woodshed

A self-hosted drumless practice library. Strip drums from songs with Demucs, then jam along from a tablet at the kit via a local-network web player.

## Setup

```bash
pip install demucs flask
```

## Usage

### 1. Strip drums from songs

Drop audio files (MP3, WAV, FLAC) into `input/`, then run:

```bash
python3 separate.py
```

Drumless files land in `library/` as WAV. Each song takes a few minutes depending on hardware.

**Flags:**

| Flag | Description |
|------|-------------|
| `--mp3` | Output MP3 instead of WAV (smaller files, lighter on wifi) |
| `--model htdemucs` | Faster model (~4x), slightly lower quality |
| `--model htdemucs_ft` | Quality model (default) |
| `--force` | Reprocess files already in the library |
| `--device mps\|cuda\|cpu` | Override device (auto-detected: MPS on Apple Silicon, CUDA on Nvidia, else CPU) |

**Examples:**

```bash
# First pass — quality output
python3 separate.py

# Quick test run — fastest model
python3 separate.py --model htdemucs

# Redo everything as MP3
python3 separate.py --force --mp3
```

### 2. Start the player

```bash
python3 server.py
```

The terminal prints your LAN address, e.g. `Woodshed -> http://192.168.1.5:8000`. Open that on your phone or tablet at the kit.

## Player features

- Track list with real-time filter
- Play / pause, seek bar, time display
- Volume slider
- Loop toggle (replays current track or auto-advances to next)

## Notes

- Drum removal leaves faint cymbal bleed — acceptable for practice
- Drumless files also drag straight into a DAW for recording sessions
- The library is just a folder of audio files — no database

## Project structure

```
separate.py        # batch pipeline: input/ -> Demucs -> library/
server.py          # Flask player server, binds 0.0.0.0:8000
static/index.html  # single-file player UI (no build step)
input/             # drop source songs here (gitignored)
library/           # drumless output (gitignored)
```

## Running tests

```bash
pip install pytest
python3 -m pytest tests/ -v
```
