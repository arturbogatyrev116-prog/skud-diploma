@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ================================================
echo   SKUD - Setup (first-time installation)
echo ================================================
echo.

REM === [1/5] Check Python ===
echo [1/5] Checking Python...
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found in PATH.
    echo Install Python 3.10+ from https://python.org/downloads
    echo IMPORTANT: enable "Add Python to PATH" during installation.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo       Found Python !PYVER!
echo.

REM === [2/5] Virtual environment ===
echo [2/5] Virtual environment (venv)...
if exist venv\Scripts\activate.bat (
    echo       venv already exists, skipping.
) else (
    echo       Creating venv...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
    echo       venv created.
)
echo.

REM === [3/5] Install dependencies ===
echo [3/5] Installing dependencies from requirements.txt...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
REM Note: RPi-only packages are skipped via platform markers in requirements.txt
REM Verify critical packages actually installed (pip can stop on first error)
python -c "import flask, qrcode, cryptography, dotenv, flask_wtf" 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] Critical packages failed to install in venv.
    echo Trying to install them individually...
    python -m pip install flask flask-wtf cryptography python-dotenv "qrcode[pil]"
    python -c "import flask, qrcode, cryptography, dotenv, flask_wtf" 2>nul
    if errorlevel 1 (
        echo.
        echo [FATAL] Cannot install core packages. Check Python version compatibility.
        echo Python 3.14 may lack pre-built wheels for some packages.
        echo Consider installing Python 3.12 from https://python.org/downloads
        pause
        exit /b 1
    )
)
echo       Core packages OK ^(flask, qrcode, cryptography, dotenv, flask_wtf^).
echo.

REM === [4/5] .env file ===
echo [4/5] .env configuration...
if exist .env (
    echo       .env already exists, skipping.
) else (
    if not exist .env.example (
        echo [ERROR] .env.example not found.
        pause
        exit /b 1
    )
    copy .env.example .env >nul
    REM Generate SECRET_KEY and NFC_TOKEN_KEY via Python (UTF-8 safe)
    python -c "import io, secrets; from cryptography.fernet import Fernet; s=io.open('.env',encoding='utf-8').read(); s=s.replace('замените_на_случайную_строку_32_байта', secrets.token_hex(32)); s=s.replace('generate_nfc_key_placeholder', Fernet.generate_key().decode()); io.open('.env','w',encoding='utf-8',newline='\n').write(s)"
    if errorlevel 1 (
        echo [WARNING] Could not auto-generate keys. Edit .env manually.
    ) else (
        echo       .env created, SECRET_KEY and NFC_TOKEN_KEY generated.
    )
)
echo.

REM === [5/5] Download ngrok ===
echo [5/5] ngrok HTTPS tunnel...
if not exist tools mkdir tools
if exist tools\ngrok.exe (
    echo       ngrok.exe already present, skipping.
) else (
    echo       Downloading ngrok via PowerShell ^(~20 MB^)...
    powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip' -OutFile 'tools\ngrok.zip'"
    if errorlevel 1 (
        echo [WARNING] Failed to download ngrok.
        echo Download manually from https://ngrok.com/download and put ngrok.exe in tools\
    ) else (
        powershell -NoProfile -Command "Expand-Archive -Path 'tools\ngrok.zip' -DestinationPath 'tools' -Force"
        del /q tools\ngrok.zip
        echo       ngrok.exe downloaded to tools\
    )
)
echo.

REM === Check ngrok authtoken ===
if exist tools\ngrok.exe (
    tools\ngrok.exe config check >nul 2>&1
    if errorlevel 1 (
        echo --------------------------------------------------
        echo  IMPORTANT: ngrok requires an authtoken.
        echo  1. Sign up at https://dashboard.ngrok.com
        echo  2. Copy token from https://dashboard.ngrok.com/get-started/your-authtoken
        echo  3. Run this command in THIS folder:
        echo        setup_ngrok.bat YOUR_TOKEN
        echo --------------------------------------------------
        echo.
    ) else (
        echo       ngrok authtoken already configured.
        echo.
    )
)

echo ================================================
echo  DONE. Run start_demo.bat to launch the demo.
echo ================================================
echo.
pause
