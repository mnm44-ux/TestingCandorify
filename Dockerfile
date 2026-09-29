# Candorify — backend API + static website in one container.
#
# The FastAPI app (backend/app/main.py) serves the JSON API under /api and
# mounts the static website from ../../frontend, so the image keeps the repo
# layout: /app/backend and /app/frontend side by side.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install backend dependencies first for better layer caching.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --upgrade pip && pip install -r backend/requirements.txt

# Copy application code (backend + the static frontend it serves).
COPY backend/ backend/
COPY frontend/ frontend/

# Run as a non-root user.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/backend

EXPOSE 8000

# Render (and most hosts) provide $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
