@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=%~dp0..\env\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Creating the parent virtual environment...
    py -3 -m venv "%~dp0..\env"
    if errorlevel 1 goto failed
)

"%PYTHON%" -c "import yaml; from websockets.asyncio.server import serve" >nul 2>&1
if errorlevel 1 (
    echo Installing WebSocket proxy dependencies...
    "%PYTHON%" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 goto failed
)

"%PYTHON%" "%~dp0server.py" %*
if errorlevel 1 goto failed
exit /b 0

:failed
echo Could not start the WebSocket server.
pause
exit /b 1
