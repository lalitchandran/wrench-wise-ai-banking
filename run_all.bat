@echo off
setlocal enabledelayedexpansion

title Bharat Apex Digital Bank - Production-Grade Multi-Agent Banking System
color 0B

echo ===============================================================================
echo          BHARAT APEX DIGITAL BANK - MULTI-AGENT SYSTEM LAUNCHER
echo     Powered by LangGraph, SQLite (INR ₹), FastAPI, React, and Streamlit
echo ===============================================================================
echo.

:: Detect Python executable
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PY_CMD=py
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set PY_CMD=python
    ) else (
        echo [ERROR] Python was not found in PATH! Please install Python 3.10+ and retry.
        pause
        exit /b 1
    )
)

echo [*] Detected Python command: %PY_CMD%

:: Step 1: Install Python Requirements
echo [*] Checking and installing Python dependencies...
%PY_CMD% -m pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [!] Warning: Some dependencies may not have installed cleanly. Proceeding...
)

:: Step 2: Seed SQLite Database
echo [*] Initializing SQLite Core Banking Engine (Aarav, Bhavna, Chirag in INR)...
%PY_CMD% -c "from backend.database import init_db; init_db('banking.db', seed=True); print('    Core ledger verified in INR (₹).')"

:: Step 3: Check / Build React Frontend
if not exist "frontend\dist\index.html" (
    echo [*] Building React Frontend...
    where npm >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        cd frontend
        call npm install --silent
        call npm run build
        cd ..
        echo [*] React frontend build complete.
    ) else (
        echo [!] npm not found. Falling back to Streamlit interface mode.
    )
)

:: Step 4: Launch Web Interface
echo.
echo ===============================================================================
echo [SUCCESS] Multi-Agent Mesh is ready!
echo.
echo Launching React Frontend + FastAPI Unified Server:
echo    URL: http://127.0.0.1:8000
echo.
echo (To launch Streamlit dashboard instead: %PY_CMD% -m streamlit run app.py)
echo ===============================================================================
echo.

:: Open Browser
start "" "http://127.0.0.1:8000"

:: Start FastAPI Server (serves both React frontend and Multi-Agent API)
%PY_CMD% -m uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload

pause
