@echo off
setlocal
set "BASE_DIR=%~dp0"
if not exist "%BASE_DIR%py\\_rcc" mkdir "%BASE_DIR%py\\_rcc"
pyside6-rcc "%BASE_DIR%qml.qrc" --binary -o "%BASE_DIR%py\\_rcc\\qml.rcc"
pyside6-rcc "%BASE_DIR%resource.qrc" --binary -o "%BASE_DIR%py\\_rcc\\resource.rcc"
python main.py
