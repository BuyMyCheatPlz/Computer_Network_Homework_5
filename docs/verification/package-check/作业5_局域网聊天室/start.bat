@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m lan_chat
if errorlevel 1 pause
