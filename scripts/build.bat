@echo off

rem This script automates the PyInstaller executable building process

set EXEC_NAME=MeasureSummary
if not "%1"=="" set EXEC_NAME=%1

set DB_FILE=src/assets/
set SCHEMA_FILE=measureparser/resources/measure.schema.json

cd %~dp0\..
call pyinstaller --clean --noconsole -y -n "%EXEC_NAME%"^
 --icon=src/assets/app.ico^
 --add-data="%DB_FILE%;assets"^
 --add-data="%SCHEMA_FILE%;assets"^
 measureparser/__main__.py
