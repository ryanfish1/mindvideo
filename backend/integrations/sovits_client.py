"""
GPT-SoVITS API 客户端

支持两种模式:
1. Gradio WebUI (本地部署)
2. REST API (api_v2.py)
"""

import asyncio
from pathlib import Path
from typing import Optional

import aiohttp
from loguru import logger

from ..config import settings


class GPTSoVITSClient:
    """GPT-SoVITS API 客户端"""

    def __init__(self):
        self.url = settings.SOVITS_URL
        self.model = settings.SOVITS_MODEL
        # 参考音频路径（用于零样本推理）
        self.reference_audio = settings.SOVITS_REFERENCE_AUDIO
        self.use_gradio = False  # 使用 REST API (api_v2.py)

    async def synthesize(
        self,
        text: str,
        output_path: Optional[Path] = None,
        speaker: str = "default",
        language: str = "zh",
    ) -> tuple[bytes, str, float]:
        """
        语音合成

        Args:
            text: 待合成的文本
            output_path: 输出文件路径
            speaker: 说话人 ID (Gradio 模式忽略)
            language: 语言代码

        Returns:
            (音频数据, 文件路径, 时长秒数) 元组
        """
        logger.debug(f"Synthesizing audio with GPT-SoVITS: {text[:50]}...")

        if self.use_gradio:
            return await self._synthesize_gradio(text, output_path)
        else:
            return await self._synthesize_api(text, output_path, speaker, language)

    async def _synthesize_gradio(
        self,
        text: str,
        output_path: Optional[Path] = None,
    ) -> tuple[bytes, str, float]:
        """
        使用 Gradio WebUI 进行语音合成

        Args:
            text: 待合成的文本
            output_path: 输出文件路径

        Returns:
            (音频数据, 文件路径, 时长秒数) 元组
        """
        try:
            from gradio_client import Client

            # 连接到 Gradio WebUI
            client = Client(self.url)

            # 调用推理函数
            # 函数名可能需要根据实际 WebUI 调整
            result = client.predict(
                text,                    # 输入文本
                self.reference_audio,    # 参考音频路径
                "zh",                    # 参考音频语言
                "",                      # 参考文本（可选）
                "zh",                    # 目标语言
                api_name="/infer_tts"    # API 名称（可能需要调整）
            )

            # result 通常是生成的音频文件路径或音频数据
            if isinstance(result, (list, tuple)) and len(result) > 0:
                audio_result = result[0]
            else:
                audio_result = result

            # 如果返回的是文件路径
            if isinstance(audio_result, str) and Path(audio_result).exists():
                audio_path = Path(audio_result)
                with open(audio_path, "rb") as f:
                    audio_data = f.read()

                duration = await self._get_audio_duration(audio_path)
                logger.info(f"Gradio TTS audio: {audio_path}, duration: {duration:.2f}s")
                return audio_data, str(audio_path), duration

            # 如果返回的是音频数据
            elif isinstance(audio_result, bytes):
                if output_path is None:
                    output_path = settings.CACHE_PATH / f"sovits_{id(text)}.wav"

                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "wb") as f:
                    f.write(audio_result)

                duration = await self._get_audio_duration(output_path)
                logger.info(f"Gradio TTS audio saved: {output_path}, duration: {duration:.2f}s")
                return audio_result, str(output_path), duration

            else:
                raise Exception(f"Unexpected result type: {type(audio_result)}")

        except ImportError:
            logger.warning("gradio_client not available, falling back to API mode")
            self.use_gradio = False
            return await self._synthesize_api(text, output_path, "default", "zh")

        except Exception as e:
            logger.error(f"Gradio TTS synthesis failed: {e}")
            # 回退到 Edge TTS
            raise

    async def _synthesize_api(
        self,
        text: str,
        output_path: Optional[Path] = None,
        speaker: str = "default",
        language: str = "zh",
    ) -> tuple[bytes, str, float]:
        """
        使用 REST API 进行语音合成 (api_v2.py)

        Args:
            text: 待合成的文本
            output_path: 输出文件路径
            speaker: 说话人 ID (ignored for zero-shot)
            language: 语言代码

        Returns:
            (音频数据, 文件路径, 时长秒数) 元组
        """
        # GPT-SoVITS API v2 格式
        payload = {
            "text": text,
            "text_lang": language,
            "ref_audio_path": self.reference_audio,
            "prompt_lang": language,
            "prompt_text": "",  # 可选
            "text_split_method": "cut5",
            "media_type": "wav",
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.url}/tts",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GPT-SoVITS API error: {response.status} - {error_text}")
                        raise Exception(f"GPT-SoVITS API error: {response.status}")

                    # 返回音频数据流
                    audio_data = await response.read()

                    # 保存到文件
                    if output_path is None:
                        output_path = settings.CACHE_PATH / f"sovits_{id(text)}.wav"

                    output_path = Path(output_path)
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(output_path, "wb") as f:
                        f.write(audio_data)

                    # 计算音频时长
                    duration = await self._get_audio_duration(output_path)

                    logger.info(f"API TTS audio saved: {output_path}, duration: {duration:.2f}s")
                    return audio_data, str(output_path), duration

            except aiohttp.ClientError as e:
                logger.error(f"GPT-SoVITS connection error: {e}")
                raise Exception(f"Failed to connect to GPT-SoVITS: {e}")

    async def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频时长"""
        try:
            from ffmpy import FFprobe

            probe = FFprobe(
                str(audio_path),
                args="-show_entries format=duration -v quiet -of csv=p=0"
            )
            output = probe.run(stdout_output=True)
            duration = float(output[0].strip())
            return duration
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
            # 默认估算：中文约 3-4 字/秒
            return 3.0

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
        """测试 GPT-SoVITS 连接"""
        try:
            if self.use_gradio:
                from gradio_client import Client
                client = Client(self.url)
                # 尝试连接即可
                logger.info(f"Gradio WebUI connection test successful: {self.url}")
                return True
            else:
                # For REST API, try to connect to the port
                # Any response (including 404) means the server is running
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.url}/",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as response:
                        # Accept any response that isn't a connection error
                        logger.info("GPT-SoVITS API connection test successful")
                        return True
        except Exception as e:
            logger.error(f"GPT-SoVITS connection test failed: {e}")
        return False


# 全局客户端实例
sovits_client = GPTSoVITSClient()


class EdgeTTSClient:
    """
    Edge TTS 客户端（备用）

    当 GPT-SoVITS 不可用时使用 Microsoft Edge TTS
    """

    def __init__(self):
        self.voice = settings.EDGE_TTS_VOICE
        self.rate = settings.EDGE_TTS_RATE
        self.volume = settings.EDGE_TTS_VOLUME

    async def synthesize(
        self,
        text: str,
        output_path: Optional[Path] = None,
    ) -> tuple[bytes, str, float]:
        """
        使用 Edge TTS 合成语音

        Args:
            text: 待合成的文本
            output_path: 输出文件路径

        Returns:
            (音频数据, 文件路径, 时长) 元组
        """
        import edge_tts

        logger.debug(f"Synthesizing with Edge TTS: {text[:50]}...")

        if output_path is None:
            output_path = settings.CACHE_PATH / f"edge_tts_{id(text)}.mp3"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            communicate = edge_tts.Communicate(
                text,
                self.voice,
                rate=self.rate,
                volume=self.volume,
            )

            await communicate.save(str(output_path))

            # 获取时长
            duration = await self._get_audio_duration(output_path)

            with open(output_path, "rb") as f:
                audio_data = f.read()

            logger.info(f"Edge TTS audio saved: {output_path}, duration: {duration:.2f}s")
            return audio_data, str(output_path), duration

        except Exception as e:
            logger.error(f"Edge TTS synthesis failed: {e}")
            raise

    async def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频时长"""
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
            return 3.0  # 默认 3 秒

    async def synthesize_batch(
        self,
        texts: list[str],
        output_dir: Optional[Path] = None,
        max_concurrent: int = 4,
    ) -> list[tuple[bytes, str, float]]:
        """批量合成"""
        results = []
        output_dir = output_dir or settings.CACHE_PATH

        semaphore = asyncio.Semaphore(max_concurrent)

        async def synthesize_one(i: int, text: str):
            async with semaphore:
                output_path = output_dir / f"audio_{i:04d}.mp3"
                try:
                    return await self.synthesize(text, output_path)
                except Exception as e:
                    logger.error(f"Failed to synthesize audio {i}: {e}")
                    return b"", "", 0.0

        tasks = [synthesize_one(i, text) for i, text in enumerate(texts)]
        results = await asyncio.gather(*tasks)

        return results


# 全局 Edge TTS 客户端实例
edge_tts_client = EdgeTTSClient()
