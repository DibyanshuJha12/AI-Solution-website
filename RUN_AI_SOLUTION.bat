@echo off
setlocal
cd /d "%~dp0"
set "PS_EXE=powershell.exe"
where pwsh.exe >nul 2>nul
if not errorlevel 1 set "PS_EXE=pwsh.exe"
"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_AI_SOLUTION.ps1" %*
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
  echo.
  echo AI SOLUTION could not start. Review the error above.
  pause
)
endlocal & exit /b %EXITCODE%
