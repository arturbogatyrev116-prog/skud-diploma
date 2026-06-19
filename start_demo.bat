@echo off
cd /d "%~dp0"

if not exist venv\Scripts\activate.bat (
    echo.
    echo [ERROR] venv not found. Run setup.bat first.
    echo.
    pause
    exit /b 1
)

if not exist .env (
    echo.
    echo [ERROR] .env not found. Run setup.bat first.
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   SKUD - Demo launcher
echo ================================================
echo.
echo  1. Window "SKUD Server"  - Flask on port 5001
echo  2. Window "Ngrok Tunnel" - HTTPS tunnel for mobile
echo  3. Browser opens /terminal with QR code
echo.
echo  To stop: stop_demo.bat (or close the windows)
echo ================================================
echo.

REM Start Flask in a separate window (chcp 65001 for Russian flask logs)
start "SKUD Server" cmd /k "chcp 65001 >nul && cd /d "%~dp0" && call venv\Scripts\activate && python app.py"

REM Wait for Flask to boot
timeout /t 3 /nobreak >nul

REM Start ngrok if available
if exist tools\ngrok.exe (
    start "Ngrok Tunnel" cmd /k "cd /d "%~dp0" && tools\ngrok.exe http 5001"
    timeout /t 3 /nobreak >nul
) else (
    echo.
    echo [WARNING] tools\ngrok.exe not found.
    echo Mobile page will be reachable only on the local network.
    echo.
)

REM Open terminal page with QR
start "" "http://localhost:5001/terminal"

echo.
echo Done. Terminal windows are open.
echo You can close this window.
echo.
timeout /t 5
exit /b 0
