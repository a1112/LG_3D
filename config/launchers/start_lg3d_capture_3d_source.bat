@echo off
setlocal
set "LG3D_ROOT=D:\LCX_USER\LG_3D"
set "PYTHONPATH=%LG3D_ROOT%\package\CoilDataBase;%LG3D_ROOT%\app;%LG3D_ROOT%\app\CapTrue"
if not defined COIL_DATABASE_URL echo WARNING: COIL_DATABASE_URL is not set; using application default database config.
cd /d "%LG3D_ROOT%\app\CapTrue"
call start_watchdog.bat
