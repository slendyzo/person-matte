@echo off
setlocal
title Person Matte - CPU fallback
"%~dp0runtime\python.exe" -B "%~dp0person_matte.py" --cpu %*
set "MATTE_EXIT=%errorlevel%"
echo.
pause
exit /b %MATTE_EXIT%
