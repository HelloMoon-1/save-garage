@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0Check-Transfer.ps1" %1
pause
