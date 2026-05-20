@echo off
setlocal
cd /d "%~dp0"

set "DASHBOARD_HOME=%~dp0"
set "APP_DIR=%~dp0system"
set "SOURCE_VENV=%APP_DIR%\.venv\Scripts\python.exe"
set "SOURCE_LAUNCHER=%APP_DIR%\Run Dashboard.bat"
set "PORTABLE_EXE=%APP_DIR%\dist\Dashboard Bangchak\Dashboard Bangchak.exe"
set "HAS_PYTHON="

if exist "%SOURCE_VENV%" (
    "%SOURCE_VENV%" -m pip --version >nul 2>nul
    if not errorlevel 1 (
        set "HAS_PYTHON=1"
    ) else (
        echo Existing system\.venv has no pip. Using system Python instead.
    )
)

py -3 -V >nul 2>nul
if %errorlevel%==0 (
    set "HAS_PYTHON=1"
)

python -V >nul 2>nul
if %errorlevel%==0 (
    set "HAS_PYTHON=1"
)

if defined HAS_PYTHON if exist "%SOURCE_LAUNCHER%" (
    call "%SOURCE_LAUNCHER%"
    goto :eof
)

if exist "%PORTABLE_EXE%" (
    start "" /D "%APP_DIR%\dist\Dashboard Bangchak" "%PORTABLE_EXE%"
    goto :eof
)

echo.
echo Python was not found on this machine.
echo.
echo Source version:
echo - install Python 3.12+ and run this file again
echo.
echo Portable version:
echo - run Run Portable Dashboard.bat if the portable build already exists
echo - or build it first with Build Portable.bat
echo.
pause
