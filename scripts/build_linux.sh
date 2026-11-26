#!/bin/bash
# Builds build_out/dist/SaveGarage (a folder with the SaveGarage executable) and SaveGarage-linux.tar.gz.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
PY="${PYTHON:-python3}"
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/pip install -q -r requirements.txt pyinstaller

.venv/bin/python -m PyInstaller "$ROOT/engine/main.py" --name SaveGarage --onedir --noconfirm --clean \
  --distpath build_out/dist --workpath build_out/work --specpath build_out \
  --paths "$ROOT/engine" \
  --add-data "$ROOT/vendor:vendor" --add-data "$ROOT/ui:ui" --add-data "$ROOT/engine/workers:engine/workers" \
  --add-data "$ROOT/LICENSE:." --add-data "$ROOT/CREDITS.md:." --add-data "$ROOT/README.md:." \
  --hidden-import app --hidden-import money --hidden-import garlic --hidden-import savedit --hidden-import statnames \
  --hidden-import bootstrap --hidden-import updater --hidden-import ed25519 --hidden-import tarfile --hidden-import secrets \
  --hidden-import sqlite3 --hidden-import ipaddress --hidden-import select --hidden-import uuid --hidden-import hashlib \
  --hidden-import tempfile --hidden-import argparse --hidden-import contextlib --hidden-import stat --hidden-import zipfile \
  --hidden-import runpy --hidden-import urllib.parse \
  --collect-all cryptography
tar -C build_out/dist -czf build_out/dist/SaveGarage-linux.tar.gz SaveGarage
echo "Built build_out/dist/SaveGarage"
