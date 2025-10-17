@echo off
cd /d "%~dp0"
title GT MBE Control Warnings
set LOG_LEVEL=WARNING
venv\Scripts\python.exe src\main.py