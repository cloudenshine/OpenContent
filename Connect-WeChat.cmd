@echo off
chcp 65001 >nul
cd /d "%~dp0"
python scripts\connect_wechat.py %*
echo.
pause
