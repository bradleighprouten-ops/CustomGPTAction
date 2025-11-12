@echo off
REM Setup and test script for RAG Backend Application

echo ========================================
echo RAG Backend Application Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

echo Step 1: Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)

echo.
echo Step 2: Running system tests...
python test_setup.py
if errorlevel 1 (
    echo.
    echo WARNING: Some tests failed. Please review the errors above.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To start the application:
echo   python main.py
echo.
echo Or with uvicorn:
echo   uvicorn main:app --reload --host 0.0.0.0 --port 8000
echo.
echo Web Portal: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
pause
