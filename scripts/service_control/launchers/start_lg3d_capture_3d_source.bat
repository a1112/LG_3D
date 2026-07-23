@echo off
setlocal
if not defined LG3D_ROOT for %%I in ("%~dp0..\..\..") do set "LG3D_ROOT=%%~fI"
if not defined LG3D_PYTHON_EXE set "LG3D_PYTHON_EXE=D:\python\py311\python.exe"
set "PYTHONPATH=%LG3D_ROOT%\package\CoilDataBase;%LG3D_ROOT%\app;%LG3D_ROOT%\app\CapTrue"
if not defined COIL_DATABASE_URL echo WARNING: COIL_DATABASE_URL is not set; using application default database config.
cd /d "%LG3D_ROOT%\app\CapTrue"
call start_watchdog.bat
