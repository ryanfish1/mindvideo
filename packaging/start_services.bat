@echo off
REM MindVideo 启动脚本
REM 自动启动IndexTTS服务和MindVideo应用

setlocal enabledelayedexpansion

echo ========================================
echo MindVideo 服务启动
echo ========================================
echo.

REM 配置路径（根据实际情况修改）
set INDEX_TTS_PATH=G:\index\index-tts-windows
set PROJECT_PATH=D:\code\generation
set INDEX_PORT=7861
set APP_PORT=8000

REM 检查IndexTTS路径
if not exist "%INDEX_TTS_PATH%\indextts_server.py" (
    echo [错误] IndexTTS路径不存在: %INDEX_TTS_PATH%
    echo 请编辑本文件修改 INDEX_TTS_PATH
    pause
    exit /b 1
)

REM 检查端口占用
netstat -ano | findstr ":%INDEX_PORT%" >nul
if !errorlevel! == 0 (
    echo [提示] IndexTTS服务已在运行 (端口 %INDEX_PORT%)
) else (
    echo [1/2] 启动IndexTTS服务...
    start "IndexTTS Server" cmd /k "cd /d %INDEX_TTS_PATH% && python indextts_server.py --port %INDEX_PORT% --host 127.0.0.1"
    echo      等待服务启动...
    timeout /t 3 >nul
)

netstat -ano | findstr ":%APP_PORT%" >nul
if !errorlevel! == 0 (
    echo [提示] MindVideo应用已在运行 (端口 %APP_PORT%)
) else (
    echo [2/2] 启动MindVideo应用...
    start "MindVideo" cmd /k "cd /d %PROJECT_PATH% && python -m uvicorn backend.main:app --host 127.0.0.1 --port %APP_PORT% --reload"
)

echo.
echo ========================================
echo 服务启动完成！
echo ========================================
echo IndexTTS API: http://127.0.0.1:%INDEX_PORT%
echo MindVideo Web: http://127.0.0.1:%APP_PORT%
echo API文档: http://127.0.0.1:%APP_PORT%/docs
echo ========================================
echo.

REM 可选：自动打开浏览器
start http://127.0.0.1:%APP_PORT%/docs

pause
