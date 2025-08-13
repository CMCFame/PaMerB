@echo off
REM PaMerB IVR Converter - Batch Runner
REM This batch file runs the PowerShell script to start the Streamlit app

echo Starting PaMerB IVR Converter...
echo.

REM Check if PowerShell is available
powershell -Command "Get-Host" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell not found
    echo [TIP] Please install PowerShell or use: python -m streamlit run app.py --server.port 8502
    pause
    exit /b 1
)

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0run_app.ps1" %*

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo [ERROR] Script failed. Press any key to exit...
    pause >nul
)