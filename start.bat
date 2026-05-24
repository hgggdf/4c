@echo off
chcp 65001 >nul
title Medical Strategy - Starting

set ROOT=%~dp0
set ROOT=%ROOT:~0,-1%
set BACKEND=%ROOT%\backend
set FRONTEND=%ROOT%\frontend
set VENV=%BACKEND%\.venv
set PYTHON=%VENV%\Scripts\python.exe

echo ==========================================
echo   Medical Strategy - One Click Start
echo ==========================================
echo.

echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    goto :error
)
python --version
echo.

echo [2/6] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found.
    echo Please install Node.js 18+ from https://nodejs.org/
    goto :error
)
node --version
echo.

echo [3/6] Setting up Python venv...
if not exist "%PYTHON%" (
    echo Creating virtual environment...
    cd /d "%BACKEND%"
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create venv
        goto :error
    )
    echo Installing backend dependencies...
    "%PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: pip install failed
        goto :error
    )
    echo Done.
) else (
    "%PYTHON%" -c "import uvicorn, pymysql, sqlalchemy, fastapi, apscheduler" >nul 2>&1
    if errorlevel 1 (
        echo Installing missing backend dependencies...
        cd /d "%BACKEND%"
        "%PYTHON%" -m pip install -r requirements.txt
        if errorlevel 1 (
            echo ERROR: pip install failed
            goto :error
        )
        echo Done.
    ) else (
        echo OK.
    )
)
echo.

echo [4/6] Setting up frontend...
if not exist "%FRONTEND%\node_modules" (
    echo Running npm install...
    cd /d "%FRONTEND%"
    npm install
    if errorlevel 1 (
        echo ERROR: npm install failed
        goto :error
    )
    echo Done.
) else (
    echo OK.
)
echo.

echo [5/6] Checking .env config...
if not exist "%ROOT%\.env" (
    if exist "%ROOT%\.env.example" (
        echo Creating .env from .env.example...
        copy "%ROOT%\.env.example" "%ROOT%\.env" >nul
        echo WARNING: Please edit .env with your MySQL credentials and API keys.
    ) else (
        echo ERROR: .env not found and no .env.example available.
        goto :error
    )
)
echo OK.
echo.

echo [6/6] Starting services...
cd /d "%BACKEND%"
"%PYTHON%" "%ROOT%\check_db.py" >nul 2>&1
if errorlevel 1 (
    echo WARNING: MySQL not reachable. Check .env config.
    echo Backend will start but may fail at runtime.
)
start "Backend" cmd /k "cd /d %BACKEND% && "%PYTHON%" main.py"
timeout /t 3 /nobreak >nul
start "Frontend" cmd /k "cd /d %FRONTEND% && npm run dev"

echo.
echo ==========================================
echo   Started!
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:5173
echo ==========================================
echo.
pause
exit /b 0

:error
echo.
pause
exit /b 1
