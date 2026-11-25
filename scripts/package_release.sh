#!/bin/bash
# Builds the release files on a Linux machine (no CI needed):
#   SaveGarage-<version>-windows-x64.zip   portable: official embeddable Python + dependencies, double-click to start
#   SaveGarage-<version>-macos.zip         double-click launcher; sets up its own Python environment on first run
#   SaveGarage-<version>-linux-x64.tar.gz  self-contained PyInstaller build
#   SHA256SUMS.txt
# Output goes to build_out/release. Needs python3, curl and internet access.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
PYWIN="${PYWIN:-3.14.10}"                    # Python version bundled in the Windows build
VERSION=$(python3 -c "import re; print(re.search(r\"VERSION = '([^']+)'\", open('engine/app.py').read()).group(1))")
OUT="$ROOT/build_out/release"
CACHE="$ROOT/build_out/cache"
STAGE="$ROOT/build_out/stage"
rm -rf "$OUT" "$STAGE"
mkdir -p "$OUT" "$CACHE" "$STAGE"
APP_FILES=(engine vendor ui LICENSE CREDITS.md README.md README.zh-CN.md requirements.txt)

copy_app() {   # copy the app source into $1, without caches
  mkdir -p "$1"
  for f in "${APP_FILES[@]}"; do cp -R "$ROOT/$f" "$1/"; done
  find "$1" -name __pycache__ -prune -exec rm -rf {} +
}

zip_dir() {    # zip_dir <parent> <folder> <archive>; keeps the executable bit of launchers and binaries
  python3 - "$1" "$2" "$3" <<'PY'
import os, sys, zipfile
parent, folder, archive = sys.argv[1:]
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for root, dirs, files in os.walk(os.path.join(parent, folder)):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(root, name)
            info = zipfile.ZipInfo.from_file(path, os.path.relpath(path, parent))
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(path, 'rb') as f:
                z.writestr(info, f.read())
PY
}

echo "== Save Garage $VERSION"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt pyinstaller

# ---------------------------------------------------------------- Windows (portable)
WIN="$STAGE/win/SaveGarage"
copy_app "$WIN/app"
EMBED="$CACHE/python-$PYWIN-embed-amd64.zip"
[ -f "$EMBED" ] || curl -sSfL -o "$EMBED" "https://www.python.org/ftp/python/$PYWIN/python-$PYWIN-embed-amd64.zip"
python3 -c "import zipfile, sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$EMBED" "$WIN/app/python"
PTH=$(ls "$WIN/app/python"/python3*._pth)
printf 'Lib\\site-packages\r\n' >> "$PTH"
WHEELS="$CACHE/wheels-win-$PYWIN"
PYTAG=$(echo "$PYWIN" | awk -F. '{print $1$2}')
.venv/bin/python -m pip download -q --only-binary=:all: --platform win_amd64 --implementation cp --python-version "$PYTAG" \
  -r requirements.txt -d "$WHEELS"
mkdir -p "$WIN/app/python/Lib/site-packages"
for w in "$WHEELS"/*.whl; do python3 -c "import zipfile, sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$w" "$WIN/app/python/Lib/site-packages"; done
printf '%s\r\n' '@echo off' 'title Save Garage' \
  'echo Save Garage is starting. Your browser opens in a moment.' \
  'echo Keep this window open while you use Save Garage. Close it, or click Quit in the page, to stop.' \
  'set SAVEGARAGE_DESKTOP=1' \
  '"%~dp0app\python\python.exe" "%~dp0app\engine\main.py" --open %*' \
  'if errorlevel 1 pause' > "$WIN/Start Save Garage.bat"
printf '%s\r\n' 'Save Garage for Windows 10 and 11' '' \
  '1. Double-click "Start Save Garage.bat". If Windows SmartScreen appears, click More info, then Run anyway.' \
  '2. When Windows Firewall asks about Python, allow it on private networks. Your PS5 needs to reach this PC.' \
  '3. Your browser opens Save Garage. Follow the steps on screen.' '' \
  'Saves and backups are kept in %LOCALAPPDATA%\SaveGarage.' \
  'Full guide: see app\README.md or the project page.' > "$WIN/README.txt"
zip_dir "$STAGE/win" SaveGarage "$OUT/SaveGarage-$VERSION-windows-x64.zip"

# ---------------------------------------------------------------- macOS (launcher + source)
MAC="$STAGE/mac/SaveGarage"
copy_app "$MAC/app"
cat > "$MAC/Start Save Garage.command" <<'SH'
#!/bin/bash
# Starts Save Garage. The first run sets up a private Python environment, which needs internet access.
cd "$(dirname "$0")/app" || exit 1
SUPPORT="$HOME/Library/Application Support/SaveGarage"
VENV="$SUPPORT/venv"
PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "Save Garage needs Python 3.9 or newer. Install it from https://www.python.org/downloads/macos/ and open this again."
  read -n 1 -s -r -p "Press any key to close."; exit 1
fi
mkdir -p "$SUPPORT"
if [ ! -x "$VENV/bin/python" ]; then
  echo "Setting up Save Garage for the first time. This takes a minute."
  "$PY" -m venv "$VENV" && "$VENV/bin/python" -m pip install -q -r requirements.txt || { echo "Setup failed. Check your internet connection and try again."; rm -rf "$VENV"; read -n 1 -s -r -p "Press any key to close."; exit 1; }
fi
echo "Save Garage is running. Keep this window open while you use it. Close it, or click Quit in the page, to stop."
SAVEGARAGE_DESKTOP=1 exec "$VENV/bin/python" engine/main.py --open
SH
chmod +x "$MAC/Start Save Garage.command"
cat > "$MAC/README.txt" <<'TXT'
Save Garage for macOS

1. Double-click "Start Save Garage.command". If macOS says it can't check the developer, right-click it, choose Open,
   then Open again. You only do this once.
2. The first start sets up Save Garage (needs Python 3.9 or newer and an internet connection).
3. Allow access to devices on your local network when asked. Your PS5 needs to reach this Mac.
4. Your browser opens Save Garage. Follow the steps on screen.

Saves and backups are kept in ~/Library/Application Support/SaveGarage.
TXT
zip_dir "$STAGE/mac" SaveGarage "$OUT/SaveGarage-$VERSION-macos.zip"

# ---------------------------------------------------------------- Linux (PyInstaller)
./scripts/build_linux.sh >/dev/null
cat > build_out/dist/SaveGarage/README.txt <<'TXT'
Save Garage for Linux

Run ./SaveGarage --open (or ./SaveGarage --help for options). curl must be installed.
The PS5 protocol uses ports 1004 to 1006, which Linux keeps for root. Allow them while you use Save Garage:
  sudo sysctl -w net.ipv4.ip_unprivileged_port_start=1004
and set it back afterwards with ...=1024. Saves and backups are kept in ~/.local/share/SaveGarage.
TXT
tar -C build_out/dist -czf "$OUT/SaveGarage-$VERSION-linux-x64.tar.gz" SaveGarage

(cd "$OUT" && sha256sum SaveGarage-* > SHA256SUMS.txt)
rm -rf "$STAGE"
echo "== release files in build_out/release:"
ls -la "$OUT"
cat "$OUT/SHA256SUMS.txt"
