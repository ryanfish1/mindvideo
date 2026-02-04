"""
SDXL API 客户端

用于调用本地 Stable Diffusion XL WebUI API 生成图片
支持自动回退到在线 SDXL API（硅基流动）
"""

import base64
from pathlib import Path
from typing import Optional

import aiohttp
from loguru import logger

from ..config import settings


class SDXLClient:
    """
    SDXL WebUI API 客户端

    自动检测本地 SDXL WebUI 是否可用，
    如果不可用则回退到在线 API
    """

    def __init__(self):
        self.url = settings.SDXL_URL
        self.checkpoint = settings.SDXL_CHECKPOINT
        self.width = settings.SDXL_WIDTH
        self.height = settings.SDXL_HEIGHT
        self.steps = settings.SDXL_STEPS
        self.cfg_scale = settings.SDXL_CFG_SCALE
        self.sampler = settings.SDXL_SAMPLER

        # 在线 API 回退客户端
        self._online_client = None
        self._use_online = False

    def _get_online_client(self):
        """获取在线 SDXL 客户端"""
        if self._online_client is None:
            try:
                from .sdxl_online_client import online_sdxl_client
                self._online_client = online_sdxl_client
            except ImportError:
                logger.warning("Online SDXL client not available")
        return self._online_client

    async def _check_local_available(self) -> bool:
        """检查本地 SDXL 是否可用"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.url}/sdapi/v1/options",
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as response:
                    if response.status == 200:
                        logger.info("Using local SDXL WebUI")
                        return True
        except Exception:
            pass

        # 检查是否有在线 API 可用
        online_client = self._get_online_client()
        if online_client and settings.SILICONFLOW_API_KEY:
            logger.info("Local SDXL unavailable, using online SDXL API")
            self._use_online = True
            return True

        logger.error("No SDXL backend available (local or online)")
        return False

    async def _get_current_model(self) -> Optional[str]:
        """获取当前加载的模型"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/sdapi/v1/options") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("sd_model_checkpoint")
        except Exception as e:
            logger.warning(f"Failed to get current model: {e}")
        return None

    async def _set_model(self, model_name: str) -> bool:
        """设置 SDXL 模型"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"sd_model_checkpoint": model_name}
                async with session.post(f"{self.url}/sdapi/v1/options", json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Model changed to: {model_name}")
                        return True
        except Exception as e:
            logger.error(f"Failed to set model: {e}")
        return False

    async def txt2img(
        self,
        prompt: str,
        negative_prompt: str = "",
        output_path: Optional[Path] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        sampler: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """
        生成图片（txt2img）

        自动选择本地或在线 SDXL API

        Args:
            prompt: 正向提示词
            negative_prompt: 负向提示词
            output_path: 输出文件路径
            width: 图片宽度
            height: 图片高度
            steps: 采样步数
            cfg_scale: CFG 强度
            sampler: 采样器名称

        Returns:
            (图片数据, 图片路径) 元组
        """
        # 如果需要，检测使用哪个后端
        if not hasattr(self, '_backend_checked'):
            await self._check_local_available()
            self._backend_checked = True

        # 如果使用在线 API
        if self._use_online:
            online_client = self._get_online_client()
            if online_client:
                return await online_client.txt2img(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    output_path=output_path,
                    width=width or self.width,
                    height=height or self.height,
                    steps=steps or self.steps,
                    cfg_scale=cfg_scale or self.cfg_scale,
                )

        # 使用本地 SDXL WebUI
        return await self._txt2img_local(
            prompt=prompt,
            negative_prompt=negative_prompt,
            output_path=output_path,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            sampler=sampler,
        )

    async def _txt2img_local(
        self,
        prompt: str,
        negative_prompt: str = "",
        output_path: Optional[Path] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        sampler: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """使用本地 SDXL WebUI 生成图片"""
        # 检查并设置模型
        current_model = await self._get_current_model()
        if current_model and self.checkpoint not in current_model:
            logger.info(f"Switching model from {current_model} to {self.checkpoint}")
            await self._set_model(self.checkpoint)

        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt or "(worst quality, low quality:1.4), blurry, distortion, ugly, deformed",
            "width": width or self.width,
            "height": height or self.height,
            "steps": steps or self.steps,
            "cfg_scale": cfg_scale or self.cfg_scale,
            "sampler_name": sampler or self.sampler,
            "send_images": True,
            "save_images": False,
        }

        logger.debug(f"Generating image with local SDXL: {prompt[:100]}...")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.url}/sdapi/v1/txt2img",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300),  # 5 分钟超时
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Local SDXL API error: {response.status} - {error_text}")
                        # 尝试回退到在线 API
                        online_client = self._get_online_client()
                        if online_client:
                            logger.info("Falling back to online SDXL API")
                            self._use_online = True
                            return await online_client.txt2img(
                                prompt=prompt,
                                negative_prompt=negative_prompt,
                                output_path=output_path,
                                width=width or self.width,
                                height=height or self.height,
                                steps=steps or self.steps,
                                cfg_scale=cfg_scale or self.cfg_scale,
                            )
                        raise Exception(f"Local SDXL API error: {response.status}")

                    data = await response.json()

                    if not data.get("images"):
                        raise Exception("No images returned from SDXL")

                    # 解码第一张图片
                    image_data = base64.b64decode(data["images"][0])

                    # 保存到文件
                    if output_path is None:
                        output_path = settings.CACHE_PATH / f"sdxl_{id(prompt)}.png"

                    output_path = Path(output_path)
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(output_path, "wb") as f:
                        f.write(image_data)

                    logger.info(f"Image generated (local SDXL): {output_path}")
                    return image_data, str(output_path)

            except aiohttp.ClientError as e:
                logger.error(f"Local SDXL connection error: {e}")
                raise Exception(f"Failed to connect to local SDXL: {e}")
            except Exception as e:
                logger.error(f"Image generation failed: {e}")
                raise

    async def txt2img_batch(
        self,
        prompts: list[tuple[str, str]],  # (positive, negative) 列表
        output_dir: Optional[Path] = None,
        **kwargs,
    ) -> list[tuple[bytes, str]]:
        """
        批量生成图片

        Args:
            prompts: (正向提示词, 负向提示词) 列表
            output_dir: 输出目录
            **kwargs: 其他参数传递给 txt2img

        Returns:
            (图片数据, 图片路径) 列表
        """
        results = []
        output_dir = output_dir or settings.CACHE_PATH

        for i, (positive, negative) in enumerate(prompts):
            output_path = output_dir / f"scene_{i:04d}.png"
            try:
                result = await self.txt2img(positive, negative, output_path, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to generate image {i}: {e}")
                # 继续处理其他图片

        return results

    async def get_progress(self) -> dict:
        """获取当前生成进度"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/sdapi/v1/progress") as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.warning(f"Failed to get progress: {e}")
        return {"progress": 0, "eta_relative": 0}

    async def interrupt(self) -> bool:
        """中断当前生成"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.url}/sdapi/v1/interrupt") as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to interrupt: {e}")
        return False

    async def test_connection(self) -> bool:
        """
        测试 SDXL 连接

        优先测试本地 SDXL，如果不可用则测试在线 API
        """
        # 先尝试本地 SDXL
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/sdapi/v1/options", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        logger.info("Local SDXL connection test successful")
                        self._use_online = False
                        return True
        except Exception as e:
            logger.debug(f"Local SDXL unavailable: {e}")

        # 尝试在线 SDXL API
        online_client = self._get_online_client()
        if online_client and settings.SILICONFLOW_API_KEY:
            logger.info("Testing online SDXL API...")
            result = await online_client.test_connection()
            if result:
                self._use_online = True
                return True

        logger.error("No SDXL backend available")
        return False


# 全局客户端实例
sdxl_client = SDXLClient()
