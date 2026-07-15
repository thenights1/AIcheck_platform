@echo off
chcp 65001 >nul
echo ============================================
echo   ComplianceAudit Agent
echo ============================================
echo.

REM --- 检查 opencode CLI 是否可用 ---
where opencode >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 opencode CLI 工具。
    echo   请先安装 opencode: pip install opencode
    echo   或从 https://github.com/anomalyco/opencode 获取。
    pause
    exit /b 1
)

echo [检查] opencode CLI 已就绪

REM --- 安装依赖（首次运行）---
if not exist ".deps_installed" (
    echo [安装] 正在安装 Agent 依赖...
    pip install -r requirements.txt -q
    if %errorlevel% equ 0 (
        type nul > ".deps_installed"
        echo [完成] 依赖安装成功
    ) else (
        echo [警告] 依赖安装失败，请手动执行: pip install -r requirements.txt
    )
)

REM --- 配置服务器地址 ---
set SERVER_URL=http://localhost:8000
if not "%~1"=="" set SERVER_URL=%~1

echo.
echo   Server : %SERVER_URL%
echo   Skills : %~dp0compliance_skills\
echo.
echo [启动] Agent 正在连接...

python -m agent.main --server %SERVER_URL%

pause
