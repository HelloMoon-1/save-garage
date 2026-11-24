#!/bin/bash
# Builds build_out/dist/SaveGarage.app and build_out/dist/SaveGarage-macos.zip for the CPU of the Mac that runs it.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
PY="${PYTHON:-python3}"
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/pip install -q -r requirements.txt pyinstaller

.venv/bin/python -m PyInstaller "$ROOT/engine/main.py" --name SaveGarage --windowed --onedir --noconfirm --clean \
  --icon "$ROOT/assets/icon.icns" --osx-bundle-identifier io.github.nothgm.savegarage \
  --distpath build_out/dist --workpath build_out/work --specpath build_out \
  --paths "$ROOT/engine" \
  --add-data "$ROOT/vendor:vendor" --add-data "$ROOT/ui:ui" --add-data "$ROOT/engine/workers:engine/workers" \
  --add-data "$ROOT/LICENSE:." --add-data "$ROOT/CREDITS.md:." --add-data "$ROOT/README.md:." \
  --hidden-import app --hidden-import money --hidden-import garlic --hidden-import savedit --hidden-import statnames \
  --hidden-import sqlite3 --hidden-import ipaddress --hidden-import select --hidden-import uuid --hidden-import hashlib \
  --hidden-import tempfile --hidden-import argparse --hidden-import contextlib --hidden-import stat --hidden-import zipfile \
  --hidden-import runpy --hidden-import urllib.parse \
  --collect-all cryptography

APP=build_out/dist/SaveGarage.app
PLIST="$APP/Contents/Info.plist"
# The UI lives in the browser, so no Dock icon; macOS asks before the app reaches the PS5 on the local network.
plutil -replace LSUIElement -bool true "$PLIST"
plutil -replace NSLocalNetworkUsageDescription -string "Finds your PS5 and moves your save over your home network." "$PLIST"
codesign --force --deep --sign - "$APP"
rm -f build_out/dist/SaveGarage-macos.zip
ditto -c -k --keepParent "$APP" build_out/dist/SaveGarage-macos.zip
echo "Built $APP"
