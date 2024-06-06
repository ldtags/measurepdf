@echo off

rem This script automates the PyInstaller executable building process

setlocal enabledelayedexpansion
setlocal enableextensions

for %%x in (%*) do (
    if /I "--clean"=="%%~x" call %~dp0/clean.bat
)

set EXEC_NAME=MeasureSummary
set ASSETS=src\assets
set BUILD_CMD=pyinstaller --clean -y -n %EXEC_NAME% --noconsole --icon=%ASSETS%\images\etrm.ico

for %%x in (%ASSETS%\images\*) do (
    set BUILD_CMD=!BUILD_CMD! --add-data=%%x;src\assets\images
)
for /f "tokens=* delims=" %%x in ('dir /b %ASSETS%\fonts\*') do (
    for %%y in (%ASSETS%\fonts\%%x\*) do (
        set BUILD_CMD=!BUILD_CMD! --add-data=%%y;src\assets\fonts\%%x
    )
)

cd %~dp0\..
call %BUILD_CMD% --hidden-import customtkinter cli.py

mkdir .\dist\summaries
ren %~dp0\..\dist\MeasureSummary bin
rem cscript .\scripts\shortcut.vbs "%~dp0..\dist\Measure Summarizer.LNK" "%~dp0..\dist\bin\src\assets\images\etrm.ico"

endlocal
