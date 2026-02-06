"""
AI 视频生成系统 V1.0
使用 Pexels API + IndexTTS 生成科普视频

生成流程：
1. 智能匹配视频 (Pexels API + LLM)
2. 生成 TTS 音频 (IndexTTS)
3. 处理视频片段 (精确裁剪 + 重新编码)
4. 合并音频到视频
5. 拼接最终视频

作者: AI Assistant
版本: 1.0
日期: 2026-02-06
"""
import asyncio
from pathlib import Path

from backend.services.video_matching import video_matching_service
from backend.integrations.indextts_client import indextts_client

# ============== 配置区域 ==============

# 文案（根据需要修改）
SCRIPT = '''你这辈子花的每一笔冤枉钱，其实都是你心甘情愿掏出来的。当你站在柜台前，以为自己在货比三家、理性决策时，真相是：早在你推开门之前，商家就已经通过一种名为"锚定效应"的心理诡计，在你的大脑里植入了一套预设好的剧本，锁死了你的钱包。这种机制就像在你大脑的决策系统里钉入了一根无形的钉子，而最令人毛骨悚然的是，你现在脑子里可能已经密密麻麻钉了十几根，却一根都没察觉。我们总以为自己是自由意志的主人，是那个手握方向盘的司机，但现实往往残酷得令人发笑——我们不过是坐在副驾驶上，盯着假的方向盘自嗨，而真正的驾驶权，早就被那个率先抛出数字的人悄悄接管了。'''

# TTS 配置
TTS_EMOTION = "neutral"   # 情感: neutral, clean, happy, sad, angry
TTS_SPEED = 1.25         # 语速倍率
TTS_VOLUME = 1.5         # 音量倍率

# 输出配置
CACHE_DIR = Path("D:/code/generation/storage/cache")
OUTPUT_DIR = Path("D:/code/generation/storage/output")

# ========================================


def get_storyboard():
    """分镜定义 - 根据文案修改场景分段

    每个场景包含：
    - narration: 旁白文案
    - keyword_hint: 关键词提示（帮助 AI 搜索匹配视频）
    - duration: 预期时长（秒）
    """
    return {
        "scenes": [
            {
                "narration": "你这辈子花的每一笔冤枉钱，其实都是你心甘情愿掏出来的。",
                "keyword_hint": "消费 支付 钱包 后悔",
                "duration": 5.0
            },
            {
                "narration": "当你站在柜台前，以为自己在货比三家、理性决策时，",
                "keyword_hint": "购物 商店 柜台 选择",
                "duration": 5.0
            },
            {
                "narration": "真相是：早在你推开门之前，",
                "keyword_hint": "商店门 进入 商场",
                "duration": 3.5
            },
            {
                "narration": "商家就已经通过一种名为锚定效应的心理诡计，",
                "keyword_hint": "价格标签 销售 促销 锚定",
                "duration": 5.0
            },
            {
                "narration": "在你的大脑里植入了一套预设好的剧本，锁死了你的钱包。",
                "keyword_hint": "大脑 操控 影响 洗脑",
                "duration": 5.0
            },
            {
                "narration": "这种机制就像在你大脑的决策系统里钉入了一根无形的钉子，",
                "keyword_hint": "钉子 隐喻 陷阱 锚定",
                "duration": 5.0
            },
            {
                "narration": "而最令人毛骨悚然的是，",
                "keyword_hint": "恐惧 惊悚 阴影 不安",
                "duration": 3.0
            },
            {
                "narration": "你现在脑子里可能已经密密麻麻钉了十几根，却一根都没察觉。",
                "keyword_hint": "困惑 不知 无意识 钉子",
                "duration": 5.0
            },
            {
                "narration": "我们总以为自己是自由意志的主人，是那个手握方向盘的司机，",
                "keyword_hint": "驾驶 方向盘 掌控 自由",
                "duration": 6.0
            },
            {
                "narration": "但现实往往残酷得令人发笑——",
                "keyword_hint": "讽刺 嘲笑 残酷",
                "duration": 3.5
            },
            {
                "narration": "我们不过是坐在副驾驶上，盯着假的方向盘自嗨，",
                "keyword_hint": "假象 欺骗 副驾驶 自欺",
                "duration": 5.0
            },
            {
                "narration": "而真正的驾驶权，早就被那个率先抛出数字的人悄悄接管了。",
                "keyword_hint": "操控 数据 键盘 数字 掌控",
                "duration": 6.0
            }
        ]
    }


async def generate_audio_with_indextts(text, index):
    """使用 IndexTTS 生成音频"""
    output_path = CACHE_DIR / f"audio_{index:03d}.wav"

    _, audio_path, duration = await indextts_client.synthesize(
        text=text,
        output_path=output_path,
        emotion=TTS_EMOTION,
        speed=TTS_SPEED,
        volume=TTS_VOLUME,
    )

    print(f"  Audio {index+1}: {duration:.2f}s")
    return str(audio_path), duration


