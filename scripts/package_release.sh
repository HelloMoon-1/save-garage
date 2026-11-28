#!/bin/bash
# Builds the release files on a Linux machine (no CI needed):
#   MoonSlot-<version>-windows-x64.zip   portable: official embeddable Python + dependencies, double-click to start
#   MoonSlot-<version>-macos.zip         double-click launcher; sets up its own Python environment on first run
#   MoonSlot-<version>-linux-x64.tar.gz  self-contained PyInstaller build
#   SHA256SUMS.txt
# Each package holds build.json, the build marker engine/updater.py reads to update it: its flavour and version, and for
# Windows and macOS the app files and launchers an update replaces and a fingerprint of the Python runtime (an update
# that changes it has to be downloaded by hand). dev_scratch/ship.sh then signs SHA256SUMS.txt (scripts/sign_release.py).
# Output goes to build_out/release, or to OUT=<folder>. Needs python3, curl and internet access.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
PYWIN="${PYWIN:-3.14.10}"                    # Python version bundled in the Windows build
VERSION=$(python3 -c "import re; print(re.search(r\"VERSION = '([^']+)'\", open('engine/app.py').read()).group(1))")
OUT="$(realpath -m "${OUT:-$ROOT/build_out/release}")"
case "$ROOT/" in "$OUT"/*) echo "OUT=$OUT would hold the source: not a folder to build into"; exit 1;; esac
case "$OUT" in /|"$(realpath -m "$HOME")") echo "OUT=$OUT is not a folder to build into"; exit 1;; esac
CACHE="$ROOT/build_out/cache"
STAGE="$ROOT/build_out/stage"
rm -rf "$OUT" "$STAGE"
mkdir -p "$OUT" "$CACHE" "$STAGE"
APP_FILES=(engine vendor ui docs LICENSE NOTICE CREDITS.md README.md README.zh-CN.md requirements.txt)

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

build_json() { # build_json <file> <flavour> [<runtime> <launcher> <readme>]: the build marker engine/updater.py reads
  # runtime: the bundled Python folder (Windows) or requirements.txt (macOS), as SHA-256 over "<sha256>  <path>" lines
  # sorted by path (updater.runtime_id), or over the file. Linux: "files" names everything in the folder (with
  # build.json), which an update renames as a whole, so the updater leaves a folder that holds anything else alone
  VERSION="$VERSION" APP_LIST="${APP_FILES[*]}" python3 - "$@" <<'PY'
import hashlib, json, os, sys
path, flavour, rest = sys.argv[1], sys.argv[2], sys.argv[3:]
b = {'flavour': flavour, 'version': os.environ['VERSION']}
if rest:
    rt, top = rest[0], rest[1:]
    if os.path.isdir(rt):
        lines = []
        for d, _, fs in os.walk(rt):
            for n in fs:
                p = os.path.join(d, n)
                with open(p, 'rb') as f:
                    lines.append((os.path.relpath(p, rt).replace(os.sep, '/'), hashlib.sha256(f.read()).hexdigest()))
        b['runtime'] = hashlib.sha256(''.join('%s  %s\n' % (h, p) for p, h in sorted(lines)).encode()).hexdigest()
    else:
        with open(rt, 'rb') as f:
            b['runtime'] = hashlib.sha256(f.read()).hexdigest()
    b['files'] = os.environ['APP_LIST'].split()
    b['top'] = top
else:
    b['files'] = sorted(set(os.listdir(os.path.dirname(path) or '.')) | {'build.json'})
with open(path, 'w') as f:
    json.dump(b, f, indent=1)
    f.write('\n')
PY
}

echo "== MoonSlot $VERSION"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt pyinstaller

# ---------------------------------------------------------------- Windows (portable)
WIN="$STAGE/win/MoonSlot"
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
# cmd.exe reads a batch file a line at a time, so the line that runs MoonSlot also ends the file: an update can then
# replace this launcher while it is running
printf '%s\r\n' '@echo off' 'title GTA6 Story Save Editor' \
  'echo GTA6 Story Save Editor is starting. Your browser opens in a moment.' \
  'echo Keep this window open while you use the editor. Close it, or click Quit in the page, to stop.' \
  'set SAVEGARAGE_DESKTOP=1' \
  'if not exist "%~dp0app\engine\main.py" if exist "%~dp0.update\backup\app\engine\main.py" move "%~dp0.update\backup\app\engine" "%~dp0app\engine" >nul' \
  '"%~dp0app\python\python.exe" "%~dp0app\engine\main.py" --open %* || pause & exit /b' > "$WIN/Start MoonSlot.bat"
printf '%s\r\n' 'GTA6 Story Save Editor for Windows 10 and 11' '' \
  '1. Double-click "Start MoonSlot.bat". If Windows SmartScreen appears, click More info, then Run anyway.' \
  '2. When Windows Firewall asks about Python, allow it on private networks. Your PS5 needs to reach this PC.' \
  '3. Your browser opens the editor. Follow the steps on screen.' '' \
  'Saves and backups are kept in the saves folder beside the launcher.' \
  'Full guide: see app\README.md or the project page.' > "$WIN/README.txt"
build_json "$WIN/app/build.json" windows "$WIN/app/python" "Start MoonSlot.bat" README.txt
zip_dir "$STAGE/win" MoonSlot "$OUT/MoonSlot-$VERSION-windows-x64.zip"

# ---------------------------------------------------------------- macOS (launcher + source)
MAC="$STAGE/mac/MoonSlot"
copy_app "$MAC/app"
cat > "$MAC/Start MoonSlot.command" <<'SH'
#!/bin/bash
# Starts MoonSlot. The first run sets up a private Python environment, which needs internet access.
cd "$(dirname "$0")/app" || exit 1
# an update cut short at the wrong moment can leave engine/ in its backup: put it back (the app then finishes the job)
[ -f engine/main.py ] || { [ -f ../.update/backup/app/engine/main.py ] && mv ../.update/backup/app/engine engine; }
SUPPORT="$HOME/Library/Application Support/MoonSlot"
VENV="$SUPPORT/venv"
PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "The editor needs Python 3.9 or newer. Install it from https://www.python.org/downloads/macos/ and open this again."
  read -n 1 -s -r -p "Press any key to close."; exit 1
fi
mkdir -p "$SUPPORT"
# the Python setup is kept between versions, so a version that needs a new package adds it here (issue #17)
FRESH=""
if [ ! -x "$VENV/bin/python" ]; then
  echo "Setting up Save Garage for the first time. This takes a minute."
  "$PY" -m venv "$VENV" || { echo "Setup failed. Check your internet connection and try again."; rm -rf "$VENV"; read -n 1 -s -r -p "Press any key to close."; exit 1; }
  FRESH=1
fi
if ! "$VENV/bin/python" -c 'import psutil, cryptography' 2>/dev/null; then
  [ -n "$FRESH" ] || echo "Adding what this version of Save Garage needs. This takes a minute."
  if ! "$VENV/bin/python" -m pip install -q -r requirements.txt; then
    if [ -n "$FRESH" ] || ! "$VENV/bin/python" -c 'import cryptography' 2>/dev/null; then
      echo "Setup failed. Check your internet connection and try again."; rm -rf "$VENV"; read -n 1 -s -r -p "Press any key to close."; exit 1
    fi
    # only psutil is missing: everything but sending back to consoles that ask for IPv6 data still works
    echo "Save Garage couldn't add a package it needs (check your internet connection). It starts anyway; start it again once you're online."
  fi
fi
echo "GTA6 Story Save Editor is running. Keep this window open while you use it. Close it, or click Quit in the page, to stop."
SAVEGARAGE_DESKTOP=1 exec "$VENV/bin/python" engine/main.py --open
SH
chmod +x "$MAC/Start MoonSlot.command"
cat > "$MAC/README.txt" <<'TXT'
GTA6 Story Save Editor for macOS

1. Double-click "Start MoonSlot.command". If macOS says it can't check the developer, right-click it, choose Open,
   then Open again. You only do this once.
2. The first start sets up the editor (needs Python 3.9 or newer and an internet connection).
3. Allow access to devices on your local network when asked. Your PS5 needs to reach this Mac.
4. Your browser opens the editor. Follow the steps on screen.

Saves and backups are kept in the saves folder beside the launcher.
TXT
build_json "$MAC/app/build.json" macos "$MAC/app/requirements.txt" "Start MoonSlot.command" README.txt
zip_dir "$STAGE/mac" MoonSlot "$OUT/MoonSlot-$VERSION-macos.zip"

# ---------------------------------------------------------------- Linux (PyInstaller)
./scripts/build_linux.sh >/dev/null
cp LICENSE NOTICE CREDITS.md README.md README.zh-CN.md build_out/dist/MoonSlot/
mkdir -p build_out/dist/MoonSlot/docs
cp -R docs/releases build_out/dist/MoonSlot/docs/
cat > build_out/dist/MoonSlot/README.txt <<'TXT'
GTA6 Story Save Editor for Linux

Run ./MoonSlot --open (or ./MoonSlot --help for options). curl must be installed.
The PS5 protocol uses ports 1004 to 1006, which Linux keeps for root. Allow them while you use the editor:
  sudo sysctl -w net.ipv4.ip_unprivileged_port_start=1004
and set it back afterwards with ...=1024. Saves and backups are kept in the saves folder beside the launcher.
TXT
build_json build_out/dist/MoonSlot/build.json linux
tar -C build_out/dist -czf "$OUT/MoonSlot-$VERSION-linux-x64.tar.gz" MoonSlot

(cd "$OUT" && sha256sum MoonSlot-* > SHA256SUMS.txt)
rm -rf "$STAGE"
echo "== release files in build_out/release:"
ls -la "$OUT"
cat "$OUT/SHA256SUMS.txt"
