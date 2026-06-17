@echo off
cd /d "%~dp0.."
echo Dang khoi dong SATORI v2...
if not exist "venv\Scripts\python.exe" (
    echo [LOI] Chua cai dat. Chay scripts\1_install.bat truoc.
    pause & exit /b 1
)
venv\Scripts\python run.py
if %errorLevel% neq 0 pause
