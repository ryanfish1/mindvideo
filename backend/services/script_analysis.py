"""
脚本分析服务

使用 DeepSeek API 分析用户文案，生成分镜数据
"""

import json
import uuid
from datetime import datetime

from loguru import logger

from ..config import settings
from ..integrations.deepseek_client import deepseek_client
from ..models import KenBurnsEffect, SceneType, Storyboard, StoryboardScene


class ScriptAnalysisService:
    """脚本分析服务"""

    def __init__(self):
        self.client = deepseek_client
        self.default_duration = settings.DEFAULT_SCENE_DURATION

    async def analyze_script(self, script: str, project_id: str) -> Storyboard:
        """
        分析文案，生成分镜

        Args:
            script: 用户输入的文案
            project_id: 项目 ID

        Returns:
            生成的分镜数据
        """
        logger.info(f"Analyzing script for project {project_id}")

        try:
            # 调用 DeepSeek API
            result = await self.client.analyze_script(script)

            # 解析返回的场景数据
            scenes_data = result.get("scenes", [])

            if not scenes_data:
                raise Exception("No scenes returned from script analysis")

            # 构建 StoryboardScene 对象列表
            scenes = []
            for i, scene_data in enumerate(scenes_data):
                # 解析 Ken Burns 特效
                ken_burns_str = scene_data.get("ken_burns", "zoom_in")
                try:
                    ken_burns = KenBurnsEffect(ken_burns_str)
                except ValueError:
                    ken_burns = KenBurnsEffect.ZOOM_IN

                # 解析场景类型
                scene_type_str = scene_data.get("scene_type", "narration")
                try:
                    scene_type = SceneType(scene_type_str)
                except ValueError:
                    scene_type = SceneType.NARRATION

                # 获取或生成提示词
                narration = scene_data.get("narration", "")
                visual_prompt = scene_data.get("visual_prompt", "")

                # 如果没有提供视觉提示词，使用默认
                if not visual_prompt:
                    from ..services.prompt_engine import build_visual_prompt

                    visual_prompt, _ = build_visual_prompt(narration, scene_type.value)

                scene = StoryboardScene(
                    id=str(uuid.uuid4()),
                    narration=narration,
                    visual_prompt=visual_prompt,
                    scene_type=scene_type,
                    duration=float(scene_data.get("duration", self.default_duration)),
                    ken_burns=ken_burns,
                    order=i,
                )
                scenes.append(scene)

            # 创建分镜
            storyboard = Storyboard(
                id=str(uuid.uuid4()),
                project_id=project_id,
                scenes=scenes,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # 计算总时长
            storyboard.calculate_duration()

            logger.info(
                f"Script analysis completed: {len(scenes)} scenes, "
                f"total duration: {storyboard.total_duration:.2f}s"
            )

            return storyboard

        except Exception as e:
            logger.error(f"Script analysis failed: {e}")
            raise

    async def refine_scene_prompt(
        self,
        scene: StoryboardScene,
        context: str,
    ) -> tuple[str, str]:
        """
        为单个镜头优化 SDXL 提示词

        Args:
            scene: 镜头对象
            context: 场景上下文

        Returns:
            (positive_prompt, negative_prompt) 元组
        """
        try:
            return await self.client.generate_visual_prompt(
                scene.narration,
                context,
            )
        except Exception as e:
            logger.warning(f"Failed to refine prompt, using default: {e}")
            from ..services.prompt_engine import build_visual_prompt

            return build_visual_prompt(scene.narration, scene.scene_type.value)

    async def analyze_and_split_scenes(
        self,
        script: str,
        target_duration: float = settings.TARGET_VIDEO_DURATION,
    ) -> list[dict]:
        """
        分析文案并拆分镜头

        Args:
            script: 用户文案
            target_duration: 目标视频时长

        Returns:
            镜头数据字典列表
        """
        # 计算需要的镜头数
        avg_scene_duration = self.default_duration
        target_scene_count = int(target_duration / avg_scene_duration)

        logger.info(f"Target: {target_duration}s video, ~{target_scene_count} scenes")

        # 使用完整的 analyze_script 方法
        storyboard = await self.analyze_script(script, "temp")

        # 如果镜头数不足，尝试拆分长镜头
        scenes = storyboard.scenes
        if len(scenes) < target_scene_count // 2:
            logger.warning(f"Scene count ({len(scenes)}) is too low, consider splitting long scenes")

        return [scene.model_dump() for scene in scenes]


# 全局服务实例
script_analysis_service = ScriptAnalysisService()
