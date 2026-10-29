@echo off
setlocal
title Person Matte - GPU extraction
"%~dp0runtime\python.exe" -B "%~dp0person_matte.py" %*
set "MATTE_EXIT=%errorlevel%"
echo.
if not "%MATTE_EXIT%"=="0" echo Extraction did not complete. Read the error above and README.txt.
pause
exit /b %MATTE_EXIT%
