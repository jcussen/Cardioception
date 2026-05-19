@echo off
setlocal

for %%I in ("%~dp0..") do set "REPO_DIR=%%~fI"
set "ENV_DIR=%REPO_DIR%\conda-envs\cardioception-hrd"
set "ENV_FILE=%REPO_DIR%\environment_cardioception.yml"
set "CHECK_SCRIPT=%REPO_DIR%\scripts\check_nonin_env.py"

where conda >nul 2>nul
if errorlevel 1 (
    echo Could not find conda.
    echo.
    echo Open Anaconda Prompt or Miniforge Prompt, go to this repository,
    echo and run:
    echo scripts\setup_cardioception_env.bat
    echo.
    pause
    exit /b 1
)

if exist "%ENV_DIR%\python.exe" (
    echo The Cardioception environment already exists:
    echo %ENV_DIR%
    echo.
    echo To rebuild it, delete this folder first:
    echo rmdir /s /q conda-envs\cardioception-hrd
    echo.
    pause
    exit /b 1
)

echo Using repository:
echo %REPO_DIR%
echo.
echo Creating Cardioception environment:
echo %ENV_DIR%
echo.

conda env create --prefix "%ENV_DIR%" -f "%ENV_FILE%"
if errorlevel 1 goto failed

echo.
echo Installing PsychoPy...
conda run --prefix "%ENV_DIR%" python -m pip install "psychopy==2025.2.4"
if errorlevel 1 goto failed

echo.
echo Installing Systole...
conda run --prefix "%ENV_DIR%" python -m pip install "systole==0.3.1" --no-deps
if errorlevel 1 goto failed

echo.
echo Installing Cardioception...
conda run --prefix "%ENV_DIR%" python -m pip install -e "%REPO_DIR%" --no-deps
if errorlevel 1 goto failed

echo.
echo Checking the environment...
conda run --prefix "%ENV_DIR%" python "%CHECK_SCRIPT%"
if errorlevel 1 goto failed

echo.
echo Setup complete. You can now double-click Run_HRD.bat.
pause
exit /b 0

:failed
echo.
echo Setup failed. Copy the messages above when asking for help.
pause
exit /b 1
