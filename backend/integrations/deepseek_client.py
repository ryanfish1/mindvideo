"""
DeepSeek API 客户端

用于调用 DeepSeek API 进行脚本分析和提示词生成
"""

import json
from typing import Any

import aiohttp
from loguru import logger

from ..config import settings


class DeepSeekClient:
    """LLM API 客户端（支持 DeepSeek/SiliconFlow 等 OpenAI 兼容接口）"""

    def __init__(self):
        # 自动选择配置的 API（优先使用硅基流动）
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL

    async def _call_api(self, messages: list[dict[str, str]], **kwargs) -> dict[str, Any]:
        """调用 DeepSeek API"""
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs,
        }

        logger.debug(f"Calling LLM API: {self.base_url}/chat/completions")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"LLM API error: {response.status} - {error_text}")
                    raise Exception(f"LLM API error: {response.status} - {error_text}")

                data = await response.json()
                return data

    async def analyze_script(self, script: str) -> dict[str, Any]:
        """
        分析文案，生成分镜

        Args:
            script: 用户输入的文案

        Returns:
            包含分镜数据的字典
        """
        system_prompt = """你是 MindVideo 的专业分镜设计师，专门为认知科普视频设计分镜。

你的任务是将用户文案拆分为 2-4 秒的镜头序列，为每个镜头生成 SDXL 图片提示词。

**Mindmart 风格核心原则：**
1. **禁止字面翻译** - 不要简单描述文案字面意思
2. **追求隐喻性** - 使用象征性、抽象的视觉元素
3. **电影感 > 清晰度** - 优先考虑氛围、构图、色调
4. **哲学性 > 说明性** - 让画面引发思考

**SDXL 基础风格提示词（必须包含）：**
cinematic lighting, film grain, anamorphic lens, depth of field, professional photography, 8k uhd, high quality, masterpiece, moody atmosphere, dramatic composition, surreal touches, philosophical imagery, hyper-realistic, volumetric lighting

**视觉隐喻映射：**
- "博弈/竞争" → 棋盘、赌场轮盘、黑暗中的牌桌、拳击赛场 → dark mood, film noir, high contrast
- "大脑/认知" → 神经元网络、精密钟表结构、迷宫、大脑切面、生锈机器 → sci-fi, medical render, surrealism
- "陷阱/危机" → 悬崖、深渊、捕兽夹、多米诺骨牌、风暴 → dramatic atmosphere, stormy, apocalyptic
- "财富/金钱" → 金色流沙、燃烧货币、天平、硬币瀑布 → gold and black theme, minimalist
- "社会/群体" → 提线木偶、面具、灰色人群、聚光灯 → dystopian, surrealism, symbolic
- "成长/突破" → 破茧成蝶、攀登山峰、破墙而出、光芒 → inspirational, dramatic lighting

**镜头类型：**
- narration: 旁白镜头（配合文案内容）
- metaphor: 隐喻镜头（抽象表达概念）
- transition: 转场镜头（场景切换）
- title: 标题镜头（显示文字）

**Ken Burns 特效：**
- zoom_in: 缓慢推进（强调聚焦）
- zoom_out: 缓慢拉远（展示环境）
- pan_left: 向左平移（展现空间）
- pan_right: 向右平移（延续视线）
- none: 无特效（静态画面）

请返回 JSON 格式的分镜数据，结构如下：
```json
{
  "scenes": [
    {
      "narration": "旁白文案",
      "visual_prompt": "SDXL正向提示词",
      "scene_type": "narration|metaphor|transition|title",
      "duration": 3.0,
      "ken_burns": "zoom_in|zoom_out|pan_left|pan_right|none"
    }
  ]
}
```"""

        user_prompt = f"""请将以下文案拆分为分镜序列，目标视频时长约 5 分钟（80-100 个镜头）：

{script}

要求：
1. 每个镜头 2-4 秒
2. 遵循 Mindmart 风格原则
3. 为每个镜头生成符合内容的 SDXL 提示词
4. 选择合适的 Ken Burns 特效
5. 返回完整的 JSON 数据"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self._call_api(
                messages,
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=16000,
            )

            content = response["choices"][0]["message"]["content"]
            result = json.loads(content)

            logger.info(f"Script analysis completed, generated {len(result.get('scenes', []))} scenes")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise Exception(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Script analysis failed: {e}")
            raise

    async def generate_visual_prompt(self, narration: str, scene_context: str) -> tuple[str, str]:
        """
        为单个镜头生成 SDXL 提示词

        Args:
            narration: 旁白文案
            scene_context: 场景上下文

        Returns:
            (positive_prompt, negative_prompt) 元组
        """
        system_prompt = """你是 MindVideo 的 SDXL 提示词专家。

为给定的旁白文案生成高质量的电影级提示词。

**正向提示词必须包含：**
cinematic lighting, film grain, anamorphic lens, depth of field, professional photography, 8k uhd, high quality, masterpiece, moody atmosphere, dramatic composition, surreal touches, philosophical imagery, hyper-realistic, volumetric lighting

**根据内容添加风格关键词：**
- 认知/大脑: sci-fi, medical render, macro photography, surrealism
- 财富/金钱: gold and black theme, minimalist, elegant
- 危机/陷阱: dramatic atmosphere, stormy, apocalyptic
- 成长/突破: inspirational, dramatic lighting, hopeful

**负向提示词：**
(worst quality, low quality:1.4), blurry, distortion, ugly, deformed, cartoon, anime, 3d render, oversaturated, flat lighting, watermark, text

返回 JSON 格式：
{
  "positive": "正向提示词",
  "negative": "负向提示词"
}"""

        user_prompt = f"""旁白文案：{narration}\n\n场景上下文：{scene_context}\n\n请生成 SDXL 提示词。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self._call_api(
                messages,
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=500,
            )

            content = response["choices"][0]["message"]["content"]
            result = json.loads(content)

            return result.get("positive", ""), result.get("negative", "")

        except Exception as e:
            logger.error(f"Visual prompt generation failed: {e}")
            # 返回默认提示词
            return (
                "cinematic lighting, film grain, anamorphic lens, depth of field, professional photography, 8k uhd, high quality, masterpiece, moody atmosphere",
                "(worst quality, low quality:1.4), blurry, distortion, ugly, deformed",
            )

    async def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            messages = [{"role": "user", "content": "Hello"}]
            await self._call_api(messages, max_tokens=10)
            logger.info("LLM API connection test successful")
            return True
        except Exception as e:
            logger.error(f"LLM API connection test failed: {e}")
            return False


# 全局客户端实例
deepseek_client = DeepSeekClient()
