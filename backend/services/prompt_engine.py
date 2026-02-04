"""
Mindmart 提示词引擎

生成符合 Mindmart 风格的 SDXL 提示词
"""

from typing import Optional


# ========== Mindmart 基础风格提示词 ==========

MINDMART_BASE_PROMPT = """cinematic lighting, film grain, anamorphic lens, depth of field,
professional photography, 8k uhd, high quality, masterpiece, moody atmosphere,
dramatic composition, surreal touches, philosophical imagery, hyper-realistic,
volumetric lighting, movie still, ar 16:9"""

MINDMART_NEGATIVE_PROMPT = """(worst quality, low quality:1.4), blurry, distortion, ugly,
deformed, cartoon, anime, 3d render, oversaturated, flat lighting, watermark,
text, signature, logo, bad anatomy, disfigured, poorly drawn face, mutation"""


# ========== 视觉隐喻映射库 ==========

METAPHOR_MAPPINGS = {
    "博弈/竞争": {
        "elements": ["棋盘", "赌场轮盘", "黑暗中的牌桌", "拿铲子的淘金者", "拳击赛场", "博弈", "竞争"],
        "style": "dark mood, film noir, high contrast, cinematic, dramatic shadows",
        "examples": [
            "A chessboard in dark room with dramatic lighting",
            "Casino roulette wheel spinning in low light",
            "Card game table in film noir style",
            "Boxing ring with atmospheric lighting",
        ],
    },
    "大脑/认知": {
        "elements": ["神经元", "突触", "神经网络", "钟表", "齿轮", "迷宫", "大脑切面", "机械大脑", "生锈机器"],
        "style": "sci-fi, medical render, macro photography, surrealism, bioluminescent, intricate",
        "examples": [
            "Glowing neural network in dark space",
            "Intricate clockwork mechanism representing consciousness",
            "Brain cross-section with mechanical elements",
            "Maze with glowing pathways",
            "Rusty machine representing cognitive decline",
        ],
    },
    "陷阱/危机": {
        "elements": ["悬崖", "深渊", "捕兽夹", "多米诺骨牌", "风暴", "深海下沉", "铁锚", "陷阱", "危机"],
        "style": "dramatic atmosphere, stormy, apocalyptic, ominous, tense",
        "examples": [
            "Figure standing at cliff edge in fog",
            "Animal trap in dark forest",
            "Dominoes falling in dramatic slow motion",
            "Ship anchor descending into deep dark water",
            "Approaching storm on horizon",
        ],
    },
    "财富/金钱": {
        "elements": ["金色流沙", "燃烧货币", "天平", "巨大数字", "硬币瀑布", "精炼厂", "账本", "财富", "金钱"],
        "style": "gold and black theme, minimalist, elegant, volumetric lighting, luxury",
        "examples": [
            "Gold coins falling in slow motion against black",
            "Antique weighing scale with gold dust",
            "Giant numbers floating in golden light",
            "Luxury vault with dramatic lighting",
        ],
    },
    "社会/群体": {
        "elements": ["提线木偶", "面具", "灰色人群", "整齐划一", "聚光灯", "散场", "社会", "群体"],
        "style": "dystopian, surrealism, symbolic, cinematic, psychological",
        "examples": [
            "Marionette puppet hanging in dark space",
            "Rows of identical masks on wall",
            "Crowd of faceless figures in grey",
            "Single spotlight in empty theatre",
        ],
    },
    "成长/突破": {
        "elements": ["破茧", "蝴蝶", "攀登山峰", "破墙", "光芒", "阶梯", "突破束缚", "成长"],
        "style": "inspirational, dramatic lighting, cinematic, hopeful, powerful",
        "examples": [
            "Butterfly emerging from cocoon in dramatic light",
            "Figure climbing mountain peak at sunrise",
            "Light breaking through cracked wall",
            "Spiral staircase ascending into light",
            "Chain breaking in dramatic slow motion",
        ],
    },
    "时间/选择": {
        "elements": ["时钟", "分岔路口", "沙漏", "时间隧道", "多重宇宙", "选择", "时间"],
        "style": "surreal, philosophical, conceptual, depth of field, ethereal",
        "examples": [
            "Antique clock in misty landscape",
            "Fork in road under dramatic sky",
            "Hourglass with floating particles",
            "Infinite mirror tunnel",
            "Multiple doorways in abstract space",
        ],
    },
}


# ========== 镜头类型提示词模板 ==========

SCENE_TYPE_PROMPTS = {
    "narration": {
        "style_suffix": "storytelling atmosphere, documentary style",
        "composition": "balanced composition, rule of thirds",
    },
    "metaphor": {
        "style_suffix": "surreal, symbolic, abstract, conceptual art",
        "composition": "centered composition, minimalist, negative space",
    },
    "transition": {
        "style_suffix": "atmospheric, environmental, establishing shot",
        "composition": "wide angle, environmental context",
    },
    "title": {
        "style_suffix": "clean background, text-friendly, minimal",
        "composition": "plenty of negative space, center focus",
    },
}


