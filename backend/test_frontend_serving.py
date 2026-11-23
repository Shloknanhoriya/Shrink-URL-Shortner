"""Checks that a built frontend is served without clashing with short codes."""

import importlib
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


def make_app(dist: Path):
    os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
    os.environ["FRONTEND_DIST"] = str(dist)
    import main

    importlib.reload(main)
    return main.app


def test_serves_built_frontend_and_still_redirects():
    dist = Path(tempfile.mkdtemp())
    (dist / "assets").mkdir()
    (dist / "index.html").write_text("<html>shrink-ui</html>")
    (dist / "assets" / "app.js").write_text("console.log('hi')")

    client = TestClient(make_app(dist))

    assert "shrink-ui" in client.get("/").text
    assert client.get("/assets/app.js").status_code == 200

    # short links keep working alongside the UI
    code = client.post("/api/links", json={"url": "https://example.com/x"}).json()["code"]
    r = client.get(f"/{code}", follow_redirects=False)
    assert r.status_code == 307

    # "assets" can't be claimed as an alias
    bad = client.post("/api/links", json={"url": "https://a.com", "alias": "assets"})
    assert bad.status_code == 422


def test_works_without_a_built_frontend():
    client = TestClient(make_app(Path(tempfile.mkdtemp()) / "missing"))
    assert client.get("/health").json() == {"status": "ok"}
