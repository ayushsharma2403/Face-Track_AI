@echo off
cd /d "%~dp0"
echo ========================================================
echo   Starting Face-Track AI Digital Biometric System...
echo ========================================================

IF EXIST .venv_cam\Scripts\python.exe (
    set "PYTHON_EXE=.venv_cam\Scripts\python.exe"
) ELSE IF EXIST .venv\Scripts\python.exe (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) ELSE (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" app.py
pause
