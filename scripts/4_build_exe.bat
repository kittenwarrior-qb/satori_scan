@echo off
cd /d "%~dp0.."
echo Dang dong goi SATORI thanh .exe...
venv\Scripts\pip install pyinstaller --quiet
venv\Scripts\pyinstaller --name satori --onefile ^
    --add-data "app/templates;app/templates" ^
    --add-data "app/static;app/static" ^
    --hidden-import passlib.handlers.bcrypt ^
    --hidden-import pymodbus ^
    run.py
echo.
echo Ket qua: dist\satori.exe
echo Nho copy file .env vao cung thu muc voi satori.exe
pause
