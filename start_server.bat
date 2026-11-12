@echo off
chcp 65001 >nul
cd /d "%~dp0"
bin\chat_server.exe %*
if errorlevel 1 pause
