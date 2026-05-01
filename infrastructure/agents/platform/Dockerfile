FROM python:3.14-slim

# Base deps + Chromium runtime libs (pour Playwright headless) +
# docker.io CLI (pour OSINT orchestrator qui spawn maigret/holehe via
# subprocess — socket monté côté compose, mais besoin du binaire client).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git \
    docker.io \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libxkbcommon0 \
    libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 \
    fonts-liberation fonts-noto-cjk fonts-noto-color-emoji && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Télécharger Chromium pour Playwright (~150 MB dans /ms-playwright)
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install chromium

COPY . .

# Prompts montés en volume (pour update sans rebuild)
ENV PROMPTS_DIR=/app/prompts
ENV DOCS_DIR=/app/docs

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsSL http://127.0.0.1:8100/healthz || exit 1

EXPOSE 8100
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "2"]
