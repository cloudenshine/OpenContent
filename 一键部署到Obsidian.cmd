@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Deploy-ToObsidian.ps1" %*
if errorlevel 1 (
    echo.
    echo [ERROR] Deployment failed. Press any key to exit.
    pause
    exit /b 1
)
echo.
echo [SUCCESS] Deployment completed. Press any key to exit.
pause
