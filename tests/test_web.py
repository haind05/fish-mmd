from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import pytest
from http.server import ThreadingHTTPServer
from fish_features import web


@pytest.fixture
def server(monkeypatch, tmp_path):
    monkeypatch.setattr(web, "overview", lambda: {"images": 1000})
    monkeypatch.setattr(web, "gallery", lambda query: {"q": query.get("q", [""])[0]})
    s = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
    s.images_root = tmp_path
    thread = threading.Thread(target=s.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{s.server_port}"
    s.shutdown()
    s.server_close()
    thread.join()


def test_http_serves_app_and_api(server):
    with urlopen(server+"/") as response:
        assert response.status == 200
        assert 'lang="vi"' in response.read().decode()
    with urlopen(server+"/api/overview") as response:
        assert json.load(response) == {"images": 1000}
    with urlopen(server+"/api/images?q=cheilinus") as response:
        assert json.load(response)["q"] == "cheilinus"


def test_unknown_route_and_bad_id(server):
    for path, status in [("/missing", 404), ("/api/images/invalid", 400)]:
        with pytest.raises(HTTPError) as error:
            urlopen(server+path)
        assert error.value.code == status


def test_image_paths_cannot_escape_dataset(tmp_path):
    root = tmp_path / "images"
    root.mkdir()
    (tmp_path / "outside.png").write_bytes(b"secret")
    with pytest.raises(FileNotFoundError):
        web.resolve_image(root, "../outside.png")
    (root / "fish.png").write_bytes(b"image")
    assert web.resolve_image(root, "fish.png") == root / "fish.png"


def test_database_unavailable_shows_recovery_message(server, monkeypatch):
    def fail():
        raise ConnectionError("private connection details")
    monkeypatch.setattr(web, "overview", fail)
    with pytest.raises(HTTPError) as error:
        urlopen(server+"/api/overview")
    assert error.value.code == 503
    data = json.load(error.value)
    assert "docker compose" in data["error"]
    assert "private connection" not in data["error"]


def test_search_upload_reaches_pipeline(server, monkeypatch):
    monkeypatch.setattr(web, "search_bytes", lambda raw, filename, flip, background: {"size": len(raw), "flip": flip, "filename": filename})
    with urlopen(Request(server+"/api/search?filename=fish.png&flip=1", data=b'pixels', method='POST')) as response:
        data = json.load(response)
        assert data == {"size": 6, "flip": True, "filename": "fish.png"}


def test_search_rejects_oversize_before_reading(server):
    request = Request(server+"/api/search", data=b'', headers={"Content-Length": str(web.MAX_UPLOAD+1)}, method='POST')
    with pytest.raises(HTTPError) as error:
        urlopen(request)
    assert error.value.code == 413


def test_search_rmbg_unavailable_returns_actionable_error(server, monkeypatch):
    def unavailable(*args, **kwargs):
        assert kwargs['background'] == 'rmbg2'
        raise web.BackgroundUnavailable('Dang nhap Hugging Face tren may')
    monkeypatch.setattr(web, 'search_bytes', unavailable)
    with pytest.raises(HTTPError) as error:
        urlopen(Request(server+'/api/search?background=rmbg2', data=b'image', method='POST'))
    assert error.value.code == 503
    assert json.load(error.value)['code'] == 'background_unavailable'


def test_dataset_query_never_runs_background_model(server, monkeypatch, tmp_path):
    import urllib.request
    # server fixture dung tmp_path lam images_root.
    (tmp_path/'fish.png').write_bytes(b'image')
    monkeypatch.setattr(web, 'detail', lambda image_id: {'image': {'relative_path':'fish.png'}})
    monkeypatch.setattr(web, 'search_bytes', lambda raw, filename, flip, background: {'background':background})
    with urlopen(Request(server+'/api/search?id=1&background=rmbg2', data=b'', method='POST')) as response:
        assert json.load(response)['background'] == 'none'
