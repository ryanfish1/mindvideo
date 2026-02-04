"""
视频生成工作流

协调各个服务完成完整的视频生成流程
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger

from ..config import settings
from ..models import GenerationTask, Project, ProjectStatus, Storyboard, TaskStage
from ..repositories.project_repo import project_repo
from ..repositories.task_repo import task_repo
from .audio_synthesis import audio_synthesis_service
from .script_analysis import script_analysis_service
from .video_composition import video_composition_service
from .visual_generation import visual_generation_service


class VideoGenerationWorkflow:
    """视频生成工作流"""

    def __init__(self):
        self.script_analysis = script_analysis_service
        self.visual_generation = visual_generation_service
        self.audio_synthesis = audio_synthesis_service
        self.video_composition = video_composition_service

    async def execute(
        self,
        project_id: str,
        use_sovits: bool = False,
        enable_subtitles: bool = True,
        progress_callback=None,
    ) -> str:
        """
        执行完整的视频生成流程

        Args:
            project_id: 项目 ID
            use_sovits: 是否使用 GPT-SoVITS（否则使用 Edge TTS）
            enable_subtitles: 是否启用字幕
            progress_callback: 进度回调函数

        Returns:
            输出视频路径
        """
        # 获取项目
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise Exception(f"Project not found: {project_id}")

        # 创建任务
        task = GenerationTask(
            id=str(uuid.uuid4()),
            project_id=project_id,
            stage=TaskStage.ANALYZING,
            progress=0.0,
            total_scenes=0,
            message="开始生成视频...",
        )
        task = await task_repo.create(task)

        try:
            # 如果没有分镜，先分析脚本
            if not project.storyboard:
                logger.info(f"Analyzing script for project {project_id}")
                await self._update_task_progress(task, TaskStage.ANALYZING, 0.0, "分析文案中...")

                storyboard = await self.script_analysis.analyze_script(project.script, project_id)
                project = await project_repo.update_storyboard(project_id, storyboard)
                task.total_scenes = len(storyboard.scenes)
                await task_repo.update(task)
            else:
                # 使用现有分镜
                storyboard = project.storyboard
                task.total_scenes = len(storyboard.scenes)
                await task_repo.update(task)

            if not storyboard or not storyboard.scenes:
                raise Exception("No scenes in storyboard")

            # 阶段 1: 生成图片
            logger.info(f"Generating images for {len(storyboard.scenes)} scenes")
            await self._update_task_progress(task, TaskStage.IMAGES, 0.0, "生成图片中...")

            async def image_progress_callback(stage, progress, current, total):
                await self._update_task_progress(
                    task,
                    TaskStage.IMAGES,
                    0.1 + progress * 0.3,  # 图片阶段占 30%
                    f"生成图片 {current}/{total}",
                    current,
                )
                if progress_callback:
                    await progress_callback(stage, progress, current, total)

            storyboard.scenes = await self.visual_generation.generate_scene_images(
                storyboard,
                project_id,
                image_progress_callback,
            )

            # 保存更新后的分镜
            project.storyboard = storyboard
            await project_repo.update(project)

            # 阶段 2: 生成音频
            logger.info("Generating audio")
            await self._update_task_progress(task, TaskStage.AUDIO, 0.4, "生成语音中...")

            async def audio_progress_callback(stage, progress, current, total):
                await self._update_task_progress(
                    task,
                    TaskStage.AUDIO,
                    0.4 + progress * 0.2,  # 音频阶段占 20%
                    f"生成语音 {current}/{total}",
                    current,
                )
                if progress_callback:
                    await progress_callback(stage, progress, current, total)

            storyboard.scenes = await self.audio_synthesis.generate_scene_audios(
                storyboard,
                project_id,
                use_sovits,
                audio_progress_callback,
            )

            # 保存更新后的分镜
            project.storyboard = storyboard
            await project_repo.update(project)

            # 阶段 3: 生成视频片段
            logger.info("Generating video segments")
            await self._update_task_progress(task, TaskStage.VIDEO, 0.6, "渲染视频片段...")

            async def video_progress_callback(stage, progress, current, total):
                await self._update_task_progress(
                    task,
                    TaskStage.VIDEO,
                    0.6 + progress * 0.3,  # 视频阶段占 30%
                    f"渲染片段 {current}/{total}",
                    current,
                )
                if progress_callback:
                    await progress_callback(stage, progress, current, total)

            output_path = await self.video_composition.compose_final_video(
                storyboard,
                project_id,
                enable_subtitles,
                video_progress_callback,
            )

            # 阶段 4: 完成
            await self._update_task_progress(task, TaskStage.DONE, 1.0, "视频生成完成!")

            # 更新项目状态
            await project_repo.set_video_output(project_id, output_path)

            logger.info(f"Video generation completed: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            await self._update_task_progress(
                task,
                TaskStage.COMPOSING,
                task.progress,
                f"生成失败: {str(e)}",
                error=str(e),
            )
            await project_repo.update_status(project_id, ProjectStatus.FAILED, str(e))
            raise

    async def _update_task_progress(
        self,
        task: GenerationTask,
        stage: TaskStage,
        progress: float,
        message: str,
        current_scene: int = None,
        error: str = None,
    ):
        """更新任务进度"""
        task.stage = stage
        task.progress = progress
        task.message = message
        if current_scene is not None:
            task.current_scene = current_scene
        if error is not None:
            task.error = error

        await task_repo.update(task)

        # 记录日志
        logger.info(f"Task {task.id}: {stage.value} - {progress:.1%} - {message}")

    async def get_task_status(self, task_id: str) -> dict:
        """获取任务状态"""
        task = await task_repo.get_by_id(task_id)
        if not task:
            return None

        return {
            "task_id": task.id,
            "project_id": task.project_id,
            "stage": task.stage.value,
            "progress": task.progress,
            "message": task.message,
            "current_scene": task.current_scene,
            "total_scenes": task.total_scenes,
            "error": task.error,
        }


# 全局工作流实例
video_generation_workflow = VideoGenerationWorkflow()
