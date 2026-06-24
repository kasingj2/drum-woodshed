from pathlib import Path
import pytest
from separate import find_audio_files, output_path, is_processed


def test_find_audio_files_returns_supported_formats(tmp_path):
    (tmp_path / 'song.mp3').write_bytes(b'')
    (tmp_path / 'track.wav').write_bytes(b'')
    (tmp_path / 'album.flac').write_bytes(b'')
    (tmp_path / 'cover.jpg').write_bytes(b'')
    (tmp_path / 'notes.txt').write_bytes(b'')
    result = find_audio_files(tmp_path)
    assert set(result) == {
        tmp_path / 'song.mp3',
        tmp_path / 'track.wav',
        tmp_path / 'album.flac',
    }


def test_find_audio_files_empty_dir(tmp_path):
    assert find_audio_files(tmp_path) == []


def test_output_path_wav(tmp_path):
    source = tmp_path / 'input' / 'my song.mp3'
    lib = tmp_path / 'library'
    assert output_path(source, lib, mp3=False) == lib / 'my song.wav'


def test_output_path_mp3(tmp_path):
    source = tmp_path / 'input' / 'my song.flac'
    lib = tmp_path / 'library'
    assert output_path(source, lib, mp3=True) == lib / 'my song.mp3'


def test_output_path_preserves_stem_with_spaces(tmp_path):
    source = tmp_path / 'Led Zeppelin - Rock and Roll.mp3'
    lib = tmp_path / 'library'
    assert output_path(source, lib, mp3=False) == lib / 'Led Zeppelin - Rock and Roll.wav'


def test_is_processed_false_when_missing(tmp_path):
    lib = tmp_path / 'library'
    lib.mkdir()
    source = tmp_path / 'song.mp3'
    assert is_processed(source, lib) is False


def test_is_processed_true_for_wav(tmp_path):
    lib = tmp_path / 'library'
    lib.mkdir()
    (lib / 'song.wav').write_bytes(b'')
    source = tmp_path / 'song.mp3'
    assert is_processed(source, lib) is True


def test_is_processed_true_for_mp3(tmp_path):
    lib = tmp_path / 'library'
    lib.mkdir()
    (lib / 'song.mp3').write_bytes(b'')
    source = tmp_path / 'song.flac'
    assert is_processed(source, lib) is True
