# Stage 1: build the React app
FROM node:20-slim AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app serving the API and the built UI
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/data/shortener.db \
    PORT=8000

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/main.py backend/main.py
COPY --from=ui /ui/dist frontend/dist

# Run as a non-root user; /data holds the SQLite file and must be a volume
RUN useradd --system --uid 1000 app && mkdir /data && chown app:app /data
USER app

WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import os,urllib.request as u; u.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health')" || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
