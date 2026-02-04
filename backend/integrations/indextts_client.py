"""
IndexTTS API Client

连接到 IndexTTS HTTP 服务 (运行在 127.0.0.1:7861)
"""

import asyncio
from pathlib import Path
from typing import Optional

import aiohttp
from loguru import logger

from ..config import settings


class IndexTTSClient:
    """IndexTTS API Client (HTTP 服务)"""

    def __init__(self):
        self.url = settings.INDEXTTS_URL
        self.reference_audio = settings.INDEXTTS_REFERENCE_AUDIO

    async def synthesize(
        self,
        text: str,
        output_path: Optional[Path] = None,
        reference_audio: Optional[str] = None,
        emotion: Optional[str] = None,
        speed: float = 1.0,
        volume: float = 1.0,
    ) -> tuple[bytes, str, float]:
        """
        语音合成

        Args:
            text: 待合成的文本
            output_path: 输出文件路径
            reference_audio: 参考音频路径（音色）
            emotion: 情感控制 (可选: "clean", "neutral", "happy", "sad", "angry")
            speed: 语速调整 (1.0 = 正常, 1.2 = 快20%, 0.8 = 慢20%)
            volume: 音量调整 (1.0 = 正常, 1.5 = 大50%, 2.0 = 大100%)

        Returns:
            (音频数据, 文件路径, 时长秒数) 元组
        """
        logger.debug(f"Synthesizing with IndexTTS: {text[:50]}...")

        if output_path is None:
            output_path = settings.CACHE_PATH / f"indextts_{id(text)}.wav"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用参考音频
        ref_audio = reference_audio or self.reference_audio

        # 确定是否需要后处理
        needs_postprocess = speed != 1.0 or volume != 1.0
        temp_path = None
        if needs_postprocess:
            temp_path = output_path.parent / f"{output_path.stem}_temp.wav"

        try:
            async with aiohttp.ClientSession() as session:
                # 调用 TTS API
                payload = {
                    "text": text,
                    "reference_audio": ref_audio,
                    "emotion": emotion or "neutral"  # 默认使用 neutral (中性平静)
                }

                async with session.post(
                    f"{self.url}/tts",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"IndexTTS API error: {response.status} - {error_text}")
                        raise Exception(f"IndexTTS API error: {response.status}")

                    result = await response.json()
                    remote_audio_path = result.get("audio_path")
                    duration = result.get("duration", 0.0)

                    if not remote_audio_path:
                        raise Exception("No audio path in response")

                    # 下载音频文件
                    filename = Path(remote_audio_path).name
                    audio_url = f"{self.url}/audio/{filename}"

                    async with session.get(audio_url) as audio_response:
                        if audio_response.status != 200:
                            raise Exception(f"Failed to download audio: {audio_response.status}")

                        audio_data = await audio_response.read()

                        # 保存到临时路径或最终路径
                        save_path = temp_path if needs_postprocess else output_path
                        with open(save_path, "wb") as f:
                            f.write(audio_data)

                        # 如果需要调整语速或音量，使用 FFmpeg 后处理
                        if needs_postprocess:
                            await self._apply_audio_effects(
                                str(save_path),
                                str(output_path),
                                speed,
                                volume
                            )
                            # 删除临时文件
                            save_path.unlink(missing_ok=True)

                        # 重新计算时长（语速调整后会改变）
                        if speed != 1.0:
                            duration = duration / speed

                        logger.info(
                            f"IndexTTS synthesis successful: {output_path}, "
                            f"duration: {duration:.2f}s (speed={speed}, volume={volume})"
                        )

                        return audio_data, str(output_path), duration

        except Exception as e:
            logger.error(f"IndexTTS synthesis failed: {e}")
            raise

    async def _apply_audio_effects(
        self,
        input_path: str,
        output_path: str,
        speed: float,
        volume: float,
    ):
        """使用 FFmpeg 应用语速和音量效果"""
        import asyncio

        # 构建滤镜链
        filters = []

        # 语速调整 (atempo)
        if speed != 1.0:
            # atempo 只支持 0.5 到 2.0，如果超出范围需要串联多个
            if speed < 0.5 or speed > 2.0:
                # 将速度分解为多个 atempo
                filters.extend(self._get_atempo_filters(speed))
            else:
                filters.append(f"atempo={speed}")

        # 音量调整
        if volume != 1.0:
            filters.append(f"volume={volume}")

        if not filters:
            # 不需要任何效果，直接复制
            import shutil
            shutil.copy(input_path, output_path)
            return

        filter_complex = ",".join(filters)

        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-af", filter_complex,
            output_path
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg audio effects failed: {stderr.decode()}")
            raise Exception(f"Failed to apply audio effects: {stderr.decode()}")

    def _get_atempo_filters(self, speed: float) -> list[str]:
        """将速度分解为多个 atempo 滤镜"""
        filters = []
        remaining = speed

        # atempo 的范围是 0.5 到 2.0
        while remaining < 0.5 or remaining > 2.0:
            if remaining > 2.0:
                filters.append("atempo=2.0")
                remaining /= 2.0
            elif remaining < 0.5:
                filters.append("atempo=0.5")
                remaining /= 0.5

        if remaining != 1.0:
            filters.append(f"atempo={remaining}")

        return filters

    async def synthesize_batch(
        self,
        texts: list[str],
        output_dir: Optional[Path] = None,
        max_concurrent: int = 4,
        **kwargs,
    ) -> list[tuple[bytes, str, float]]:
        """批量语音合成"""
        results = []
        output_dir = output_dir or settings.CACHE_PATH

        semaphore = asyncio.Semaphore(max_concurrent)

        async def synthesize_one(i: int, text: str):
            async with semaphore:
                output_path = output_dir / f"audio_{i:04d}.wav"
                try:
                    return await self.synthesize(text, output_path, **kwargs)
                except Exception as e:
                    logger.error(f"Failed to synthesize audio {i}: {e}")
                    return b"", "", 0.0

        tasks = [synthesize_one(i, text) for i, text in enumerate(texts)]
        results = await asyncio.gather(*tasks)

        return results

    async def test_connection(self) -> bool:
        """测试 IndexTTS 连接"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.url}/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "healthy":
                            logger.info(f"IndexTTS connection test successful: {self.url}")
                            return True
        except Exception as e:
            logger.error(f"IndexTTS connection test failed: {e}")
        return False


# 全局客户端实例
indextts_client = IndexTTSClient()
