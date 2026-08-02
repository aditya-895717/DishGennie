#!/bin/bash
# Optional build helper — produces staticfiles/ for hosts that have a build
# step (Render, local, CI).
#
# Vercel does NOT use this. There, static assets are served by WhiteNoise
# straight out of the committed static/ directory via WHITENOISE_USE_FINDERS,
# so the deployment needs no build step and cannot be broken by one failing.
set -e

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

echo ">>> Installing Python dependencies..."
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt

echo ">>> Collecting static files..."
"$PY" manage.py collectstatic --noinput --clear

echo ">>> Build complete!"
