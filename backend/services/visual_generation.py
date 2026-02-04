"""
视觉生成服务

使用 SDXL 生成分镜图片
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger

from ..config import settings
from ..integrations.sdxl_client import sdxl_client
from ..models import Storyboard, StoryboardScene


class VisualGenerationService:
    """视觉生成服务"""

    def __init__(self):
        self.client = sdxl_client
        self.max_concurrent = settings.MAX_CONCURRENT_IMAGES

    async def generate_scene_images(
        self,
        storyboard: Storyboard,
        project_id: str,
        progress_callback=None,
    ) -> list[StoryboardScene]:
        """
        为所有镜头生成图片

        Args:
            storyboard: 分镜数据
            project_id: 项目 ID
            progress_callback: 进度回调函数

        Returns:
            更新后的镜头列表（包含图片路径）
        """
        logger.info(f"Generating images for {len(storyboard.scenes)} scenes")

        # 创建项目输出目录
        project_dir = settings.PROJECTS_PATH / project_id
        images_dir = project_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        updated_scenes = []
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def generate_one(scene: StoryboardScene, index: int):
            async with semaphore:
                try:
                    output_path = images_dir / f"scene_{scene.order:04d}.png"

                    # 调用 SDXL 生成图片
                    _, image_path = await self.client.txt2img(
                        prompt=scene.visual_prompt,
                        negative_prompt=scene.negative_prompt,
                        output_path=output_path,
                    )

                    # 更新场景对象
                    scene.image_path = image_path

                    logger.info(f"Generated image for scene {index + 1}/{len(storyboard.scenes)}: {image_path}")

                    # 调用进度回调
                    if progress_callback:
                        progress = (index + 1) / len(storyboard.scenes)
                        await progress_callback("images", progress, index + 1, len(storyboard.scenes))

                    return scene

                except Exception as e:
                    logger.error(f"Failed to generate image for scene {index}: {e}")
                    # 即使失败也返回场景对象
                    return scene

        # 并发生成图片
        tasks = [generate_one(scene, i) for i, scene in enumerate(storyboard.scenes)]
        updated_scenes = await asyncio.gather(*tasks)

        # 更新分镜
        storyboard.scenes = list(updated_scenes)
        storyboard.updated_at = datetime.now()

        success_count = sum(1 for s in updated_scenes if s.image_path)
        logger.info(f"Image generation completed: {success_count}/{len(updated_scenes)} successful")

        return updated_scenes

    async def regenerate_scene_image(
        self,
        scene: StoryboardScene,
        project_id: str,
        new_prompt: str | None = None,
    ) -> StoryboardScene:
        """
        重新生成单个镜头的图片

        Args:
            scene: 镜头对象
            project_id: 项目 ID
            new_prompt: 新的提示词（可选）

        Returns:
            更新后的镜头对象
        """
        project_dir = settings.PROJECTS_PATH / project_id
        images_dir = project_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        output_path = images_dir / f"scene_{scene.order:04d}_regen.png"

        # 使用新提示词或原有提示词
        prompt = new_prompt if new_prompt else scene.visual_prompt

        _, image_path = await self.client.txt2img(
            prompt=prompt,
            negative_prompt=scene.negative_prompt,
            output_path=output_path,
        )

        scene.image_path = image_path
        return scene

    async def batch_generate_by_type(
        self,
        scenes: list[StoryboardScene],
        scene_type: str,
        project_id: str,
    ) -> list[StoryboardScene]:
        """
        按类型批量生成图片

        Args:
            scenes: 镜头列表
            scene_type: 要生成的镜头类型
            project_id: 项目 ID

        Returns:
            更新后的镜头列表
        """
        filtered_scenes = [s for s in scenes if s.scene_type.value == scene_type]

        if not filtered_scenes:
            logger.info(f"No scenes of type '{scene_type}' to generate")
            return scenes

        logger.info(f"Generating {len(filtered_scenes)} images for type '{scene_type}'")

        project_dir = settings.PROJECTS_PATH / project_id
        images_dir = project_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # 创建临时分镜用于批量生成
        temp_storyboard = Storyboard(
            id=str(uuid.uuid4()),
            project_id=project_id,
            scenes=filtered_scenes,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        await self.generate_scene_images(temp_storyboard, project_id)

        # 更新原场景列表
        scene_map = {s.order: s for s in filtered_scenes}
        for i, scene in enumerate(scenes):
            if scene.order in scene_map:
                scenes[i] = scene_map[scene.order]

        return scenes


# 全局服务实例
visual_generation_service = VisualGenerationService()
