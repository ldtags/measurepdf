@echo off

rem Runs test modules based on the user input

cd %~dp0\..

call %cd%\.venv\scripts\activate
call python %cd%\test.py %*
@REM pause
