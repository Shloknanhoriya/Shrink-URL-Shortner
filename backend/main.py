"""URL shortener backend: FastAPI + SQLite (stdlib sqlite3, no ORM)."""

import os
import re
import secrets
import sqlite3
import string
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "shortener.db"))
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", BASE_DIR.parent / "frontend" / "dist"))
CODE_LENGTH = 6
ALPHABET = string.ascii_letters + string.digits
ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
RESERVED = {"api", "docs", "redoc", "openapi.json", "health", "static", "assets", "admin"}
MAX_URL_LENGTH = 2048

app = FastAPI(title="URL Shortener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------- database ----------

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                code        TEXT PRIMARY KEY,
                url         TEXT NOT NULL,
                clicks      INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL
            )
            """
        )


init_db()


# ---------- helpers ----------

def generate_code(conn: sqlite3.Connection) -> str:
    for _ in range(10):
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        if not conn.execute("SELECT 1 FROM links WHERE code = ?", (code,)).fetchone():
            return code
    raise HTTPException(500, "Could not generate a unique code, try again")


def validate_url(raw: str) -> str:
    raw = raw.strip()
    if len(raw) > MAX_URL_LENGTH:
        raise HTTPException(422, f"URL too long (max {MAX_URL_LENGTH} characters)")
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(422, "URL must start with http:// or https:// and include a host")
    return raw


def base_url(request: Request) -> str:
    return os.getenv("BASE_URL", str(request.base_url)).rstrip("/")


# ---------- schemas ----------

class CreateLink(BaseModel):
    url: str = Field(..., examples=["https://example.com/some/very/long/path"])
    alias: str | None = Field(None, description="Optional custom short code")


class LinkOut(BaseModel):
    code: str
    short_url: str
    original_url: str
    clicks: int
    created_at: str


# ---------- frontend (served only if it has been built) ----------
# Registered before the /{code} catch-all so "/" and "/assets/*" are not
# mistaken for short codes.

if (FRONTEND_DIST / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(FRONTEND_DIST / "index.html")


# ---------- routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/links", response_model=LinkOut, status_code=201)
def create_link(body: CreateLink, request: Request):
    url = validate_url(body.url)
    now = datetime.now(timezone.utc).isoformat()

    with db() as conn:
        if body.alias:
            code = body.alias
            if not ALIAS_RE.match(code):
                raise HTTPException(422, "Alias must be 3-32 chars: letters, digits, _ or -")
            if code.lower() in RESERVED:
                raise HTTPException(422, "That alias is reserved")
            if conn.execute("SELECT 1 FROM links WHERE code = ?", (code,)).fetchone():
                raise HTTPException(409, "That alias is already taken")
        else:
            code = generate_code(conn)

        conn.execute(
            "INSERT INTO links (code, url, clicks, created_at) VALUES (?, ?, 0, ?)",
            (code, url, now),
        )

    return LinkOut(
        code=code,
        short_url=f"{base_url(request)}/{code}",
        original_url=url,
        clicks=0,
        created_at=now,
    )


@app.get("/api/links/{code}", response_model=LinkOut)
def link_stats(code: str, request: Request):
    with db() as conn:
        row = conn.execute("SELECT * FROM links WHERE code = ?", (code,)).fetchone()
    if not row:
        raise HTTPException(404, "Link not found")
    return LinkOut(
        code=row["code"],
        short_url=f"{base_url(request)}/{row['code']}",
        original_url=row["url"],
        clicks=row["clicks"],
        created_at=row["created_at"],
    )


@app.get("/{code}")
def redirect(code: str):
    with db() as conn:
        row = conn.execute("SELECT url FROM links WHERE code = ?", (code,)).fetchone()
        if not row:
            raise HTTPException(404, "Link not found")
        conn.execute("UPDATE links SET clicks = clicks + 1 WHERE code = ?", (code,))
    # 307 keeps the redirect non-cacheable so every click is counted
    return RedirectResponse(row["url"], status_code=307)
