"""
MindVideo 后端测试脚本

用于验证各模块功能是否正常
"""

import asyncio
import sys
from pathlib import Path

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from integrations.deepseek_client import deepseek_client
from integrations.sdxl_client import sdxl_client
from integrations.sovits_client import edge_tts_client


async def test_config():
    """测试配置加载"""
    print("=== 测试配置加载 ===")
    print(f"存储路径: {settings.STORAGE_PATH}")
    print(f"输出分辨率: {settings.OUTPUT_RESOLUTION}")
    print(f"SDXL URL: {settings.SDXL_URL}")
    print(f"DeepSeek URL: {settings.DEEPSEEK_BASE_URL}")
    print("✓ 配置加载成功\n")


async def test_deepseek():
    """测试 DeepSeek API"""
    print("=== 测试 DeepSeek API ===")

    if not settings.DEEPSEEK_API_KEY:
        print("⚠ 跳过: DEEPSEEK_API_KEY 未配置\n")
        return

    try:
        result = await deepseek_client.test_connection()
        if result:
            print("✓ DeepSeek API 连接成功\n")
        else:
            print("✗ DeepSeek API 连接失败\n")
    except Exception as e:
        print(f"✗ DeepSeek API 测试失败: {e}\n")


async def test_sdxl():
    """测试 SDXL 连接"""
    print("=== 测试 SDXL WebUI ===")

    try:
        result = await sdxl_client.test_connection()
        if result:
            print("✓ SDXL WebUI 连接成功")
        else:
            print("✗ SDXL WebUI 连接失败")
    except Exception as e:
        print(f"✗ SDXL 测试失败: {e}")

    # 测试图片生成（如果连接成功）
    try:
        print("测试生成图片...")
        output_path = settings.CACHE_PATH / "test_sdxl.png"

        _, image_path = await sdxl_client.txt2img(
            prompt="cinematic lighting, film grain, a simple red apple on black background",
            negative_prompt="blurry, ugly",
            output_path=output_path,
            width=512,
            height=512,
            steps=10,
        )

        print(f"✓ 图片生成成功: {image_path}\n")
    except Exception as e:
        print(f"✗ 图片生成失败: {e}\n")


async def test_edge_tts():
    """测试 Edge TTS"""
    print("=== 测试 Edge TTS ===")

    try:
        output_path = settings.CACHE_PATH / "test_tts.mp3"

        audio_data, audio_path, duration = await edge_tts_client.synthesize(
            text="这是一个测试语音合成。",
            output_path=output_path,
        )

        print(f"✓ 语音合成成功: {audio_path}, 时长: {duration:.2f}秒\n")
    except Exception as e:
        print(f"✗ 语音合成失败: {e}\n")


async def test_prompt_engine():
    """测试提示词引擎"""
    print("=== 测试提示词引擎 ===")

    try:
        from services.prompt_engine import build_visual_prompt, suggest_ken_burns_effect

        narration = "大脑像一台精密的机器，时刻在欺骗我们的感知。"

        positive, negative = build_visual_prompt(narration, "metaphor")
        effect = suggest_ken_burns_effect(narration, "metaphor")

        print(f"旁白: {narration}")
        print(f"正向提示词: {positive[:100]}...")
        print(f"负向提示词: {negative[:100]}...")
        print(f"建议特效: {effect}")
        print("✓ 提示词引擎正常\n")
    except Exception as e:
        print(f"✗ 提示词引擎测试失败: {e}\n")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("MindVideo 后端测试")
    print("=" * 50 + "\n")

    await test_config()
    await test_prompt_engine()
    await test_deepseek()
    await test_sdxl()
    await test_edge_tts()

    print("=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
