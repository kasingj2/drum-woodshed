#!/usr/bin/env python3
import shutil
import subprocess
import sys
import argparse
from pathlib import Path

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.aiff'}
INPUT_DIR = Path('input')
LIBRARY_DIR = Path('library')
TMP_DIR = Path('.demucs_tmp')


def find_audio_files(input_dir: Path) -> list[Path]:
    """Return all audio files in input_dir with supported extensions."""
    return [p for p in input_dir.iterdir() if p.suffix.lower() in AUDIO_EXTENSIONS]


def output_path(source: Path, library_dir: Path, mp3: bool = False) -> Path:
    """Return the library destination path for a source file."""
    ext = '.mp3' if mp3 else '.wav'
    return library_dir / (source.stem + ext)


def is_processed(source: Path, library_dir: Path) -> bool:
    """Return True if a .wav or .mp3 version of source already exists in library_dir."""
    stem = source.stem
    return any((library_dir / (stem + ext)).exists() for ext in ('.wav', '.mp3'))


def get_device() -> str:
    try:
        import torch
        if torch.backends.mps.is_available():
            return 'mps'
        if torch.cuda.is_available():
            return 'cuda'
    except ImportError:
        pass
    return 'cpu'


def run_demucs(source: Path, model: str, device: str, mp3: bool) -> Path:
    TMP_DIR.mkdir(exist_ok=True)
    cmd = [
        sys.executable, '-m', 'demucs',
        '--two-stems=drums',
        f'--out={TMP_DIR}',
        '-n', model,
        f'--device={device}',
    ]
    if mp3:
        cmd.append('--mp3')
    cmd.append(str(source))

    subprocess.run(cmd, check=True)

    ext = '.mp3' if mp3 else '.wav'
    return TMP_DIR / model / source.stem / f'no_drums{ext}'


def process_file(source: Path, library_dir: Path, model: str, device: str, mp3: bool) -> None:
    print(f'Processing: {source.name}')
    try:
        tmp_out = run_demucs(source, model, device, mp3)
        dest = output_path(source, library_dir, mp3)
        shutil.move(str(tmp_out), dest)
        shutil.rmtree(TMP_DIR / model / source.stem, ignore_errors=True)
        print(f'  -> {dest.name}')
    except subprocess.CalledProcessError:
        print(f'  ERROR: demucs failed for {source.name}', file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description='Strip drums from audio files using Demucs')
    parser.add_argument('--mp3', action='store_true', help='Output MP3 instead of WAV')
    parser.add_argument('--model', default='htdemucs_ft', choices=['htdemucs_ft', 'htdemucs'],
                        help='Demucs model (default: htdemucs_ft for quality, htdemucs for speed)')
    parser.add_argument('--force', action='store_true', help='Reprocess already-processed files')
    parser.add_argument('--device', default=None,
                        help='Device override: mps, cuda, or cpu (auto-detected if omitted)')
    args = parser.parse_args()

    device = args.device or get_device()
    print(f'Device: {device}')

    INPUT_DIR.mkdir(exist_ok=True)
    LIBRARY_DIR.mkdir(exist_ok=True)

    sources = sorted(find_audio_files(INPUT_DIR))
    if not sources:
        print(f'No audio files found in {INPUT_DIR}/')
        return

    for source in sources:
        if not args.force and is_processed(source, LIBRARY_DIR):
            print(f'Skipping (already done): {source.name}')
            continue
        process_file(source, LIBRARY_DIR, args.model, device, args.mp3)


if __name__ == '__main__':
    main()
