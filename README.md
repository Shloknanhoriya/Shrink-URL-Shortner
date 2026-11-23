# Shrink — URL Shortener

A small full-stack URL shortener: **FastAPI + SQLite** backend, **React + Vite** frontend.

## Features
- Shorten any `http(s)` URL to a 6-character code, or pick a custom alias
- Redirects (HTTP 307) with a click counter per link
- Input validation (scheme, length, alias format, reserved names, duplicates)
- UI keeps your recent links in the browser, with copy button and click refresh
- Light/dark theme following the system setting

## Project layout
```
url-shortener/
├── backend/
│   ├── main.py                    # API, redirects, serves built frontend
│   ├── test_main.py               # API tests
│   ├── test_frontend_serving.py   # UI-serving tests
│   ├── requirements.txt           # runtime dependencies (used by Docker)
│   └── requirements-dev.txt       # runtime + test dependencies
├── frontend/
│   ├── index.html
│   ├── vite.config.js             # dev proxy + test config
│   ├── package.json
│   └── src/
│       ├── main.jsx               # entry point
│       ├── App.jsx                # UI
│       ├── api.js                 # fetch wrapper
│       ├── styles.css
│       ├── setupTests.js
│       └── App.test.jsx           # UI tests
├── Dockerfile                     # multi-stage build: React build + Python runtime
├── .dockerignore
└── README.md
```

## Run it (single server, production style)
```bash
# 1. Build the frontend
cd frontend
npm install
npm run build

# 2. Start the backend (serves the built UI too)
cd ../backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8000
```
Open http://localhost:8000. API docs are at http://localhost:8000/docs.

## Run it (development, with hot reload)
Two terminals:
```bash
# Terminal 1: backend
cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000

# Terminal 2: frontend
cd frontend && npm run dev
```
Open http://localhost:5173. Vite proxies `/api` to the backend.

## Tests
```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest -q   # 8 backend tests
cd frontend && npm test               # 6 frontend tests
```

## API
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/links` | Body `{"url": "...", "alias": "optional"}` → 201 with the short link |
| GET | `/api/links/{code}` | Link details and click count |
| GET | `/{code}` | Redirects to the original URL |
| GET | `/health` | Health check |

## Configuration (environment variables)
| Variable | Default | Purpose |
|----------|---------|---------|
| `DB_PATH` | `backend/shortener.db` | SQLite file location |
| `BASE_URL` | request host | Public URL used in returned short links (set this when deployed behind a proxy/domain) |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated allowed origins |
| `FRONTEND_DIST` | `frontend/dist` | Built frontend folder |

## Deploy with Docker

The image builds the React app and serves it together with the API from one container.

```bash
# Build (run from the url-shortener/ folder)
docker build -t url-shortener .

# Run: data lives in the named volume "shortdata", mounted at /data
docker run -d --name shrink -p 8000:8000 \
  -v shortdata:/data \
  -e BASE_URL=https://short.yourdomain.com \
  url-shortener
```

- **`/data` is the persistent storage.** The SQLite file is `/data/shortener.db`. Always mount a volume there, otherwise links are lost when the container is replaced. Use a named volume (as above); with a bind mount, make the host folder writable by UID 1000 (`sudo chown 1000 ./data`).
- **`BASE_URL`** is the public address used in the short links you get back. Set it to your real domain; if omitted, the address of the incoming request is used (fine for local testing, wrong behind a proxy).
- **`PORT`** (default 8000) changes the listening port. Many hosts set it automatically.
- The container runs as a non-root user and has a built-in health check on `/health`.
- Put HTTPS in front of it (Caddy, nginx, or your host's built-in TLS).

### Hosting options
| Host | How |
|------|-----|
| **Fly.io** | `fly launch` (uses the Dockerfile), then `fly volumes create data` and mount it at `/data` in `fly.toml`; set `BASE_URL` with `fly secrets set`. |
| **Railway** | Deploy from the repo, add a Volume mounted at `/data`, set `BASE_URL` in Variables. |
| **VPS** (DigitalOcean, Hetzner, etc.) | Install Docker, run the commands above, and put Caddy in front for automatic HTTPS. |

SQLite supports a single server instance, so do not scale to multiple replicas. Free tiers with ephemeral disks will lose links on restart, so pick a host with a persistent volume.

### Backups
```bash
docker run --rm -v shortdata:/data -v "$PWD":/backup alpine cp /data/shortener.db /backup/
```

## Ideas for next steps
QR codes, link expiry, per-click analytics, rate limiting, user accounts, Docker deployment.