# ========== Ken Burns 特效建议 ==========

KEN_BURNS_SUGGESTIONS = {
    "zoom_in": [
        "强调主体",
        "聚焦细节",
        "推进叙事",
        "展示情感",
    ],
    "zoom_out": [
        "展示环境",
        "揭示全景",
        "开阔视野",
        "结束场景",
    ],
    "pan_left": [
        "横向展示",
        "空间延伸",
        "跟随运动",
    ],
    "pan_right": [
        "延续视线",
        "场景过渡",
        "展示关联",
    ],
}


def build_visual_prompt(
    narration: str,
    scene_type: str = "narration",
    context: Optional[str] = None,
) -> tuple[str, str]:
    """
    构建完整的 SDXL 提示词

    Args:
        narration: 旁白文案
        scene_type: 镜头类型
        context: 场景上下文

    Returns:
        (positive_prompt, negative_prompt) 元组
    """
    positive_parts = [MINDMART_BASE_PROMPT]

    # 添加镜头类型风格
    if scene_type in SCENE_TYPE_PROMPTS:
        type_config = SCENE_TYPE_PROMPTS[scene_type]
        positive_parts.append(type_config["style_suffix"])
        positive_parts.append(type_config["composition"])

    # 分析文案中的隐喻元素
    detected_metaphor = None
    for metaphor_key, metaphor_data in METAPHOR_MAPPINGS.items():
        for element in metaphor_data["elements"]:
            if element in narration:
                detected_metaphor = metaphor_key
                positive_parts.append(metaphor_data["style"])
                break
        if detected_metaphor:
            break

    # 根据旁白内容添加具体描述
    if detected_metaphor:
        # 从隐喻库中提取相关视觉元素
        metaphor_data = METAPHOR_MAPPINGS[detected_metaphor]
        # 可以根据具体文案选择示例
        pass

    positive_prompt = ", ".join(positive_parts)

    return positive_prompt, MINDMART_NEGATIVE_PROMPT


def suggest_ken_burns_effect(narration: str, scene_type: str = "narration") -> str:
    """
    根据旁白内容建议 Ken Burns 特效

    Args:
        narration: 旁白文案
        scene_type: 镜头类型

    Returns:
        特效类型 (zoom_in/zoom_out/pan_left/pan_right/none)
    """
    # 隐喻镜头常用 zoom_in 强调象征意义
    if scene_type == "metaphor":
        return "zoom_in"

    # 标题镜头通常不需要特效
    if scene_type == "title":
        return "none"

    # 转场镜头用 zoom_out 展示环境
    if scene_type == "transition":
        return "zoom_out"

    # 根据文案关键词判断
    action_keywords = {
        "zoom_in": ["进入", "深入", "发现", "揭示", "聚焦", "本质", "核心"],
        "zoom_out": "看到", "发现", "原来", "全景", "整体", "宏观",
        "pan_left": ["回顾", "过去", "历史", "曾经"],
        "pan_right": ["未来", "向前", "接下来", "然后"],
    }

    for effect, keywords in action_keywords.items():
        if isinstance(keywords, list):
            for keyword in keywords:
                if keyword in narration:
                    return effect
        else:
            if keywords in narration:
                return effect

    # 默认使用 zoom_in
    return "zoom_in"


def get_metaphor_examples(category: str) -> list[str]:
    """
    获取指定隐喻类别的示例提示词

    Args:
        category: 隐喻类别

    Returns:
        示例提示词列表
    """
    if category in METAPHOR_MAPPINGS:
        return METAPHOR_MAPPINGS[category].get("examples", [])
    return []


def refine_prompt_for_sdxl(prompt: str, max_length: int = 400) -> str:
    """
    优化提示词以适配 SDXL

    Args:
        prompt: 原始提示词
        max_length: 最大长度（token 数）

    Returns:
        优化后的提示词
    """
    # SDXL 对长提示词有较好支持，但仍需控制
    words = prompt.split(", ")
    # 移除重复
    seen = set()
    unique_words = []
    for word in words:
        word = word.strip()
        if word and word not in seen:
            seen.add(word)
            unique_words.append(word)

    return ", ".join(unique_words[:50])  # 限制关键词数量


# ========== 快速构建函数 ==========


def quick_prompt(
    description: str,
    style: Optional[str] = None,
    mood: Optional[str] = None,
) -> str:
    """
    快速构建 SDXL 提示词

    Args:
        description: 场景描述
        style: 风格关键词
        mood: 情绪关键词

    Returns:
        完整提示词
    """
    parts = [MINDMART_BASE_PROMPT]

    if style:
        parts.append(style)
    if mood:
        parts.append(mood)

    parts.append(description)

    return ", ".join(parts)
