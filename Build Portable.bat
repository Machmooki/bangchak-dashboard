@echo off
setlocal
cd /d "%~dp0"
set "DASHBOARD_HOME=%~dp0"
call "%~dp0system\Build Portable.bat"
