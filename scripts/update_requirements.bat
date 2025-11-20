@REM A simple script to update requirements.txt while excluding the project itself.

@REM Author: Jaron Anderson
@REM Email: jaron@pressanybutton.us
@REM Date: 11-19-2025
@REM Version: 1.0

cd /d "%~dp0"
cd ..

call venv\Scripts\activate.bat
venv\Scripts\python.exe -m pip freeze | findstr /v /i "mbe_software" > requirements.txt