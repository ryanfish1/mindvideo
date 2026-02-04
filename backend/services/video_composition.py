"""
视频合成服务

使用 FFmpeg 合成最终视频
"""

import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

from loguru import logger

from ..config import settings
from ..engines.ken_burns import generate_ken_burns
from ..engines.subtitle_renderer import render_subtitles
from ..models import Storyboard, StoryboardScene


class VideoCompositionService:
    """视频合成服务"""

    def __init__(self):
        self.resolution = settings.OUTPUT_RESOLUTION
        self.fps = settings.FPS
        self.codec = settings.VIDEO_CODEC
        self.preset = settings.VIDEO_PRESET
        self.crf = settings.VIDEO_CRF

    async def compose_final_video(
        self,
        storyboard: Storyboard,
        project_id: str,
        enable_subtitles: bool = True,
        progress_callback=None,
    ) -> str:
        """
        合成最终视频

        Args:
            storyboard: 分镜数据
            project_id: 项目 ID
            enable_subtitles: 是否启用字幕
            progress_callback: 进度回调函数

        Returns:
            输出视频路径
        """
        logger.info(f"Composing final video for project {project_id}")

        # 创建项目输出目录
        project_dir = settings.PROJECTS_PATH / project_id
        output_dir = settings.OUTPUT_PATH
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成所有视频片段
        video_segments = await self._generate_video_segments(
            storyboard,
            project_dir,
            progress_callback,
        )

        if not video_segments:
            raise Exception("No video segments were generated")

        # 拼接视频
        final_output = output_dir / f"{project_id}_final.mp4"

        await self._concat_videos(video_segments, final_output)

        # 添加字幕
        if enable_subtitles:
            subtitle_output = output_dir / f"{project_id}_final_subtitled.mp4"
            await render_subtitles(str(final_output), storyboard, str(subtitle_output))
            final_output = subtitle_output

        logger.info(f"Final video composed: {final_output}")

        # 调用最终进度回调
        if progress_callback:
            await progress_callback("composing", 1.0, len(storyboard.scenes), len(storyboard.scenes))

        return str(final_output)

    async def _generate_video_segments(
        self,
        storyboard: Storyboard,
        project_dir: Path,
        progress_callback=None,
    ) -> list[Path]:
        """
        生成所有视频片段（图片 + Ken Burns + 音频）

        Args:
            storyboard: 分镜数据
            project_dir: 项目目录
            progress_callback: 进度回调

        Returns:
            视频片段路径列表
        """
        segments_dir = project_dir / "segments"
        segments_dir.mkdir(parents=True, exist_ok=True)

        video_segments = []
        tasks = []

        async def generate_segment(scene: StoryboardScene, index: int):
            try:
                # 生成 Ken Burns 视频
                segment_path = segments_dir / f"segment_{scene.order:04d}.mp4"

                if not scene.image_path:
                    logger.warning(f"Scene {index}: No image path, skipping")
                    return None

                # 生成 Ken Burns 特效视频
                await generate_ken_burns(
                    image_path=scene.image_path,
                    output_path=str(segment_path),
                    duration=scene.duration,
                    effect=scene.ken_burns,
                    resolution=self.resolution,
                )

                # 如果有音频，合并到视频
                if scene.audio_path:
                    audio_output = segments_dir / f"segment_{scene.order:04d}_with_audio.mp4"
                    await self._add_audio_to_video(
                        str(segment_path),
                        scene.audio_path,
                        str(audio_output),
                    )
                    segment_path = audio_output

                # 更新场景的视频路径
                scene.video_path = str(segment_path)

                logger.info(
                    f"Generated segment {index + 1}/{len(storyboard.scenes)}: {segment_path.name}"
                )

                # 调用进度回调
                if progress_callback:
                    progress = (index + 1) / len(storyboard.scenes)
                    await progress_callback("video", progress, index + 1, len(storyboard.scenes))

                return segment_path

            except Exception as e:
                logger.error(f"Failed to generate segment {index}: {e}")
                return None

        # 并发生成视频片段
        for i, scene in enumerate(storyboard.scenes):
            tasks.append(generate_segment(scene, i))

        results = await asyncio.gather(*tasks)

        # 过滤成功生成的片段
        video_segments = [r for r in results if r is not None]

        logger.info(f"Generated {len(video_segments)}/{len(storyboard.scenes)} video segments")

        return video_segments

    async def _add_audio_to_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
    ) -> None:
        """
        将音频添加到视频

        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg audio add failed: {stderr.decode()}")
            raise Exception(f"Failed to add audio: {stderr.decode()}")

    async def _concat_videos(
        self,
        video_segments: list[Path],
        output_path: Path,
    ) -> None:
        """
        拼接视频片段

        Args:
            video_segments: 视频片段路径列表
            output_path: 输出文件路径
        """
        if not video_segments:
            raise Exception("No video segments to concat")

        # 创建拼接列表文件
        concat_list_path = output_path.parent / "concat_list.txt"
        with open(concat_list_path, "w") as f:
            for segment in video_segments:
                f.write(f"file '{segment.absolute()}'\n")

        # 使用 ffmpeg concat demuxer 拼接
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_path),
            "-c", "copy",
            str(output_path),
        ]

        logger.info(f"Concatenating {len(video_segments)} segments...")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg concat failed: {stderr.decode()}")
            raise Exception(f"Failed to concat videos: {stderr.decode()}")

        # 清理拼接列表文件
        concat_list_path.unlink()

        logger.info(f"Video concat completed: {output_path}")

    async def add_background_music(
        self,
        video_path: str,
        music_path: str,
        output_path: str,
        music_volume: float = 0.3,
    ) -> None:
        """
        添加背景音乐

        Args:
            video_path: 视频文件路径
            music_path: 音乐文件路径
            output_path: 输出文件路径
            music_volume: 音乐音量 (0.0 - 1.0)
        """
        # 使用 ffmpeg 的 amix filter 混合音频
        audio_filter = f"[1:a]volume={music_volume}[music];[0:a][music]amix=inputs=2:duration=first"

        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex", audio_filter,
            "-c:v", "copy",
            "-c:a", "aac",
            output_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg background music failed: {stderr.decode()}")
            raise Exception(f"Failed to add background music: {stderr.decode()}")

    async def optimize_video(
        self,
        input_path: str,
        output_path: str,
        target_size_mb: float | None = None,
    ) -> None:
        """
        优化视频大小

        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            target_size_mb: 目标文件大小（MB），如果为 None 则使用默认 CRF
        """
        if target_size_mb:
            # 计算需要的比特率
            # bitrate = (target_size * 8) / duration (kbps)
            # 首先获取视频时长
            probe_cmd = [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                input_path,
            ]

            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip())

            bitrate = int((target_size_mb * 8 * 1024) / duration)
            cmd = [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-c:v", self.codec,
                "-b:v", f"{bitrate}k",
                "-c:a", "aac",
                "-b:a", "128k",
                output_path,
            ]
        else:
            # 使用 CRF 模式
            cmd = [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-c:v", self.codec,
                "-preset", self.preset,
                "-crf", str(self.crf),
                "-c:a", "aac",
                "-b:a", "128k",
                output_path,
            ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg optimize failed: {stderr.decode()}")
            raise Exception(f"Failed to optimize video: {stderr.decode()}")


# 全局服务实例
video_composition_service = VideoCompositionService()
