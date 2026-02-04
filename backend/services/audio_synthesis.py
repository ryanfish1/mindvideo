"""
音频合成服务

使用 IndexTTS、GPT-SoVITS 或 Edge TTS 生成语音
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Literal

from loguru import logger

from ..config import settings
from ..integrations.indextts_client import indextts_client
from ..integrations.sovits_client import edge_tts_client, sovits_client
from ..models import Storyboard, StoryboardScene

# TTS 引擎类型
TtsEngine = Literal["indextts", "sovits", "edge"]


class AudioSynthesisService:
    """音频合成服务"""

    def __init__(self):
        self.indextts_client = indextts_client
        self.sovits_client = sovits_client
        self.edge_tts_client = edge_tts_client
        self.max_concurrent = settings.MAX_CONCURRENT_AUDIO

    async def generate_scene_audios(
        self,
        storyboard: Storyboard,
        project_id: str,
        tts_engine: TtsEngine = "edge",
        progress_callback=None,
    ) -> list[StoryboardScene]:
        """
        为所有镜头生成音频

        Args:
            storyboard: 分镜数据
            project_id: 项目 ID
            tts_engine: TTS 引擎 ("indextts", "sovits", "edge")
            progress_callback: 进度回调函数

        Returns:
            更新后的镜头列表（包含音频路径和时长）
        """
        logger.info(f"Generating audio for {len(storyboard.scenes)} scenes (tts_engine={tts_engine})")

        # 创建项目输出目录
        project_dir = settings.PROJECTS_PATH / project_id
        audio_dir = project_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        updated_scenes = []
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # 选择 TTS 客户端
        tts_client = self._get_tts_client(tts_engine)
        file_ext = self._get_file_extension(tts_engine)

        async def generate_one(scene: StoryboardScene, index: int):
            async with semaphore:
                try:
                    output_path = audio_dir / f"audio_{scene.order:04d}.{file_ext}"

                    # 调用 TTS 生成音频
                    _, audio_path, duration = await tts_client.synthesize(
                        text=scene.narration,
                        output_path=output_path,
                    )

                    # 更新场景对象
                    scene.audio_path = audio_path

                    # 如果音频时长与预期不符，调整镜头时长
                    if duration > 0:
                        # 允许 10% 的误差范围
                        if abs(duration - scene.duration) > scene.duration * 0.1:
                            logger.info(
                                f"Scene {index}: Adjusting duration from {scene.duration}s to {duration}s "
                                f"to match audio length"
                            )
                            scene.duration = duration

                    logger.info(
                        f"Generated audio for scene {index + 1}/{len(storyboard.scenes)}: "
                        f"{audio_path} ({duration:.2f}s)"
                    )

                    # 调用进度回调
                    if progress_callback:
                        progress = (index + 1) / len(storyboard.scenes)
                        await progress_callback("audio", progress, index + 1, len(storyboard.scenes))

                    return scene

                except Exception as e:
                    logger.error(f"Failed to generate audio for scene {index}: {e}")
                    # 即使失败也返回场景对象
                    return scene

        # 并发生成音频
        tasks = [generate_one(scene, i) for i, scene in enumerate(storyboard.scenes)]
        updated_scenes = await asyncio.gather(*tasks)

        # 更新分镜
        storyboard.scenes = list(updated_scenes)
        storyboard.updated_at = datetime.now()

        # 重新计算总时长
        storyboard.calculate_duration()

        success_count = sum(1 for s in updated_scenes if s.audio_path)
        logger.info(f"Audio synthesis completed: {success_count}/{len(updated_scenes)} successful")

        return updated_scenes

    async def regenerate_scene_audio(
        self,
        scene: StoryboardScene,
        project_id: str,
        tts_engine: TtsEngine = "edge",
    ) -> tuple[StoryboardScene, float]:
        """
        重新生成单个镜头的音频

        Args:
            scene: 镜头对象
            project_id: 项目 ID
            tts_engine: TTS 引擎

        Returns:
            (更新后的镜头对象, 音频时长) 元组
        """
        project_dir = settings.PROJECTS_PATH / project_id
        audio_dir = project_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        file_ext = self._get_file_extension(tts_engine)
        output_path = audio_dir / f"audio_{scene.order:04d}_regen.{file_ext}"

        tts_client = self._get_tts_client(tts_engine)

        _, audio_path, duration = await tts_client.synthesize(
            text=scene.narration,
            output_path=output_path,
        )

        scene.audio_path = audio_path
        scene.duration = duration

        return scene, duration

    def _get_tts_client(self, tts_engine: TtsEngine):
        """根据引擎类型获取对应的 TTS 客户端"""
        if tts_engine == "indextts":
            return self.indextts_client
        elif tts_engine == "sovits":
            return self.sovits_client
        else:  # edge
            return self.edge_tts_client

    def _get_file_extension(self, tts_engine: TtsEngine) -> str:
        """根据引擎类型获取音频文件扩展名"""
        if tts_engine == "edge":
            return "mp3"
        else:  # indextts, sovits
            return "wav"

    async def sync_duration_to_audio(
        self,
        scenes: list[StoryboardScene],
    ) -> list[StoryboardScene]:
        """
        根据音频时长同步调整镜头时长

        Args:
            scenes: 镜头列表

        Returns:
            调整后的镜头列表
        """
        updated_scenes = []

        for scene in scenes:
            if scene.audio_path:
                try:
                    # 获取音频文件时长
                    audio_path = Path(scene.audio_path)
                    if audio_path.exists():
                        duration = await self._get_audio_duration(audio_path)
                        if duration > 0:
                            scene.duration = duration
                            logger.debug(f"Scene {scene.order}: Duration synced to {duration:.2f}s")
                except Exception as e:
                    logger.warning(f"Failed to get duration for scene {scene.order}: {e}")

            updated_scenes.append(scene)

        return updated_scenes

    async def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频文件时长"""
        try:
            from ffmpy import FFprobe

            probe = FFprobe(
                str(audio_path),
                global_args=["-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"],
            )
            output = probe.run(stdout_output=True)
            duration = float(output[0].strip())
            return duration
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
            return 0.0

    async def test_tts_service(self, tts_engine: TtsEngine = "edge") -> bool:
        """
        测试 TTS 服务连接

        Args:
            tts_engine: TTS 引擎

        Returns:
            连接是否成功
        """
        try:
            tts_client = self._get_tts_client(tts_engine)

            if tts_engine == "edge":
                # Edge TTS 不需要连接测试
                return True
            elif tts_engine == "indextts":
                return await self.indextts_client.test_connection()
            else:  # sovits
                return await self.sovits_client.test_connection()

        except Exception as e:
            logger.error(f"TTS service test failed: {e}")
            return False


# 全局服务实例
audio_synthesis_service = AudioSynthesisService()
