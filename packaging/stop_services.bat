@echo off
REM MindVideo 停止脚本

echo ========================================
echo MindVideo 服务停止
echo ========================================
echo.

REM 停止IndexTTS服务 (端口7861)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7861"') do (
    echo 停止IndexTTS服务 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

REM 停止MindVideo应用 (端口8000)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    echo 停止MindVideo应用 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo 所有服务已停止
pause
