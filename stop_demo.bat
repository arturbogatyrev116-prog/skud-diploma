@echo off

echo Stopping SKUD and ngrok...

taskkill /FI "WINDOWTITLE eq SKUD Server*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Ngrok Tunnel*" /T /F >nul 2>&1

REM Fallback: kill ngrok by process name
taskkill /IM ngrok.exe /F >nul 2>&1

echo Done.
timeout /t 2 >nul
exit /b 0
