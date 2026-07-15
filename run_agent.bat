@echo off
cd /d "%~dp0"

echo ============================================
echo   ComplianceAudit Agent
echo ============================================
echo.

REM --- Check Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH.
    echo   Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

echo [OK] Python detected

REM --- Check opencode CLI ---
where opencode >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] opencode CLI not found in PATH.
    echo   Agent will run in simulation mode without AI.
    echo   Install: pip install opencode
    echo.
)

REM --- Install deps (first run) ---
if not exist ".deps_installed" (
    echo [INFO] Installing Python dependencies...
    pip install -r requirements.txt -q
    if %errorlevel% equ 0 (
        type nul > ".deps_installed"
        echo [OK] Dependencies installed
    ) else (
        echo [WARN] pip install failed, please run manually:
        echo   pip install -r requirements.txt
    )
)

echo.
echo   Config  : %~dp0agent.yaml
echo   Skills  : %~dp0compliance_skills\
echo   WorkDir : %~dp0
echo.
echo [INFO] Starting Agent ...
echo.

set "PYTHONPATH=%~dp0;%PYTHONPATH%"
python -m agent.main

pause
