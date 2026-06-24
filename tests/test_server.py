from pathlib import Path
import server as srv


def test_tracks_empty_library(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srv, 'LIBRARY_DIR', tmp_path)
    resp = client.get('/api/tracks')
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_tracks_lists_audio_files(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srv, 'LIBRARY_DIR', tmp_path)
    (tmp_path / 'b_song.wav').write_bytes(b'')
    (tmp_path / 'a_song.mp3').write_bytes(b'')
    (tmp_path / 'cover.jpg').write_bytes(b'')
    resp = client.get('/api/tracks')
    assert resp.get_json() == ['a_song.mp3', 'b_song.wav']


def test_tracks_returns_sorted(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srv, 'LIBRARY_DIR', tmp_path)
    for name in ['z.wav', 'm.wav', 'a.wav']:
        (tmp_path / name).write_bytes(b'')
    resp = client.get('/api/tracks')
    assert resp.get_json() == ['a.wav', 'm.wav', 'z.wav']


def test_tracks_missing_library(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srv, 'LIBRARY_DIR', tmp_path / 'nonexistent')
    resp = client.get('/api/tracks')
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_audio_traversal_blocked(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srv, 'LIBRARY_DIR', tmp_path)
    resp = client.get('/audio/../../etc/passwd')
    assert resp.status_code == 404


def test_audio_disallowed_extension_returns_404(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srv, 'LIBRARY_DIR', tmp_path)
    (tmp_path / 'malicious.php').write_bytes(b'<?php echo "bad"; ?>')
    resp = client.get('/audio/malicious.php')
    assert resp.status_code == 404


def test_audio_missing_file_returns_404(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srv, 'LIBRARY_DIR', tmp_path)
    resp = client.get('/audio/nonexistent.wav')
    assert resp.status_code == 404


def test_audio_valid_file_returns_200(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srv, 'LIBRARY_DIR', tmp_path)
    (tmp_path / 'song.wav').write_bytes(b'RIFF' + b'\x00' * 100)
    resp = client.get('/audio/song.wav')
    assert resp.status_code == 200


def test_audio_range_request_returns_206(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srv, 'LIBRARY_DIR', tmp_path)
    (tmp_path / 'song.wav').write_bytes(b'A' * 1000)
    resp = client.get('/audio/song.wav', headers={'Range': 'bytes=0-99'})
    assert resp.status_code == 206
    assert len(resp.data) == 100


def test_audio_range_mid_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srv, 'LIBRARY_DIR', tmp_path)
    data = bytes(range(256)) * 4  # 1024 bytes, predictable content
    (tmp_path / 'song.wav').write_bytes(data)
    resp = client.get('/audio/song.wav', headers={'Range': 'bytes=100-199'})
    assert resp.status_code == 206
    assert resp.data == data[100:200]
