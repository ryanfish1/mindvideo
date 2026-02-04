"""
Ken Burns 特效引擎

使用 FFmpeg 为图片添加缓慢缩放和平移特效
"""

import asyncio
from enum import Enum
from pathlib import Path

from loguru import logger

from ..models import KenBurnsEffect


class KenBurnsEffectConfig:
    """Ken Burns 特效配置"""

    # 默认配置
    DEFAULT_FPS = 30
    DEFAULT_ZOOM_SPEED = 0.0015  # 每帧缩放增量
    DEFAULT_MAX_ZOOM = 1.5  # 最大缩放倍数
    DEFAULT_PAN_SPEED = 2.0  # 平移速度


def _build_zoompan_filter(
    effect: KenBurnsEffect,
    duration: float,
    resolution: str,
    config: KenBurnsEffectConfig,
) -> str:
    """
    构建 FFmpeg zoompan 过滤器参数

    Args:
        effect: 特效类型
        duration: 时长
        resolution: 分辨率 (WxH)
        config: 特效配置

    Returns:
        FFmpeg 过滤器字符串
    """
    width, height = resolution.lower().split("x")
    width = int(width)
    height = int(height)

    base_filter = f"scale={resolution}:force_original_aspect_ratio=decrease"

    if effect == KenBurnsEffect.ZOOM_IN:
        # 缓慢推进
        zoom_filter = (
            f"zoompan=z='min(zoom+{config.DEFAULT_ZOOM_SPEED},{config.DEFAULT_MAX_ZOOM})':"
            f"d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={resolution}:fps={config.DEFAULT_FPS}"
        )

    elif effect == KenBurnsEffect.ZOOM_OUT:
        # 缓慢拉远
        zoom_filter = (
            f"zoompan=z='max({config.DEFAULT_MAX_ZOOM}-zoom+{config.DEFAULT_ZOOM_SPEED},1.0)':"
            f"d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={resolution}:fps={config.DEFAULT_FPS}:zoom={config.DEFAULT_MAX_ZOOM}"
        )

    elif effect == KenBurnsEffect.PAN_LEFT:
        # 向左平移
        zoom_filter = (
            f"scale={width*2}:-1,"
            f"crop={resolution}:ih:{width}*0:'0'"
        )

    elif effect == KenBurnsEffect.PAN_RIGHT:
        # 向右平移
        zoom_filter = (
            f"scale={width*2}:-1,"
            f"crop={resolution}:ih:'0':'0'"
        )

    else:  # NONE
        # 无特效，静态画面
        zoom_filter = f"pad={resolution}:(ow-iw)/2:(oh-ih)/2"

    # 组合过滤器
    if effect in [KenBurnsEffect.ZOOM_IN, KenBurnsEffect.ZOOM_OUT]:
        return f"{base_filter},{zoom_filter},trim=duration={duration}"
    elif effect in [KenBurnsEffect.PAN_LEFT, KenBurnsEffect.PAN_RIGHT]:
        return f"{zoom_filter},trim=duration={duration}"
    else:
        return f"{base_filter},trim=duration={duration}"


async def generate_ken_burns(
    image_path: str,
    output_path: str,
    duration: float,
    effect: KenBurnsEffect,
    resolution: str = "2560x1440",
    fps: int = 30,
) -> str:
    """
    使用 FFmpeg 生成 Ken Burns 特效视频

    Args:
        image_path: 输入图片路径
        output_path: 输出视频路径
        duration: 视频时长（秒）
        effect: Ken Burns 特效类型
        resolution: 输出分辨率 (WxH)
        fps: 帧率

    Returns:
        输出视频路径
    """
    logger.debug(f"Generating Ken Burns video: {image_path} -> {output_path}")

    # 确保输出目录存在
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 构建过滤器
    config = KenBurnsEffectConfig()
    config.DEFAULT_FPS = fps

    vf = _build_zoompan_filter(effect, duration, resolution, config)

    # FFmpeg 命令
    cmd = [
        "ffmpeg",
        "-y",  # 覆盖输出文件
        "-loop", "1",  # 循环图片
        "-i", image_path,  # 输入图片
        "-vf", vf,  # 视频过滤器
        "-c:v", "libx264",  # 视频编码器
        "-tune", "stillimage",  # 针对静态图像优化
        "-preset", "medium",  # 编码速度/质量平衡
        "-pix_fmt", "yuv420p",  # 像素格式（兼容性）
        "-t", str(duration),  # 时长
        "-r", str(fps),  # 帧率
        str(output_path),  # 输出文件
    ]

    # 执行命令
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode()
        logger.error(f"FFmpeg Ken Burns failed: {error_msg}")
        raise Exception(f"Failed to generate Ken Burns video: {error_msg}")

    logger.info(f"Ken Burns video generated: {output_path}")
    return str(output_path)


