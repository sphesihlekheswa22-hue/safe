#!/usr/bin/env bash
# Minimal container-based deploy helper.
set -e

cd "$(dirname "$0")/.."

echo "Building and starting containers..."
docker compose up --build -d

echo "Waiting for web service..."
sleep 5
docker compose ps

echo "SafeRoute AI is running at http://localhost:5000"