async def process_video_segment(raw_path, audio_duration, index):
    """
    处理视频片段：
    1. 精确裁剪到音频长度
    2. 重新编码避免卡顿
    """
    output_path = CACHE_DIR / f"segment_{index:03d}.mp4"

    # 精确裁剪并重新编码（避免卡顿）
    cmd = [
        "ffmpeg", "-y", "-i", str(raw_path),
        "-t", str(audio_duration),  # 精确裁剪到音频长度
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",  # 重新编码保证质量
        "-r", "30",  # 统一帧率
        "-an",  # 移除原始音频
        str(output_path)
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    return str(output_path) if process.returncode == 0 else None


async def merge_audio_to_video(video_path, audio_path, index):
    """
    将音频精确合并到视频
    使用 -shortest 确保最终长度匹配音频
    """
    output_path = CACHE_DIR / f"final_{index:03d}.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",  # 视频直接复制（已重新编码过）
        "-c:a", "aac", "-b:a", "192k",  # 音频编码
        "-shortest",  # 关键：使用最短流的长度
        str(output_path)
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(CACHE_DIR)
    )
    await process.communicate()

    return str(output_path) if process.returncode == 0 else None


async def concat_videos(video_paths, output_path):
    """拼接视频"""
    concat_file = CACHE_DIR / "concat_list.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        for path in video_paths:
            f.write(f"file '{path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path)
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    return process.returncode == 0


async def main():
    """主生成流程"""
    print("=" * 60)
    print("AI 视频生成系统 V1.0")
    print(f"Emotion: {TTS_EMOTION}, Speed: {TTS_SPEED}x, Volume: {TTS_VOLUME}x")
    print("=" * 60)

    # 创建目录
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    storyboard = get_storyboard()
    total_scenes = len(storyboard['scenes'])

    # 1. 智能匹配视频
    print(f"\n[1/4] 智能匹配视频 ({total_scenes} 个场景)...")
    video_matches = []
    for i, scene in enumerate(storyboard['scenes']):
        print(f"\n  场景 {i+1}: {scene['narration'][:30]}...")

        # 使用关键词提示改进匹配
        match = await video_matching_service.find_best_match(
            narration=f"{scene['narration']} {scene['keyword_hint']}",  # 添加关键词提示
            text_overlay="",
            preferred_duration=scene['duration'],
            max_attempts=3
        )

        if match:
            video_matches.append(match)
            print(f"    [OK] {match.width}x{match.height}")
        else:
            print(f"    [FAIL] 未找到匹配")

        await asyncio.sleep(1)

    if len(video_matches) != total_scenes:
        print(f"\n[警告] 只匹配到 {len(video_matches)}/{total_scenes} 个视频")

    # 2. 生成音频
    print(f"\n[2/4] 生成 TTS 音频 (IndexTTS)...")
    audio_data = []
    for i, scene in enumerate(storyboard['scenes']):
        if i < len(video_matches):
            audio_path, duration = await generate_audio_with_indextts(scene['narration'], i)
            audio_data.append((audio_path, duration))

    # 3. 处理视频片段
    print(f"\n[3/4] 处理视频片段 (精确裁剪 + 重新编码)...")
    segment_paths = []
    for i, (match, (audio_path, audio_duration)) in enumerate(zip(video_matches, audio_data)):
        # 先下载原始视频
        raw_path = CACHE_DIR / f"raw_{i:03d}.mp4"
        success = await video_matching_service.download_video(match, str(raw_path))

        if success:
            segment_path = await process_video_segment(str(raw_path), audio_duration, i)
            if segment_path:
                segment_paths.append(segment_path)

    # 4. 合并音频
    print(f"\n[4/4] 合并音频到视频...")
    final_paths = []
    for i, (segment_path, (audio_path, _)) in enumerate(zip(segment_paths, audio_data)):
        final_path = await merge_audio_to_video(segment_path, audio_path, i)
        if final_path:
            final_paths.append(final_path)

    # 5. 拼接
    print(f"\n[5/5] 拼接最终视频...")
    timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
    final_output = OUTPUT_DIR / f"video_v1.0_{timestamp}.mp4"
    success = await concat_videos(final_paths, str(final_output))

    if success:
        print("\n" + "=" * 60)
        print("生成完成!")
        print(f"输出文件: {final_output}")

        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(final_output)],
            capture_output=True, text=True
        )
        print(f"视频时长: {result.stdout.strip()}s")
        print(f"场景数量: {len(final_paths)}")
        print("=" * 60)
    else:
        print("\n[FAIL] 拼接失败")


if __name__ == "__main__":
    asyncio.run(main())
