@echo off
setlocal

set "REPO_DIR=%~dp0"
set "PYTHON_BIN=%REPO_DIR%conda-envs\cardioception-nonin\python.exe"
set "TASK_SCRIPT=%REPO_DIR%scripts\run_hrd_nonin.py"

if not exist "%PYTHON_BIN%" (
    echo Could not find the Cardioception Nonin Python environment:
    echo %PYTHON_BIN%
    echo.
    echo Create it first by following README.md.
    echo.
    pause
    exit /b 1
)

cd /d "%REPO_DIR%"
"%PYTHON_BIN%" "%TASK_SCRIPT%"
set "STATUS=%ERRORLEVEL%"

if not "%STATUS%"=="0" (
    echo.
    echo HRD task exited with an error.
    pause
)

exit /b %STATUS%
