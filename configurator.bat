@echo off

:: Set current directory to directory of script
cd /d "%~dp0"

title Configurator
venv\Scripts\python.exe src\configurator.py