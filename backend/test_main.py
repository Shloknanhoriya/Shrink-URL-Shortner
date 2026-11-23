import os
import tempfile

# Point the app at a throwaway DB before importing it
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)


def test_create_and_redirect():
    r = client.post("/api/links", json={"url": "https://example.com/a/long/path"})
    assert r.status_code == 201
    data = r.json()
    assert len(data["code"]) == 6

    redirect = client.get(f"/{data['code']}", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://example.com/a/long/path"


def test_click_counting():
    code = client.post("/api/links", json={"url": "https://example.com/clicks"}).json()["code"]
    for _ in range(3):
        client.get(f"/{code}", follow_redirects=False)
    assert client.get(f"/api/links/{code}").json()["clicks"] == 3


def test_custom_alias_and_conflict():
    r = client.post("/api/links", json={"url": "https://example.com", "alias": "my-link"})
    assert r.status_code == 201 and r.json()["code"] == "my-link"
    dup = client.post("/api/links", json={"url": "https://example.org", "alias": "my-link"})
    assert dup.status_code == 409


def test_rejects_bad_urls():
    for bad in ["not a url", "ftp://example.com", "javascript:alert(1)", "https://"]:
        assert client.post("/api/links", json={"url": bad}).status_code == 422


def test_rejects_bad_or_reserved_alias():
    assert client.post("/api/links", json={"url": "https://a.com", "alias": "x"}).status_code == 422
    assert client.post("/api/links", json={"url": "https://a.com", "alias": "api"}).status_code == 422
    assert client.post("/api/links", json={"url": "https://a.com", "alias": "bad alias!"}).status_code == 422


def test_unknown_code_404():
    assert client.get("/doesnotexist", follow_redirects=False).status_code == 404
