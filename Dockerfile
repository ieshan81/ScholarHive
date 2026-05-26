FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Node.js for Vite frontend build (image ships Python + Playwright browsers)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Backend Python dependencies (browsers already in base image)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip \
    && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 pip install -r /app/backend/requirements.txt

# Frontend build (layer cache)
COPY frontend/package.json frontend/package-lock.json /app/frontend/
WORKDIR /app/frontend
RUN npm ci
COPY frontend/ /app/frontend/
RUN npm run build

# Application source (backend/app/main.py resolves ../frontend/dist from repo root)
WORKDIR /app
COPY backend/ /app/backend/

# Railway volume mount targets for uploads and portal agent artifacts
RUN mkdir -p /data/uploads /data/portal-sessions /data/portal-screenshots /data/portal-artifacts

WORKDIR /app/backend

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
