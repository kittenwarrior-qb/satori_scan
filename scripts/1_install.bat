@echo off
cd /d "%~dp0.."
echo ============================================
echo   SATORI v2 - Cai dat lan dau
echo ============================================

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [LOI] Chay lai voi quyen Administrator.
    pause & exit /b 1
)

python --version >nul 2>&1
if %errorLevel% neq 0 (
    if exist "%~dp0..\python-installer.exe" (
        echo Dang cai Python...
        "%~dp0..\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    ) else (
        echo [LOI] Chua co Python. Can cai Python 3.11 truoc.
        pause & exit /b 1
    )
)
echo [OK] Python san sang.

echo [1/3] Tao moi truong ao...
if not exist "venv" python -m venv venv
echo [OK] venv san sang.

echo [2/3] Cai thu vien...
venv\Scripts\pip install -r requirements.txt --quiet
echo [OK] Thu vien da cai.

echo [3/3] Tao database...
venv\Scripts\python init_db.py
echo [OK] Database san sang.

echo.
echo ============================================
echo  Hoan tat!
echo  Buoc tiep theo:
echo    1. Mo file .env sua IP thiet bi
echo    2. Chay scripts\2_start.bat
echo ============================================
pause
