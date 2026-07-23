@echo off
setlocal
if not defined LG3D_ROOT for %%I in ("%~dp0..\..\..") do set "LG3D_ROOT=%%~fI"
if not defined LG3D_PYTHON_EXE set "LG3D_PYTHON_EXE=D:\python\py311\python.exe"
if not exist "%LG3D_PYTHON_EXE%" set "LG3D_PYTHON_EXE=python"
set "PYTHON_EXE=%LG3D_PYTHON_EXE%"
set "PYTHONPATH=%LG3D_ROOT%\package\CoilDataBase;%LG3D_ROOT%\app;%LG3D_ROOT%\app\algorithm_runtime"
if not defined ALGORITHM_3D_MAX_HISTORY_COIL_COUNT set "ALGORITHM_3D_MAX_HISTORY_COIL_COUNT=80"
if not defined COIL_DATABASE_URL echo WARNING: COIL_DATABASE_URL is not set; using application default database config.
cd /d "%LG3D_ROOT%\app\algorithm_runtime"
"%PYTHON_EXE%" main.py
