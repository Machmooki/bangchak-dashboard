@echo off
setlocal
cd /d "%~dp0"

set "PORTABLE_DIR=%~dp0system\dist\Dashboard Bangchak"
set "PORTABLE_EXE=%PORTABLE_DIR%\Dashboard Bangchak.exe"

if exist "%PORTABLE_EXE%" (
    start "" /D "%PORTABLE_DIR%" "%PORTABLE_EXE%"
    goto :eof
)

echo Portable build was not found.
echo.
echo Build it first with Build Portable.bat
echo or open system\dist\Dashboard Bangchak after packaging.
echo.
pause