def generate_ken_burns_sync(
    image_path: str,
    output_path: str,
    duration: float,
    effect: KenBurnsEffect,
    resolution: str = "2560x1440",
    fps: int = 30,
) -> str:
    """
    同步版本：使用 FFmpeg 生成 Ken Burns 特效视频

    Args:
        image_path: 输入图片路径
        output_path: 输出视频路径
        duration: 视频时长（秒）
        effect: Ken Burns 特效类型
        resolution: 输出分辨率 (WxH)
        fps: 帧率

    Returns:
        输出视频路径
    """
    import subprocess

    logger.debug(f"Generating Ken Burns video (sync): {image_path} -> {output_path}")

    # 确保输出目录存在
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 构建过滤器
    config = KenBurnsEffectConfig()
    config.DEFAULT_FPS = fps

    vf = _build_zoompan_filter(effect, duration, resolution, config)

    # FFmpeg 命令
    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        "-r", str(fps),
        str(output_path),
    ]

    # 执行命令
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"FFmpeg Ken Burns failed: {result.stderr}")
        raise Exception(f"Failed to generate Ken Burns video: {result.stderr}")

    logger.info(f"Ken Burns video generated: {output_path}")
    return str(output_path)


async def generate_ken_burns_batch(
    image_paths: list[tuple[str, KenBurnsEffect]],
    output_dir: Path,
    duration: float,
    resolution: str = "2560x1440",
    fps: int = 30,
) -> list[str]:
    """
    批量生成 Ken Burns 视频

    Args:
        image_paths: (图片路径, 特效类型) 列表
        output_dir: 输出目录
        duration: 时长
        resolution: 分辨率
        fps: 帧率

    Returns:
        输出视频路径列表
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = []

    for i, (image_path, effect) in enumerate(image_paths):
        output_path = output_dir / f"segment_{i:04d}.mp4"
        tasks.append(
            generate_ken_burns(
                image_path,
                str(output_path),
                duration,
                effect,
                resolution,
                fps,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 过滤成功的结果
    successful = [r for r in results if isinstance(r, str)]

    logger.info(f"Generated {len(successful)}/{len(image_paths)} Ken Burns videos")

    return successful


def suggest_effect_for_scene(
    scene_type: str,
    narration: str,
) -> KenBurnsEffect:
    """
    根据场景类型和旁白内容建议 Ken Burns 特效

    Args:
        scene_type: 场景类型
        narration: 旁白内容

    Returns:
        建议的特效类型
    """
    # 隐喻镜头用 zoom_in 强调
    if scene_type == "metaphor":
        return KenBurnsEffect.ZOOM_IN

    # 标题镜头静态
    if scene_type == "title":
        return KenBurnsEffect.NONE

    # 转场镜头用 zoom_out
    if scene_type == "transition":
        return KenBurnsEffect.ZOOM_OUT

    # 根据关键词判断
    zoom_in_keywords = ["深入", "发现", "揭示", "聚焦", "本质", "核心", "仔细"]
    zoom_out_keywords = ["全景", "整体", "宏观", "看到", "原来"]
    pan_left_keywords = ["回顾", "过去", "历史", "曾经"]
    pan_right_keywords = ["未来", "向前", "接下来", "然后"]

    for keyword in zoom_in_keywords:
        if keyword in narration:
            return KenBurnsEffect.ZOOM_IN

    for keyword in zoom_out_keywords:
        if keyword in narration:
            return KenBurnsEffect.ZOOM_OUT

    for keyword in pan_left_keywords:
        if keyword in narration:
            return KenBurnsEffect.PAN_LEFT

    for keyword in pan_right_keywords:
        if keyword in narration:
            return KenBurnsEffect.PAN_RIGHT

    # 默认使用缓慢推进
    return KenBurnsEffect.ZOOM_IN
