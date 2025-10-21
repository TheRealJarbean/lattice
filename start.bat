@echo off

:: Set current directory to directory of script
cd /d "%~dp0"

title GT MBE Control Warnings
set LOG_LEVEL=WARNING
venv\Scripts\python.exe src\main.py