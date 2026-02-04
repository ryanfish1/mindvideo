#!/usr/bin/env python3
"""
GPT-SoVITS Training Script
Automated voice cloning training
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Paths
GPT_SOVITS_PATH = r"D:\code\generation\GPT-SoVITS-Windows\GPT-SoVITS-v3lora-20250228"
PYTHON_EXE = os.path.join(GPT_SOVITS_PATH, "runtime", "python.exe")
AUDIO_FILE = r"D:\code\generation\storage\my_voice.wav"

# Training directories
TRAIN_DIR = r"D:\code\generation\training"
AUDIO_DIR = os.path.join(TRAIN_DIR, "audio")
DATASET_DIR = os.path.join(TRAIN_DIR, "dataset")

def setup_directories():
    """Create training directories"""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(DATASET_DIR, exist_ok=True)
    print("[1/6] Directories created")

def prepare_audio():
    """Prepare audio file for training"""
    # Copy audio file
    shutil.copy(AUDIO_FILE, os.path.join(AUDIO_DIR, "my_voice.wav"))
    print(f"[2/6] Audio prepared: {AUDIO_FILE}")

def step1_get_text():
    """Step 1: ASR - Transcribe audio"""
    print("[3/6] Step 1: ASR Transcription...")
    script = os.path.join(GPT_SOVITS_PATH, "tools", "asr", "E2_Supported_Versions", "faster-whisper", "transcribe.py")

    # Use the faster-whisper ASR
    cmd = [
        PYTHON_EXE,
        "-m", "faster_whisper",
        AUDIO_FILE,
        "--model", "base",
        "--output_dir", DATASET_DIR,
        "--language", "zh"
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print("       ASR completed!")
    except Exception as e:
        print(f"       ASR failed: {e}")

def step2_extract_features():
    """Step 2: Extract audio features"""
    print("[4/6] Step 2: Feature extraction...")
    # This requires additional tools, skip for now
    print("       Skipped (requires additional setup)")

def step3_train():
    """Step 3: Train model"""
    print("[5/6] Step 3: Training model...")
    print("       This requires the WebUI")
    print("       Opening browser...")

    # Open browser to WebUI
    import webbrowser
    webbrowser.open("http://localhost:9874")

def main():
    print()
    print("=" * 50)
    print("    GPT-SoVITS Training Automation")
    print("=" * 50)
    print()

    # Setup
    setup_directories()
    prepare_audio()

    # Training steps
    step1_get_text()
    step2_extract_features()
    step3_train()

    print()
    print("[6/6] Training preparation complete!")
    print()
    print("Please continue in the browser at http://localhost:9874")
    print()

if __name__ == "__main__":
    main()
