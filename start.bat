@echo off
chcp 65001 >nul
title Medical Strategy - Starting

set ROOT=%~dp0
set ROOT=%ROOT:~0,-1%
set BACKEND=%ROOT%\backend
set FRONTEND=%ROOT%\frontend

echo ==========================================
echo   Medical Strategy - One Click Start
echo ==========================================
echo.

echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    goto :error
)
python --version
echo.

echo [2/5] Checking backend dependencies...
python -c "import uvicorn, pymysql, sqlalchemy, fastapi" >nul 2>&1
if errorlevel 1 (
    echo Installing backend dependencies...
    cd /d "%BACKEND%"
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: pip install failed
        goto :error
    )
    echo Done.
) else (
    echo OK.
)
echo.

echo [3/5] Checking frontend dependencies...
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

echo [4/5] Checking database...
cd /d "%BACKEND%"
python "%ROOT%\check_db.py"
if errorlevel 1 (
    echo ERROR: Cannot connect to MySQL. Check backend\.env config.
    goto :error
)
echo.

echo [5/5] Starting services...
start "Backend" cmd /k "cd /d %BACKEND% && python -m uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4"
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
