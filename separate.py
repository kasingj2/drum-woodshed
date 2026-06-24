#!/usr/bin/env python3
from pathlib import Path

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.aiff'}


def find_audio_files(input_dir: Path) -> list[Path]:
    """Return list of audio files (mp3, wav, flac, m4a, aiff) in input_dir."""
    return [p for p in input_dir.iterdir() if p.suffix.lower() in AUDIO_EXTENSIONS]


def output_path(source: Path, library_dir: Path, mp3: bool = False) -> Path:
    """Return the output path for a source audio file.

    Args:
        source: Path to input audio file
        library_dir: Path to output library directory
        mp3: If True, output as .mp3; otherwise output as .wav

    Returns:
        Path object for the output file
    """
    ext = '.mp3' if mp3 else '.wav'
    return library_dir / (source.stem + ext)


def is_processed(source: Path, library_dir: Path) -> bool:
    """Check if a source audio file has already been processed.

    Considers the file processed if either a .wav or .mp3 version exists
    in the library directory with the same stem.

    Args:
        source: Path to source audio file
        library_dir: Path to library directory

    Returns:
        True if either .wav or .mp3 version exists, False otherwise
    """
    stem = source.stem
    return any((library_dir / (stem + ext)).exists() for ext in ('.wav', '.mp3'))
