@echo off

:: Set current directory to directory of script
cd /d "%~dp0"

title Configurator
call venv\Scripts\activate.bat
venv\Scripts\python.exe src\configurator.py