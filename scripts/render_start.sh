#!/usr/bin/env bash
# Render production start — binds to $PORT immediately (DB setup runs in preDeploy).
set -euo pipefail

exec gunicorn \
  --worker-class gthread \
  --workers 1 \
  --threads 4 \
  --bind "0.0.0.0:${PORT:-5000}" \
  --timeout 120 \
  --graceful-timeout 30 \
  wsgi:app
