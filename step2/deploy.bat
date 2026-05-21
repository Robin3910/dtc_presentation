@echo off
REM AI 素材审核助手 · Step 2 Windows 部署脚本
REM ===========================================
REM 使用方法：
REM   deploy.bat start     启动服务
REM   deploy.bat stop      停止服务
REM   deploy.bat restart   重启服务
REM   deploy.bat status    查看状态
REM   deploy.bat install   安装依赖并启动

setlocal enabledelayedexpansion

set "SERVICE_NAME=ai-reviewer"
set "APP_DIR=%~dp0"
set "PYTHON=python"

color 0A

echo.
echo ========================================
echo   AI 素材审核助手 · Step 2 部署脚本
echo ========================================
echo.

REM 检查 Python
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 未安装或未添加到 PATH
    echo 请先安装 Python 3.8+ 并添加到系统 PATH
    pause
    exit /b 1
)

REM 进入应用目录
cd /d "%APP_DIR%"

REM 解析命令
set "COMMAND=%1"

if "%COMMAND%"=="" (
    echo 请指定操作命令：
    echo.
    echo   deploy.bat install   安装依赖并启动
    echo   deploy.bat start     启动服务
    echo   deploy.bat stop      停止服务
    echo   deploy.bat restart   重启服务
    echo   deploy.bat status    查看状态
    echo.
    set /p COMMAND="请输入命令: "
)

REM 安装依赖
if "%COMMAND%"=="install" (
    echo [INFO] 安装 Python 依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
    echo [INFO] 依赖安装完成
    echo.
)

REM 启动服务
if "%COMMAND%"=="start" (
    echo [INFO] 启动服务...
    
    REM 检查是否已运行
    tasklist /fi "windowtitle eq ai-reviewer*" 2>nul | findstr /i "python" >nul
    if not errorlevel 1 (
        echo [警告] 服务已在运行中
    ) else (
        start "ai-reviewer" /min "%PYTHON%" "%APP_DIR%app.py" --prod
        timeout /t 3 /nobreak >nul
        echo [INFO] 服务已启动
    )
    goto show_status
)

REM 停止服务
if "%COMMAND%"=="stop" (
    echo [INFO] 停止服务...
    taskkill /fi "windowtitle eq ai-reviewer*" /f >nul 2>&1
    echo [INFO] 服务已停止
    goto :eof
)

REM 重启服务
if "%COMMAND%"=="restart" (
    echo [INFO] 重启服务...
    call :stop
    timeout /t 2 /nobreak >nul
    call :start
    goto show_status
)

REM 查看状态
:show_status
echo.
echo ========================================
echo   服务状态
echo ========================================
echo.
tasklist /fi "windowtitle eq ai-reviewer*" 2>nul | findstr /i "python" >nul
if errorlevel 1 (
    echo   状态：已停止
) else (
    echo   状态：运行中
)
echo.
echo   Web 访问：    http://localhost:8080/
echo   上传页面：    http://localhost:8080/
echo   管理后台：    http://localhost:8080/admin
echo.
goto :eof

REM 帮助信息
if "%COMMAND%"=="help" (
    echo.
    echo 使用方法：
    echo   deploy.bat install   安装依赖并启动
    echo   deploy.bat start    启动服务
    echo   deploy.bat stop     停止服务
    echo   deploy.bat restart   重启服务
    echo   deploy.bat status   查看状态
    echo.
    goto :eof
)

REM 未知命令
echo [错误] 未知命令：%COMMAND%
echo 运行 deploy.bat help 查看帮助
