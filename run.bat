@echo off
setlocal
cd /d "%~dp0"
set "CHAT_URL=http://127.0.0.1:8000"

powershell -NoProfile -Command "try { $health = Invoke-RestMethod -Uri '%CHAT_URL%/api/health' -TimeoutSec 2; if ($health.ok) { exit 0 } } catch {}; exit 1"
if errorlevel 1 (
  echo Starting the customer support chatbot...
  start "Customer Support Chatbot Server" /D "%~dp0" py -3 server.py
)

echo Waiting for the chatbot server...
powershell -NoProfile -Command "$ready = $false; for ($i = 0; $i -lt 30; $i++) { try { $health = Invoke-RestMethod -Uri '%CHAT_URL%/api/health' -TimeoutSec 1; if ($health.ok) { $ready = $true; break } } catch { Start-Sleep -Seconds 1 } }; if (-not $ready) { exit 1 }"
if errorlevel 1 (
  echo.
  echo The chatbot server did not start. Check the server window for an error.
  echo Make sure Python 3 and the Ollama app are available.
  pause
  exit /b 1
)

echo Chatbot is ready at %CHAT_URL%
start "" "%CHAT_URL%"
echo Keep the chatbot server window open while chatting.
