@echo off
cd /d "%~dp0"
title GT MBE Control Debugger
set LOG_LEVEL=DEBUG
venv\Scripts\python.exe src\main.py