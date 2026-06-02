@echo off
chcp 65001 >nul
echo ========================================
echo Frontend App Starting
echo ========================================
echo.

REM Check backend server
echo Checking backend server status...
call curl -s http://localhost:8000/health >nul 2>&1

if %errorlevel% neq 0 (
    echo WARNING: Backend server is not running
    echo Please start backend first with start_backend.bat
    echo.
    pause
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Start frontend
echo.
echo Starting Streamlit app...
echo URL: http://localhost:8501
echo.
echo Press Ctrl+C to stop the app
echo.

cd frontend
call streamlit run app.py
