@echo off
setlocal

set "REPO_DIR=%~dp0"
set "ENV_DIR=%REPO_DIR%conda-envs\cardioception-hrd"
set "PYTHON_BIN=%ENV_DIR%\python.exe"
set "CHECK_SCRIPT=%REPO_DIR%scripts\check_nonin_env.py"
set "TASK_SCRIPT=%REPO_DIR%scripts\run_hrd_nonin.py"

if not exist "%PYTHON_BIN%" (
    echo Could not find the Cardioception Python environment:
    echo %PYTHON_BIN%
    echo.
    echo Create it first from Anaconda Prompt or Miniforge Prompt:
    echo scripts\setup_cardioception_env.bat
    echo.
    pause
    exit /b 1
)

cd /d "%REPO_DIR%"
set "CONDA_PREFIX=%ENV_DIR%"
set "CONDA_DEFAULT_ENV=cardioception-hrd"
set "PATH=%ENV_DIR%;%ENV_DIR%\Library\mingw-w64\bin;%ENV_DIR%\Library\usr\bin;%ENV_DIR%\Library\bin;%ENV_DIR%\Scripts;%ENV_DIR%\bin;%PATH%"

"%PYTHON_BIN%" "%CHECK_SCRIPT%"
set "STATUS=%ERRORLEVEL%"

if not "%STATUS%"=="0" (
    echo.
    echo HRD environment check failed.
    pause
    exit /b %STATUS%
)

"%PYTHON_BIN%" "%TASK_SCRIPT%"
set "STATUS=%ERRORLEVEL%"

if not "%STATUS%"=="0" (
    echo.
    echo HRD task exited with an error.
    pause
)

exit /b %STATUS%
