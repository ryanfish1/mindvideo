"""
字幕渲染引擎

使用 FFmpeg 为视频添加硬字幕
"""

import asyncio
import re
import tempfile
from pathlib import Path

from loguru import logger

from ..models import Storyboard


class SubtitleStyle:
    """字幕样式配置"""

    # Mindmart 字幕风格
    DEFAULT_FONT = "Arial"
    DEFAULT_FONT_SIZE = 48
    DEFAULT_FONT_COLOR = "&HFFFFFF"  # 白色
    DEFAULT_OUTLINE_COLOR = "&H000000"  # 黑色边框
    DEFAULT_OUTLINE_WIDTH = 2
    DEFAULT_ALIGNMENT = 2  # 底部居中
    DEFAULT_MARGIN_V = 60  # 底部边距

    # 字幕位置（从底部算起）
    POSITION_BOTTOM = 60
    POSITION_MIDDLE = 0


def _seconds_to_srt_time(seconds: float) -> str:
    """
    将秒数转换为 SRT 时间格式

    Args:
        seconds: 秒数

    Returns:
        SRT 时间格式 (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _clean_text_for_subtitle(text: str) -> str:
    """
    清理文本以用于字幕显示

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    # 移除过长的句子
    if len(text) > 30:
        # 尝试在标点处分割
        parts = re.split(r'[，。！？、；：]', text)
        if len(parts) > 1:
            # 取最重要的两部分
            text = parts[0] + "，" + parts[1]

    # 移除特殊字符
    text = re.sub(r'[\*\[\]]', '', text)

    return text.strip()


def generate_srt_content(storyboard: Storyboard) -> str:
    """
    生成分镜的 SRT 字幕内容

    Args:
        storyboard: 分镜数据

    Returns:
        SRT 格式的字幕内容
    """
    srt_lines = []
    current_time = 0.0

    for i, scene in enumerate(storyboard.scenes):
        if not scene.narration:
            continue

        start_time = current_time
        end_time = current_time + scene.duration

        # 清理文本
        subtitle_text = _clean_text_for_subtitle(scene.narration)

        srt_lines.append(str(i + 1))
        srt_lines.append(f"{_seconds_to_srt_time(start_time)} --> {_seconds_to_srt_time(end_time)}")
        srt_lines.append(subtitle_text)
        srt_lines.append("")  # 空行

        current_time = end_time

    return "\n".join(srt_lines)


def generate_ass_content(storyboard: Storyboard, style: SubtitleStyle = None) -> str:
    """
    生成分镜的 ASS 字幕内容

    Args:
        storyboard: 分镜数据
        style: 字幕样式配置

    Returns:
        ASS 格式的字幕内容
    """
    if style is None:
        style = SubtitleStyle()

    # ASS 文件头
    ass_lines = [
        "[Script Info]",
        "Title: MindVideo Subtitle",
        "ScriptType: v4.00+",
        "",
        "[V4+ Styles]",
        f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{style.DEFAULT_FONT},{style.DEFAULT_FONT_SIZE},{style.DEFAULT_FONT_COLOR},{style.DEFAULT_FONT_COLOR},{style.DEFAULT_OUTLINE_COLOR},&H00000000,0,0,0,0,100,100,0,0,1,{style.DEFAULT_OUTLINE_WIDTH},0,{style.DEFAULT_ALIGNMENT},0,0,{style.DEFAULT_MARGIN_V},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    current_time = 0.0

    for scene in storyboard.scenes:
        if not scene.narration:
            continue

        start_time = current_time
        end_time = current_time + scene.duration

        # ASS 时间格式 (H:MM:SS.CC)
        start_ass = _seconds_to_ass_time(start_time)
        end_ass = _seconds_to_ass_time(end_time)

        # 清理文本
        subtitle_text = _clean_text_for_subtitle(scene.narration)

        ass_lines.append(
            f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{subtitle_text}"
        )

        current_time = end_time

    return "\n".join(ass_lines)


def _seconds_to_ass_time(seconds: float) -> str:
    """
    将秒数转换为 ASS 时间格式

    Args:
        seconds: 秒数

    Returns:
        ASS 时间格式 (H:MM:SS.CC)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


async def render_subtitles(
    video_path: str,
    storyboard: Storyboard,
    output_path: str,
    subtitle_format: str = "ass",
    style: SubtitleStyle = None,
) -> str:
    """
    为视频添加字幕

    Args:
        video_path: 输入视频路径
        storyboard: 分镜数据
        output_path: 输出视频路径
        subtitle_format: 字幕格式 (ass/srt)
        style: 字幕样式

    Returns:
        输出视频路径
    """
    logger.info(f"Rendering subtitles to video: {output_path}")

    # 确保输出目录存在
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 生成字幕文件
    if subtitle_format == "ass":
        subtitle_content = generate_ass_content(storyboard, style)
        subtitle_suffix = ".ass"
    else:
        subtitle_content = generate_srt_content(storyboard)
        subtitle_suffix = ".srt"

    # 创建临时字幕文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=subtitle_suffix, delete=False, encoding="utf-8") as f:
        f.write(subtitle_content)
        subtitle_file = f.name

    try:
        # FFmpeg 命令
        if subtitle_format == "ass":
            # ASS 格式使用 subtitles 过滤器
            vf = f"subtitles={subtitle_file}"
        else:
            # SRT 格式
            vf = f"subtitles={subtitle_file}"

        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vf", vf,
            "-c:a", "copy",  # 音频直接复制
            str(output_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()
            logger.error(f"FFmpeg subtitle render failed: {error_msg}")
            raise Exception(f"Failed to render subtitles: {error_msg}")

        logger.info(f"Subtitles rendered successfully: {output_path}")
        return str(output_path)

    finally:
        # 清理临时文件
        try:
            Path(subtitle_file).unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup subtitle file: {e}")


def render_subtitles_sync(
    video_path: str,
    storyboard: Storyboard,
    output_path: str,
    subtitle_format: str = "ass",
    style: SubtitleStyle = None,
) -> str:
    """
    同步版本：为视频添加字幕

    Args:
        video_path: 输入视频路径
        storyboard: 分镜数据
        output_path: 输出视频路径
        subtitle_format: 字幕格式 (ass/srt)
        style: 字幕样式

    Returns:
        输出视频路径
    """
    import subprocess

    logger.info(f"Rendering subtitles to video (sync): {output_path}")

    # 确保输出目录存在
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 生成字幕文件
    if subtitle_format == "ass":
        subtitle_content = generate_ass_content(storyboard, style)
        subtitle_suffix = ".ass"
    else:
        subtitle_content = generate_srt_content(storyboard)
        subtitle_suffix = ".srt"

    # 创建临时字幕文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=subtitle_suffix, delete=False, encoding="utf-8") as f:
        f.write(subtitle_content)
        subtitle_file = f.name

    try:
        # FFmpeg 命令
        if subtitle_format == "ass":
            vf = f"subtitles={subtitle_file}"
        else:
            vf = f"subtitles={subtitle_file}"

        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vf", vf,
            "-c:a", "copy",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"FFmpeg subtitle render failed: {result.stderr}")
            raise Exception(f"Failed to render subtitles: {result.stderr}")

        logger.info(f"Subtitles rendered successfully: {output_path}")
        return str(output_path)

    finally:
        # 清理临时文件
        try:
            Path(subtitle_file).unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup subtitle file: {e}")
