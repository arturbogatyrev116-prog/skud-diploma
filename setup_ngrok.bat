@echo off
cd /d "%~dp0"

if "%~1"=="" (
    echo.
    echo Usage: setup_ngrok.bat YOUR_TOKEN
    echo.
    echo Get your token at https://dashboard.ngrok.com/get-started/your-authtoken
    echo.
    pause
    exit /b 1
)

if not exist tools\ngrok.exe (
    echo.
    echo [ERROR] tools\ngrok.exe not found. Run setup.bat first.
    echo.
    pause
    exit /b 1
)

echo Configuring ngrok authtoken...
tools\ngrok.exe config add-authtoken %1
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to set authtoken.
    pause
    exit /b 1
)

echo.
echo Done. You can now run start_demo.bat
echo.
pause
