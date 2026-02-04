"""
智能视频素材匹配服务

使用 AI 语义理解 + Pexels API 智能匹配视频素材
"""
import asyncio
from dataclasses import dataclass
from typing import Optional

import aiohttp

from ..integrations.deepseek_client import deepseek_client
from ..config import settings


@dataclass
class VideoMatch:
    """视频匹配结果"""
    url: str
    width: int
    height: int
    duration: float
    preview_url: Optional[str] = None
    relevance_score: float = 0.0


@dataclass
class SearchQuery:
    """搜索查询"""
    query: str
    priority: int  # 优先级，数字越小优先级越高
    reason: str  # 选择这个查询词的理由


class VideoMatchingService:
    """智能视频素材匹配服务"""

    def __init__(self):
        self.pexels_api_key = settings.PEXELS_API_KEY
        self.base_url = "https://api.pexels.com/videos"
        self.deepseek = deepseek_client

    async def generate_search_queries(
        self,
        narration: str,
        text_overlay: str,
    ) -> list[SearchQuery]:
        """
        为文案生成多个搜索查询词

        Args:
            narration: 旁白文案
            text_overlay: 屏幕文字

        Returns:
            搜索查询列表，按优先级排序
        """
        prompt = f"""你是一个专业的视频素材搜索专家。我需要为以下中文文案找到最合适的英文视频搜索关键词。

文案内容：
- 旁白: {narration}
- 屏幕文字: {text_overlay}

请分析文案的核心视觉元素和情感氛围，生成 3-5 个英文搜索查询词。

要求：
1. 查询词应该是具体的视觉场景描述（如 "person counting coins worried" 而不是 "money"）
2. 包含主体（person/business/nature等）+ 动作/状态
3. 考虑情感色彩（happy/sad/tense/calm等）
4. 每个查询词要有不同的角度（人物、抽象、物体、环境等）

输出格式（JSON）:
{{
    "queries": [
        {{"query": "英文搜索词1", "reason": "选择理由", "priority": 1}},
        {{"query": "英文搜索词2", "reason": "选择理由", "priority": 2}},
        {{"query": "英文搜索词3", "reason": "选择理由", "priority": 3}}
    ]
}}

只输出 JSON，不要其他内容。"""

        try:
            messages = [
                {"role": "system", "content": "You are a professional video search expert. Always output valid JSON."},
                {"role": "user", "content": prompt}
            ]
            response = await self.deepseek._call_api(
                messages,
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=1000
            )

            import json
            content = response["choices"][0]["message"]["content"]
            result = json.loads(content)

            queries = []
            for q in result.get("queries", []):
                queries.append(SearchQuery(
                    query=q["query"],
                    priority=q.get("priority", 99),
                    reason=q.get("reason", "")
                ))

            # 按优先级排序
            queries.sort(key=lambda x: x.priority)
            return queries

        except Exception as e:
            # 降级方案：基于关键词生成
            return self._fallback_queries(narration, text_overlay)

    def _fallback_queries(self, narration: str, text_overlay: str) -> list[SearchQuery]:
        """降级方案：基于简单关键词生成查询"""
        # 简单的关键词映射
        keywords = {
            "钱": "money",
            "时间": "time clock",
            "思考": "thinking person",
            "贫穷": "poverty struggle",
            "未来": "future hope",
            "消耗": "exhausted tired",
            "注意力": "focus concentration",
            "循环": "circle loop",
            "节省": "saving budgeting",
        }

        queries = []
        for cn, en in keywords.items():
            if cn in narration or cn in text_overlay:
                queries.append(SearchQuery(
                    query=en,
                    priority=len(queries),
                    reason=f"关键词匹配: {cn}"
                ))

        if not queries:
            queries.append(SearchQuery(
                query="abstract concept",
                priority=1,
                reason="默认查询"
            ))

        return queries

    async def search_pexels(
        self,
        query: str,
        orientation: str = "landscape",
        per_page: int = 10,
    ) -> list[dict]:
        """
        搜索 Pexels 视频

        Args:
            query: 搜索关键词
            orientation: 视频方向 (landscape/portrait/square)
            per_page: 每页结果数

        Returns:
            视频列表
        """
        url = f"{self.base_url}/search"
        params = {
            "query": query,
            "orientation": orientation,
            "per_page": per_page,
            "order_by": "relevance"  # 按相关性排序
        }

        headers = {
            "Authorization": self.pexels_api_key
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("videos", [])
                    return []
        except Exception as e:
            print(f"Pexels search error: {e}")
            return []

    def _select_best_video(
        self,
        videos: list[dict],
        min_width: int = 1280,
        preferred_duration: Optional[float] = None,
    ) -> Optional[VideoMatch]:
        """
        从搜索结果中选择最佳视频

        Args:
            videos: 视频列表
            min_width: 最小宽度要求
            preferred_duration: 偏好的时长

        Returns:
            最佳视频匹配
        """
        if not videos:
            return None

        candidates = []

        for video in videos:
            video_files = video.get("video_files", [])

            # 找到符合条件的视频文件
            for vf in video_files:
                width = vf.get("width", 0)
                height = vf.get("height", 0)

                if width >= min_width:
                    # 计算相关性分数
                    score = self._calculate_relevance_score(
                        video, width, preferred_duration
                    )

                    candidates.append(VideoMatch(
                        url=vf["link"],
                        width=width,
                        height=height,
                        duration=video.get("duration", 0),
                        preview_url=video.get("image"),
                        relevance_score=score
                    ))
                    break  # 每个视频只取最高分辨率

        if not candidates:
            return None

        # 按相关性分数排序
        candidates.sort(key=lambda x: x.relevance_score, reverse=True)
        return candidates[0]

    def _calculate_relevance_score(
        self,
        video: dict,
        width: int,
        preferred_duration: Optional[float],
    ) -> float:
        """
        计算视频相关性分数

        Args:
            video: 视频数据
            width: 视频宽度
            preferred_duration: 偏好时长

        Returns:
            相关性分数 (0-100)
        """
        score = 50.0  # 基础分

        # 分辨率加分 (1080p 及以上加分)
        if width >= 1920:
            score += 20
        elif width >= 1280:
            score += 10

        # 时长匹配加分
        video_duration = video.get("duration", 0)
        if preferred_duration:
            # 如果视频时长接近偏好时长，加分
            diff = abs(video_duration - preferred_duration)
            if diff < 2:
                score += 20
            elif diff < 5:
                score += 10

        # 视频质量指标 (如果有)
        if video.get("avg_fps", 0) >= 24:
            score += 5

        return min(score, 100.0)

    async def find_best_match(
        self,
        narration: str,
        text_overlay: str,
        preferred_duration: float = 5.0,
        max_attempts: int = 3,
    ) -> Optional[VideoMatch]:
        """
        为文案找到最佳匹配视频

        Args:
            narration: 旁白文案
            text_overlay: 屏幕文字
            preferred_duration: 偏好的视频时长
            max_attempts: 最大尝试次数（不同查询词）

        Returns:
            最佳视频匹配，如果没找到返回 None
        """
        # 1. 生成搜索查询词
        queries = await self.generate_search_queries(narration, text_overlay)

        if not queries:
            return None

        print(f"  Generated {len(queries)} search queries")

        # 2. 尝试每个查询词
        for attempt, search_query in enumerate(queries[:max_attempts]):
            print(f"  Attempt {attempt + 1}: '{search_query.query}' ({search_query.reason})")

            videos = await self.search_pexels(search_query.query)

            if videos:
                best_match = self._select_best_video(
                    videos,
                    min_width=1280,
                    preferred_duration=preferred_duration
                )

                if best_match:
                    print(f"    [OK] Found: {best_match.width}x{best_match.height}, {best_match.duration}s")
                    return best_match
            else:
                print(f"    [X] No results")

        # 所有查询都没找到
        print(f"  [X] No matches found after {max_attempts} attempts")
        return None

    async def download_video(
        self,
        match: VideoMatch,
        output_path: str,
    ) -> bool:
        """
        下载视频

        Args:
            match: 视频匹配结果
            output_path: 输出路径

        Returns:
            是否成功
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(match.url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(output_path, 'wb') as f:
                            f.write(content)
                        return True
            return False
        except Exception as e:
            print(f"Download error: {e}")
            return False


# 全局服务实例
video_matching_service = VideoMatchingService()
