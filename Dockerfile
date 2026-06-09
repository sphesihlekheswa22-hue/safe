# SafeRoute AI - production image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg2 build (slim image).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 5000

# Entrypoint script creates tables, seeds (idempotent) then serves via gunicorn.
CMD ["sh", "-c", "python scripts/setup_db.py && gunicorn --bind 0.0.0.0:5000 --workers 3 wsgi:app"]
