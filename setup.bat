@echo off
chcp 65001 >nul
echo ========================================
echo Product Recognition AI System Setup
echo ========================================
echo.

REM Create virtual environment
echo [1/5] Creating virtual environment...
call python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo Done
echo.

REM Activate virtual environment
echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat
echo Done
echo.

REM Install backend dependencies
echo [3/5] Installing backend dependencies...
cd backend
call pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install backend packages
    cd ..
    pause
    exit /b 1
)
cd ..
echo Done
echo.

REM Install frontend dependencies
echo [4/5] Installing frontend dependencies...
cd frontend
call pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install frontend packages
    cd ..
    pause
    exit /b 1
)
cd ..
echo Done
echo.

REM Initialize product data
echo [5/5] Initializing product data...
call python init_products.py
if %errorlevel% neq 0 (
    echo WARNING: Failed to initialize product data
    echo You can run 'python init_products.py' manually later
) else (
    echo Done
)
echo.

REM Check .env file
if not exist .env (
    echo ========================================
    echo IMPORTANT: Configure .env file
    echo ========================================
    echo .env file not found.
    echo Please copy .env.example to .env and set your GEMINI_API_KEY
    echo.
    echo Steps:
    echo 1. Copy .env.example to .env
    echo 2. Open .env in a text editor
    echo 3. Replace 'your_api_key_here' with your actual API key
    echo.
    echo Get API key from:
    echo https://makersuite.google.com/app/apikey
    echo ========================================
    pause
) else (
    echo .env file found.
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Set GEMINI_API_KEY in .env file
echo 2. Run start_backend.bat to start backend
echo 3. Run start_frontend.bat to start frontend
echo.
pause
