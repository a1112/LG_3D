@echo off
setlocal
set "LG3D_ROOT=D:\LCX_USER\LG_3D"
set "PYTHON_EXE=D:\python\py311\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
set "PYTHONPATH=%LG3D_ROOT%\package\CoilDataBase;%LG3D_ROOT%\app;%LG3D_ROOT%\app\algorithm_runtime_2D"
if not defined COIL_DATABASE_URL echo WARNING: COIL_DATABASE_URL is not set; using application default database config.
cd /d "%LG3D_ROOT%\app\algorithm_runtime_2D"
"%PYTHON_EXE%" server.py
