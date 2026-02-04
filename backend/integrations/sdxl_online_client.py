"""
SDXL 在线 API 客户端（硅基流动备用方案）

使用 SiliconFlow API 进行 SDXL 图片生成
当本地 SDXL WebUI 不可用时使用此客户端
"""

import base64
from pathlib import Path
from typing import Optional

import aiohttp
from loguru import logger

from ..config import settings


class OnlineSDXLClient:
    """
    SiliconFlow SDXL API 客户端

    使用硅基流动的在线 SDXL API 生成图片
    """

    def __init__(self):
        self.api_key = settings.SILICONFLOW_API_KEY
        self.base_url = "https://api.siliconflow.cn/v1"
        # 使用硅基流动的 Kolors 模型（快手可图，支持中文）
        self.model = "Kwai-Kolors/Kolors"

    async def txt2img(
        self,
        prompt: str,
        negative_prompt: str = "",
        output_path: Optional[Path] = None,
        width: int = 1024,
        height: int = 1024,
        steps: int = 30,
        cfg_scale: float = 7.5,
        sampler: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """
        使用 SDXL 生成图片（txt2img）

        Args:
            prompt: 正向提示词
            negative_prompt: 负向提示词
            output_path: 输出文件路径
            width: 图片宽度
            height: 图片高度
            steps: 采样步数
            cfg_scale: CFG 强度
            sampler: 采样器名称（在线 API 通常忽略）

        Returns:
            (图片数据, 图片路径) 元组
        """
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY is not configured")

        # SiliconFlow API 格式
        payload = {
            "model": self.model,
            "prompt": prompt,
            "negative_prompt": negative_prompt or "(worst quality, low quality:1.4), blurry, distortion, ugly, deformed",
            "image_size": f"{width}x{height}",
            "num_inference_steps": steps,
            "guidance_scale": cfg_scale,
        }

        logger.debug(f"Generating image with Online SDXL: {prompt[:100]}...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/images/generations",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180),  # 3 分钟超时
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Online SDXL API error: {response.status} - {error_text}")
                        raise Exception(f"Online SDXL API error: {response.status}")

                    data = await response.json()

                    # SiliconFlow 返回 base64 图片数据
                    if "data" not in data or not data["data"]:
                        raise Exception("No images returned from Online SDXL")

                    # 获取第一张图片
                    image_b64 = data["data"][0].get("b64_json") or data["data"][0].get("url")

                    if image_b64.startswith("http"):
                        # 如果返回的是 URL，下载图片
                        async with session.get(image_b64) as img_response:
                            image_data = await img_response.read()
                    else:
                        # base64 编码的图片
                        image_data = base64.b64decode(image_b64)

                    # 保存到文件
                    if output_path is None:
                        output_path = settings.CACHE_PATH / f"sdxl_online_{id(prompt)}.png"

                    output_path = Path(output_path)
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(output_path, "wb") as f:
                        f.write(image_data)

                    logger.info(f"Image generated (Online SDXL): {output_path}")
                    return image_data, str(output_path)

            except aiohttp.ClientError as e:
                logger.error(f"Online SDXL connection error: {e}")
                raise Exception(f"Failed to connect to Online SDXL: {e}")
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

    async def test_connection(self) -> bool:
        """测试在线 SDXL 连接"""
        if not self.api_key:
            logger.warning("SILICONFLOW_API_KEY not configured")
            return False

        try:
            # 生成一个简单的测试图片
            await self.txt2img(
                prompt="test image, red circle on white background",
                output_path=settings.CACHE_PATH / "test_online_sdxl.png",
                width=512,
                height=512,
                steps=10,
            )
            logger.info("Online SDXL connection test successful")
            return True
        except Exception as e:
            logger.error(f"Online SDXL connection test failed: {e}")
            return False


# 全局在线 SDXL 客户端实例
online_sdxl_client = OnlineSDXLClient()
