@echo off

:: Set current directory to directory of script
cd /d "%~dp0"

title GT MBE Control Warnings
set LOG_LEVEL=WARNING
call venv\Scripts\activate.bat
venv\Scripts\python.exe src\mbe_software\app.py