"""
生成锚定效应认知科普视频 - V1.0配置
"""
import asyncio
from pathlib import Path

from backend.services.video_matching import video_matching_service
from backend.integrations.indextts_client import indextts_client

# 文案
SCRIPT = '''你这辈子花的每一笔冤枉钱，其实都是你心甘情愿掏出来的。当你站在柜台前，以为自己在货比三家、理性决策时，真相是：早在你推开门之前，商家就已经通过一种名为"锚定效应"的心理诡计，在你的大脑里植入了一套预设好的剧本，锁死了你的钱包。这种机制就像在你大脑的决策系统里钉入了一根无形的钉子，而最令人毛骨悚然的是，你现在脑子里可能已经密密麻麻钉了十几根，却一根都没察觉。我们总以为自己是自由意志的主人，是那个手握方向盘的司机，但现实往往残酷得令人发笑——我们不过是坐在副驾驶上，盯着假的方向盘自嗨，而真正的驾驶权，早就被那个率先抛出数字的人悄悄接管了。'''

CACHE_DIR = Path("D:/code/generation/storage/cache")

# V1.0 配置
TTS_EMOTION = "neutral"  # 中性平静
TTS_SPEED = 1.25        # 快25%
TTS_VOLUME = 1.5        # 大50%


def get_storyboard():
    """分镜定义"""
    return {
        "scenes": [
            {
                "narration": "你这辈子花的每一笔冤枉钱，其实都是你心甘情愿掏出来的。",
                "duration": 5.0
            },
            {
                "narration": "当你站在柜台前，以为自己在货比三家、理性决策时，",
                "duration": 5.0
            },
            {
                "narration": "真相是：早在你推开门之前，",
                "duration": 3.5
            },
            {
                "narration": "商家就已经通过一种名为锚定效应的心理诡计，",
                "duration": 5.0
            },
            {
                "narration": "在你的大脑里植入了一套预设好的剧本，锁死了你的钱包。",
                "duration": 5.0
            },
            {
                "narration": "这种机制就像在你大脑的决策系统里钉入了一根无形的钉子，",
                "duration": 5.0
            },
            {
                "narration": "而最令人毛骨悚然的是，",
                "duration": 3.0
            },
            {
                "narration": "你现在脑子里可能已经密密麻麻钉了十几根，却一根都没察觉。",
                "duration": 5.0
            },
            {
                "narration": "我们总以为自己是自由意志的主人，是那个手握方向盘的司机，",
                "duration": 6.0
            },
            {
                "narration": "但现实往往残酷得令人发笑——",
                "duration": 3.5
            },
            {
                "narration": "我们不过是坐在副驾驶上，盯着假的方向盘自嗨，",
                "duration": 5.0
            },
            {
                "narration": "而真正的驾驶权，早就被那个率先抛出数字的人悄悄接管了。",
                "duration": 6.0
            }
        ]
    }


async def generate_audio_with_indextts(text, index):
    """使用 IndexTTS 生成音频 - V1.0配置"""
    output_path = CACHE_DIR / f"anchoring_audio_{index:03d}.wav"

    _, audio_path, duration = await indextts_client.synthesize(
        text=text,
        output_path=output_path,
        emotion=TTS_EMOTION,
        speed=TTS_SPEED,
        volume=TTS_VOLUME,
    )

    print(f"  Audio {index+1}: {duration:.2f}s")
    return str(audio_path), duration


async def process_video_segment(match, duration, index):
    """处理视频片段"""
    input_path = CACHE_DIR / f"anchoring_raw_{index:03d}.mp4"
    output_path = CACHE_DIR / f"anchoring_segment_{index:03d}.mp4"

    # 下载视频
    success = await video_matching_service.download_video(match, str(input_path))
    if not success:
        return None

    # 裁剪视频到音频长度
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast",
        "-an",
        str(output_path)
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    return str(output_path)


async def merge_audio_to_video(video_path, audio_path, index):
    """将音频合并到视频（无字幕）"""
    output_path = CACHE_DIR / f"anchoring_final_{index:03d}.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_path)
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(CACHE_DIR)
    )
    await process.communicate()

    return str(output_path)


async def concat_videos(video_paths, output_path):
    """拼接视频"""
    list_path = CACHE_DIR / "anchoring_concat_list.txt"
    with open(list_path, 'w') as f:
        for path in video_paths:
            f.write(f"file '{path}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_path),
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac",
        str(output_path)
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    return str(output_path)


async def main():
    print("=" * 60)
    print("Anchoring Effect Video - V1.0 Config")
    print(f"Emotion: {TTS_EMOTION}, Speed: {TTS_SPEED}x, Volume: {TTS_VOLUME}x")
    print("=" * 60)

    storyboard = get_storyboard()
    total_scenes = len(storyboard['scenes'])

    # 1. 智能匹配视频
    print(f"\n[1/4] Smart matching videos ({total_scenes} scenes)...")
    video_matches = []
    for i, scene in enumerate(storyboard['scenes']):
        print(f"\n  Scene {i+1}: {scene['narration'][:40]}...")
        match = await video_matching_service.find_best_match(
            narration=scene['narration'],
            text_overlay="",
            preferred_duration=scene['duration'],
            max_attempts=3
        )

        if match:
            video_matches.append(match)
        else:
            print(f"    [X] No match found for scene {i+1}")

        await asyncio.sleep(1)

    if len(video_matches) != total_scenes:
        print(f"\nWarning: Only {len(video_matches)}/{total_scenes} videos matched")

    # 2. 生成音频
    print(f"\n[2/4] Generating audio with IndexTTS...")
    audio_data = []
    for i, scene in enumerate(storyboard['scenes']):
        if i < len(video_matches):
            audio_path, duration = await generate_audio_with_indextts(scene['narration'], i)
            audio_data.append((audio_path, duration))

    # 3. 处理视频片段
    print(f"\n[3/4] Processing video segments...")
    segment_paths = []
    for i, (match, (audio_path, audio_duration)) in enumerate(zip(video_matches, audio_data)):
        segment_path = await process_video_segment(match, audio_duration, i)
        if segment_path:
            segment_paths.append(segment_path)

    # 4. 合并音频
    print(f"\n[4/4] Merging audio to video...")
    final_paths = []
    for i, (segment_path, (audio_path, _)) in enumerate(zip(segment_paths, audio_data)):
        final_path = await merge_audio_to_video(segment_path, audio_path, i)
        final_paths.append(final_path)

    # 5. 拼接
    print(f"\n[5/5] Concatenating final video...")
    output_dir = Path("D:/code/generation/storage/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    final_output = output_dir / "anchoring_effect_v1.0.mp4"
    await concat_videos(final_paths, str(final_output))

    print("\n" + "=" * 60)
    print("Done!")
    print(f"Output: {final_output}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
