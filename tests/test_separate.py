from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess
import pytest
from separate import find_audio_files, output_path, is_processed, get_device, run_demucs, process_file


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


def test_get_device_returns_string():
    device = get_device()
    assert device in ('mps', 'cuda', 'cpu')


def test_run_demucs_builds_correct_command(tmp_path):
    source = tmp_path / 'song.mp3'
    source.write_bytes(b'')

    # Fake the no_drums output that demucs would create
    fake_out = tmp_path / '.demucs_tmp' / 'htdemucs_ft' / 'song' / 'no_drums.wav'
    fake_out.parent.mkdir(parents=True)
    fake_out.write_bytes(b'audio')

    with patch('separate.TMP_DIR', tmp_path / '.demucs_tmp'), \
         patch('separate.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = run_demucs(source, model='htdemucs_ft', device='cpu', mp3=False)

    cmd = mock_run.call_args[0][0]
    assert '--two-stems=drums' in cmd
    assert '-n' in cmd
    assert 'htdemucs_ft' in cmd
    assert '--device=cpu' in cmd
    assert str(source) in cmd
    assert result == fake_out


def test_run_demucs_passes_mp3_flag(tmp_path):
    source = tmp_path / 'song.mp3'
    source.write_bytes(b'')

    fake_out = tmp_path / '.demucs_tmp' / 'htdemucs_ft' / 'song' / 'no_drums.mp3'
    fake_out.parent.mkdir(parents=True)
    fake_out.write_bytes(b'audio')

    with patch('separate.TMP_DIR', tmp_path / '.demucs_tmp'), \
         patch('separate.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = run_demucs(source, model='htdemucs_ft', device='cpu', mp3=True)

    cmd = mock_run.call_args[0][0]
    assert '--mp3' in cmd
    assert result == fake_out


def test_process_file_moves_output_to_library(tmp_path):
    source = tmp_path / 'input' / 'song.mp3'
    source.parent.mkdir()
    source.write_bytes(b'')
    lib = tmp_path / 'library'
    lib.mkdir()

    fake_out = tmp_path / '.demucs_tmp' / 'htdemucs_ft' / 'song' / 'no_drums.wav'
    fake_out.parent.mkdir(parents=True)
    fake_out.write_bytes(b'drumless audio')

    with patch('separate.TMP_DIR', tmp_path / '.demucs_tmp'), \
         patch('separate.run_demucs', return_value=fake_out):
        process_file(source, lib, model='htdemucs_ft', device='cpu', mp3=False)

    assert (lib / 'song.wav').exists()
    assert (lib / 'song.wav').read_bytes() == b'drumless audio'
