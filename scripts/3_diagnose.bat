@echo off
cd /d "%~dp0.."
echo ============================================
echo   SATORI v2 - Kiem tra thiet bi
echo ============================================
echo.
echo  1. Xem tat ca IP tren mang LAN (arp -a)
echo  2. Test Scanner (lang nghe port 51236)
echo  3. Test Laser   (gui lenh in thu)
echo  4. Test IO-Box  (kich tung coil)
echo  5. Ping thiet bi trong .env
echo.
set /p choice=Nhap so (1-5):

if "%choice%"=="1" goto lan_scan
if "%choice%"=="2" goto scanner
if "%choice%"=="3" goto laser
if "%choice%"=="4" goto iobox
if "%choice%"=="5" goto ping
goto end

:lan_scan
echo.
echo --- Danh sach thiet bi tren mang LAN ---
arp -a
echo.
echo Neu chua thay du thiet bi, thu ping broadcast:
echo   ping 192.168.1.255
echo Roi chay lai arp -a
goto end

:scanner
echo Lang nghe port 51236 - cho Scanner ket noi...
venv\Scripts\python diagnose.py scanner 51236
goto end

:laser
set /p ip=Nhap IP laser (vi du 192.168.1.60):
set /p port=Nhap Port (Enter = 9100):
if "%port%"=="" set port=9100
venv\Scripts\python diagnose.py laser %ip% %port%
goto end

:iobox
set /p ip=Nhap IP IO-Box (vi du 192.168.1.50):
set /p coil=Nhap so coil muon test (0, 1, 2...):
venv\Scripts\python diagnose.py iobox %ip% 502 %coil%
goto end

:ping
venv\Scripts\python diagnose.py ping
goto end

:end
pause
