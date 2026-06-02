@echo off
chcp 65001 >nul
echo ========================================
echo Backend Server Starting
echo ========================================
echo.

REM Check .env file
if not exist .env (
    echo ERROR: .env file not found.
    echo Please create .env file and set GEMINI_API_KEY
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Start backend
echo.
echo Starting FastAPI server...
echo URL: http://localhost:8000
echo Swagger UI: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

cd backend
call python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
