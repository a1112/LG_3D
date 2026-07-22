@echo off
setlocal
set "PRESERVED_LOGS=build\preserved_dist_logs"
if exist "dist\lis\logs" xcopy /E /I /Y "dist\lis\logs" "%PRESERVED_LOGS%" >nul

pyinstaller --noconfirm lis.spec
if errorlevel 1 exit /b %errorlevel%

if not exist "dist\lis\config" mkdir "dist\lis\config"
xcopy /E /I /Y "config" "dist\lis\config"
if exist "%PRESERVED_LOGS%" xcopy /E /I /Y "%PRESERVED_LOGS%" "dist\lis\logs" >nul
