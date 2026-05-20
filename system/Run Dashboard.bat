@echo off
setlocal
cd /d "%~dp0"

if not defined DASHBOARD_HOME (
    for %%I in ("%~dp0..") do set "DASHBOARD_HOME=%%~fI"
)

set "SOURCE_RUN=%~dp0run_dashboard.py"
set "SOURCE_VENV=%~dp0.venv\Scripts\python.exe"

if exist "%SOURCE_VENV%" (
    "%SOURCE_VENV%" -m pip --version >nul 2>nul
    if not errorlevel 1 (
        "%SOURCE_VENV%" "%SOURCE_RUN%"
        goto :end
    )
    echo Existing .venv has no pip. Using system Python instead.
)

py -3 -V >nul 2>nul
if %errorlevel%==0 (
    py -3 "%SOURCE_RUN%"
    goto :end
)

python -V >nul 2>nul
if %errorlevel%==0 (
    python "%SOURCE_RUN%"
    goto :end
)

echo.
echo Python was not found on this machine.
echo Install Python 3.12+ first, then run Run Dashboard.bat again.
echo.
pause
goto :eof

:end
if errorlevel 1 pause
