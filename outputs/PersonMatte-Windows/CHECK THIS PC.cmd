@echo off
setlocal
title Person Matte - system check
"%~dp0runtime\python.exe" -B "%~dp0person_matte.py" --check
set "MATTE_EXIT=%errorlevel%"
echo.
pause
exit /b %MATTE_EXIT%
