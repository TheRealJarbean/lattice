@echo off

:: Set current directory to directory of script
cd /d "%~dp0"

title GT MBE Control Debugger
set LOG_LEVEL=DEBUG
call venv\Scripts\activate.bat
venv\Scripts\python.exe src\mbe_software\app.py