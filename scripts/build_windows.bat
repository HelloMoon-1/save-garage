@echo off
rem Builds build_out\dist\SaveGarage\SaveGarage.exe. Needs: pip install -r requirements.txt pyinstaller
cd /d "%~dp0.."
set ROOT=%CD%
python -m PyInstaller "%ROOT%\engine\main.py" --name SaveGarage --noconsole --onedir --noconfirm --clean ^
  --icon "%ROOT%\assets\icon.ico" ^
  --distpath "%ROOT%\build_out\dist" --workpath "%ROOT%\build_out\work" --specpath "%ROOT%\build_out" ^
  --paths "%ROOT%\engine" ^
  --add-data "%ROOT%\vendor;vendor" --add-data "%ROOT%\ui;ui" --add-data "%ROOT%\engine\workers;engine\workers" ^
  --add-data "%ROOT%\LICENSE;." --add-data "%ROOT%\CREDITS.md;." --add-data "%ROOT%\README.md;." ^
  --hidden-import app --hidden-import money --hidden-import garlic --hidden-import savedit --hidden-import statnames ^
  --hidden-import sqlite3 --hidden-import ipaddress --hidden-import select --hidden-import uuid --hidden-import hashlib ^
  --hidden-import tempfile --hidden-import argparse --hidden-import contextlib --hidden-import stat --hidden-import zipfile ^
  --hidden-import runpy --hidden-import urllib.parse ^
  --collect-all cryptography
