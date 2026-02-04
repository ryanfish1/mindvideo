"""
配置管理模块

从环境变量和配置文件中读取系统配置
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """系统配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========== API 配置 ==========
    # 硅基流动配置（优先使用）
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_MODEL: str = "deepseek-ai/DeepSeek-V3"

    # DeepSeek 配置（备用）
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # 自动使用硅基流动（如果配置了 API Key）
    @property
    def LLM_API_KEY(self) -> str:
        """自动选择可用的 API Key"""
        return self.SILICONFLOW_API_KEY or self.DEEPSEEK_API_KEY

    @property
    def LLM_BASE_URL(self) -> str:
        """自动选择可用的 API 地址"""
        return self.SILICONFLOW_BASE_URL if self.SILICONFLOW_API_KEY else self.DEEPSEEK_BASE_URL

    @property
    def LLM_MODEL(self) -> str:
        """自动选择可用的模型"""
        return self.SILICONFLOW_MODEL if self.SILICONFLOW_API_KEY else self.DEEPSEEK_MODEL

    # ========== SDXL 配置 ==========
    SDXL_URL: str = "http://localhost:7860"
    SDXL_CHECKPOINT: str = "AnythingXL_xl.safetensors"
    SDXL_WIDTH: int = 2560
    SDXL_HEIGHT: int = 1440
    SDXL_STEPS: int = 30
    SDXL_CFG_SCALE: float = 7.5
    SDXL_SAMPLER: str = "DPM++ 2M Karras"

    # ========== GPT-SoVITS 配置 ==========
    SOVITS_URL: str = "http://localhost:9881"  # REST API (api_v2.py)
    SOVITS_MODEL: str = "default"
    SOVITS_REFERENCE_AUDIO: str = r"D:\code\generation\storage\my_voice_ref.wav"  # 3-10 seconds reference audio

    # ========== IndexTTS 配置 ==========
    INDEXTTS_URL: str = "http://127.0.0.1:7860"  # Gradio WebUI
    INDEXTTS_REFERENCE_AUDIO: str = r"G:\index\index-tts-windows\prompts\sample_prompt.wav"  # 参考音频

    # ========== Edge TTS 配置（备用） ==========
    EDGE_TTS_VOICE: str = "zh-CN-YunxiNeural"
    EDGE_TTS_RATE: str = "+0%"
    EDGE_TTS_VOLUME: str = "+0%"

    # ========== Pexels 配置 ==========
    PEXELS_API_KEY: str = ""

    # ========== 存储配置 ==========
    STORAGE_PATH: Path = Path("./storage")
    PROJECTS_PATH: Path = Path("./storage/projects")
    ASSETS_PATH: Path = Path("./storage/assets")
    CACHE_PATH: Path = Path("./storage/cache")
    OUTPUT_PATH: Path = Path("./storage/output")

    # ========== 视频输出配置 ==========
    OUTPUT_RESOLUTION: str = "2560x1440"  # 2K
    FPS: int = 30
    VIDEO_CODEC: str = "libx264"
    VIDEO_PRESET: str = "medium"
    VIDEO_CRF: int = 23

    # ========== 镜头配置 ==========
    DEFAULT_SCENE_DURATION: float = 3.0  # 默认镜头时长（秒）
    MIN_SCENE_DURATION: float = 2.0  # 最小镜头时长
    MAX_SCENE_DURATION: float = 5.0  # 最大镜头时长
    TARGET_VIDEO_DURATION: float = 300.0  # 目标视频时长（5分钟）

    # ========== 并发配置 ==========
    MAX_CONCURRENT_IMAGES: int = 2  # SDXL 最大并发生成数
    MAX_CONCURRENT_AUDIO: int = 4  # TTS 最大并发生成数

    # ========== 服务器配置 ==========
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ========== 日志配置 ==========
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_FILE: str = "mindvideo.log"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    settings = Settings()
    # 确保存储目录存在
    settings.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    settings.PROJECTS_PATH.mkdir(parents=True, exist_ok=True)
    settings.ASSETS_PATH.mkdir(parents=True, exist_ok=True)
    settings.CACHE_PATH.mkdir(parents=True, exist_ok=True)
    settings.OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    return settings


# 全局配置实例
settings = get_settings()
