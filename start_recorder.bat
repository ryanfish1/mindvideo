@echo off
chcp 65001 >nul
echo ==========================================
echo           Audio Recorder
echo ==========================================
echo.
echo Starting in 3 seconds...
echo Press Ctrl+C to stop and save
echo.

python "D:\code\generation\record.py"

echo.
echo Press any key to exit...
pause >nul
