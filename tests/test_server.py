import re
from pathlib import Path
import server as srv
from server import get_lan_ip
from unittest.mock import MagicMock


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


def test_get_lan_ip_returns_ip_string():
    ip = get_lan_ip()
    # Should be a dotted-quad IP like 192.168.1.5 or 127.0.0.1
    assert re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip)
