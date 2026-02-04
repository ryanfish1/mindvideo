"""
MindVideo 打包配置
使用 PyInstaller 将应用打包为单个exe，IndexTTS模型作为外部依赖
"""
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent

# PyInstaller 配置
PYINSTALLER_SPEC = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['backend/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 包含配置文件
        ('backend/config.py', 'backend'),
        ('.env', '.'),
    ],
    hiddenimports=[
        'uvicorn',
        'fastapi',
        'aiohttp',
        'httpx',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MindVideo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
"""


def build_installer():
    """生成安装程序脚本"""
    setup_script = '''@echo off
echo ========================================
echo MindVideo 安装程序
echo ========================================

echo.
echo 1. 检查IndexTTS模型路径...
set /p INDEX_PATH="请输入IndexTTS模型目录路径 (例如: G:\\index\\index-tts-windows): "
if not exist "%INDEX_PATH%\\checkpoints" (
    echo [错误] 找不到模型文件，请检查路径
    pause
    exit /b 1
)

echo.
echo 2. 配置环境变量...
echo INDEX_TTS_PATH=%INDEX_PATH% >> .env

echo.
echo 3. 启动IndexTTS服务...
cd /d "%INDEX_PATH%"
start "IndexTTS Server" python indextts_server.py --port 7861

echo.
echo 4. 等待服务启动...
timeout /t 5

echo.
echo 5. 启动MindVideo应用...
cd /d "%~dp0"
start "MindVideo" MindVideo.exe

echo.
echo 安装完成！
echo IndexTTS服务: http://localhost:7861
echo MindVideo服务: http://localhost:8000
pause
'''

    with open(ROOT / "dist" / "install.bat", "w") as f:
        f.write(setup_script)

    print("安装程序生成: dist/install.bat")


def main():
    print("MindVideo 打包工具")
    print("=" * 50)
    print()
    print("打包方案：")
    print("1. 应用程序打包为单个exe")
    print("2. IndexTTS模型作为外部依赖（用户指定路径）")
    print()

    choice = input("是否开始打包？(y/n): ")
    if choice.lower() != 'y':
        return

    print()
    print("执行 PyInstaller 打包...")
    print()

    # 生成 .spec 文件
    spec_file = ROOT / "MindVideo.spec"
    with open(spec_file, "w") as f:
        f.write(PYINSTALLER_SPEC)

    # 执行打包
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_file), "--clean"],
        cwd=ROOT,
    )

    if result.returncode == 0:
        print()
        print("打包成功！")
        print(f"输出目录: {ROOT / 'dist'}")
        build_installer()
    else:
        print("打包失败，请检查错误信息")


if __name__ == "__main__":
    main()
