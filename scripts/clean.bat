@echo off

rem This script is used for removing build files from the directory

cd %~dp0\..
rmdir /s /q "build", "dist"
del /q /f *.spec
