@echo off
setlocal
cd /d "%~dp0"

if not defined DASHBOARD_HOME (
    for %%I in ("%~dp0..") do set "DASHBOARD_HOME=%%~fI"
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pip --version >nul 2>nul
    if not errorlevel 1 (
        ".venv\Scripts\python.exe" build_portable.py
        goto :end
    )
    echo Existing .venv has no pip. Using system Python instead.
)

py -3 -V >nul 2>nul
if %errorlevel%==0 (
    py -3 build_portable.py
    goto :end
)

python -V >nul 2>nul
if %errorlevel%==0 (
    python build_portable.py
    goto :end
)

echo Python was not found on this machine.
echo Install Python 3.12+ first, then run Build Portable.bat again.
pause
goto :eof

:end
if errorlevel 1 pause
