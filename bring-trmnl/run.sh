#!/usr/bin/env bash
set -e

# Seed /data/config.json from HA options on first run
if [ ! -f /data/config.json ]; then
    echo "[INFO] Seeding config from Home Assistant options..."
    python3 /app/seed_config.py
fi

echo "[INFO] Starting Bring! → TRMNL web interface on port 8099..."
python3 -m waitress \
    --host=0.0.0.0 \
    --port=8099 \
    --threads=2 \
    --connection-limit=10 \
    --channel-timeout=60 \
    web:app &

echo "[INFO] Starting Bring! → TRMNL daemon..."
exec python3 /app/main.py
