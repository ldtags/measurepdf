@echo off

rem This script automates the PyInstaller executable building process

setlocal enabledelayedexpansion
setlocal enableextensions


set EXEC_NAME=MeasureSummary
if not "%1"=="" set EXEC_NAME=%1

set ASSETS=src\assets
set BUILD_CMD=pyinstaller --clean --noconsole -y -n %EXEC_NAME% --icon=%ASSETS%\images\etrm.ico
for %%x in (%ASSETS%\images\*) do (
    set BUILD_CMD=!BUILD_CMD! --add-data=%%x;src\assets\images
)
for /f "tokens=* delims=" %%x in ('dir /b %ASSETS%\fonts\*') do (
    for %%y in (%ASSETS%\fonts\%%x\*) do (
        set BUILD_CMD=!BUILD_CMD! --add-data=%%y;src\assets\fonts\%%x
    )
)

cd %~dp0\..
call %BUILD_CMD% cli.py


endlocal
