@echo off
setlocal
title Person Matte - local GPU extraction
set "MATTE_PYTHON=F:\TRABALHO\DELPHI DIGITAL\Podcast Tools\.venv-portrait-native\Scripts\python.exe"
if not exist "%MATTE_PYTHON%" (
  echo The local portrait Python runtime was not found.
  echo Expected: %MATTE_PYTHON%
  pause
  exit /b 1
)
"%MATTE_PYTHON%" "%~dp0person_matte.py" %*
set "MATTE_EXIT=%errorlevel%"
if not "%MATTE_EXIT%"=="0" (
  echo.
  echo Extraction failed. Read the error above. The source is unchanged.
) else (
  echo.
  echo Finished. Your new MATTE folder is beside the source video.
)
pause
exit /b %MATTE_EXIT%
