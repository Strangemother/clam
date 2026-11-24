@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0env\Scripts\python.exe" (
    "%~dp0env\Scripts\python.exe" "%~dp0run_server_and_ws.py"
    goto done
)

for %%V in (3.14 3.13 3.12 3.11 3.10) do (
    py -%%V -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        py -%%V "%~dp0run_server_and_ws.py"
        goto done
    )
)
python -c "import sys; sys.exit(not (3,10)<=sys.version_info[:2]<=(3,14))" ^
    >nul 2>&1
if not errorlevel 1 (
    python "%~dp0run_server_and_ws.py"
    goto done
)
echo Python 3.10 through 3.14 is required.
pause
exit /b 1

:done
if errorlevel 1 (
    echo Server launcher failed.
    pause
    exit /b 1
)
exit /b 0
