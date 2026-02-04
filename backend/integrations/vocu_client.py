"""
Vocu.ai TTS Client

API Base URL: https://api.apifox.cn
API Key: sk-c962b937525ae0dc601ade4b8c9f0710
"""

import asyncio
from pathlib import Path
from typing import Optional

import aiohttp
from loguru import logger

from ..config import settings


class VocuAIClient:
    """Vocu.ai TTS Client"""

    def __init__(self):
        # API configuration
        self.api_key = "sk-c962b937525ae0dc601ade4b8c9f0710"
        self.base_url = "https://api.apifox.cn"
        # Try different endpoint paths
        self.endpoints = [
            "/v1/tts",
            "/v1/synthesize",
            "/vocu/v1/tts",
            "/tts",
            "/synthesize",
        ]
        self.voice = "default"

    async def synthesize(
        self,
        text: str,
        output_path: Optional[Path] = None,
        voice: Optional[str] = None,
    ) -> tuple[bytes, str, float]:
        """
        Synthesize speech using Vocu.ai API

        Args:
            text: Text to synthesize
            output_path: Output file path
            voice: Voice ID

        Returns:
            (audio_data, file_path, duration) tuple
        """
        logger.debug(f"Synthesizing with Vocu.ai: {text[:50]}...")

        if output_path is None:
            output_path = settings.CACHE_PATH / f"vocu_{id(text)}.mp3"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Try different request formats
        # Format 1: Standard TTS
        payload_1 = {
            "text": text,
            "voice": voice or self.voice,
        }

        # Format 2: With model
        payload_2 = {
            "model": "tts-1",
            "input": text,
            "voice": voice or self.voice,
        }

        # Format 3: Vocu specific
        payload_3 = {
            "content": text,
            "voice_id": voice or self.voice,
        }

        payloads = [payload_1, payload_2, payload_3]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for endpoint in self.endpoints:
            url = self.base_url + endpoint

            for i, payload in enumerate(payloads):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            url,
                            headers=headers,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=30),
                        ) as response:
                            logger.debug(f"Request: {url} (format {i+1})")

                            if response.status == 200:
                                content_type = response.headers.get('content-type', '')

                                # Check if audio response
                                if 'audio' in content_type or 'mpeg' in content_type or 'wav' in content_type:
                                    audio_data = await response.read()

                                    with open(output_path, "wb") as f:
                                        f.write(audio_data)

                                    duration = await self._get_audio_duration(output_path)

                                    logger.info(
                                        f"Vocu.ai synthesis successful! "
                                        f"Endpoint: {endpoint}, Format: {i+1}"
                                    )
                                    return audio_data, str(output_path), duration

                                # Check if JSON with audio URL
                                elif 'application/json' in content_type:
                                    data = await response.json()
                                    if isinstance(data, dict):
                                        # Look for audio URL
                                        audio_url = data.get('audio_url') or data.get('url') or data.get('data')
                                        if audio_url:
                                            # Download audio
                                            async with session.get(audio_url) as audio_response:
                                                if audio_response.status == 200:
                                                    audio_data = await audio_response.read()
                                                    with open(output_path, "wb") as f:
                                                        f.write(audio_data)

                                                    duration = await self._get_audio_duration(output_path)

                                                    logger.info(
                                                        f"Vocu.ai synthesis successful! Downloaded from URL"
                                                    )
                                                    return audio_data, str(output_path), duration

                            elif response.status_code == 401:
                                logger.error("Vocu.ai authentication failed")
                                raise Exception("Invalid API key")

                            elif response.status_code == 403:
                                logger.error("Vocu.ai access denied")
                                raise Exception("Access denied - check API permissions")

                            elif response.status_code == 429:
                                logger.error("Vocu.ai rate limit exceeded")
                                raise Exception("Rate limit exceeded")

                except aiohttp.ClientError as e:
                    logger.debug(f"Request failed: {e}")
                    continue

        # If all attempts failed, try once more with error output
        raise Exception(
            "Failed to synthesize with Vocu.ai. "
            "Please check:\n"
            "1. API key is valid\n"
            "2. Sufficient points/balance\n"
            "3. Correct endpoint URL"
        )

    async def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration"""
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
            return 3.0

    async def synthesize_batch(
        self,
        texts: list[str],
        output_dir: Optional[Path] = None,
        max_concurrent: int = 4,
        **kwargs,
    ) -> list[tuple[bytes, str, float]]:
        """Batch synthesis"""
        results = []
        output_dir = output_dir or settings.CACHE_PATH

        semaphore = asyncio.Semaphore(max_concurrent)

        async def synthesize_one(i: int, text: str):
            async with semaphore:
                output_path = output_dir / f"audio_{i:04d}.mp3"
                try:
                    return await self.synthesize(text, output_path, **kwargs)
                except Exception as e:
                    logger.error(f"Failed to synthesize audio {i}: {e}")
                    return b"", "", 0.0

        tasks = [synthesize_one(i, text) for i, text in enumerate(texts)]
        results = await asyncio.gather(*tasks)

        return results

    async def test_connection(self) -> bool:
        """Test Vocu.ai API connection"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Vocu.ai connection test failed: {e}")
            return False


# Global client instance
vocu_client = VocuAIClient()
