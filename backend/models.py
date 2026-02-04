"""
数据模型定义

定义所有 Pydantic 数据模型，用于 API 请求/响应和数据验证
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_serializer


# ==================== 枚举类型 ====================


class SceneType(str, Enum):
    """镜头类型"""

    NARRATION = "narration"  # 旁白镜头
    METAPHOR = "metaphor"  # 隐喻镜头
    TRANSITION = "transition"  # 转场镜头
    TITLE = "title"  # 标题镜头


class KenBurnsEffect(str, Enum):
    """Ken Burns 特效类型"""

    ZOOM_IN = "zoom_in"  # 缩放推进
    ZOOM_OUT = "zoom_out"  # 缩放拉远
    PAN_LEFT = "pan_left"  # 向左平移
    PAN_RIGHT = "pan_right"  # 向右平移
    NONE = "none"  # 无特效


class ProjectStatus(str, Enum):
    """项目状态"""

    DRAFT = "draft"  # 草稿
    ANALYZING = "analyzing"  # 分析中
    READY = "ready"  # 准备就绪
    GENERATING = "generating"  # 生成中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class TaskStage(str, Enum):
    """任务阶段"""

    ANALYZING = "analyzing"  # 脚本分析
    IMAGES = "images"  # 图片生成
    AUDIO = "audio"  # 音频生成
    VIDEO = "video"  # 视频片段生成
    COMPOSING = "composing"  # 视频合成
    DONE = "done"  # 完成


# ==================== 核心模型 ====================


class StoryboardScene(BaseModel):
    """分镜镜头模型"""

    id: str = Field(description="镜头 ID")
    narration: str = Field(description="旁白文案")
    visual_prompt: str = Field(description="SDXL 正向提示词")
    negative_prompt: str = Field(
        default="(worst quality, low quality:1.4), blurry, distortion, ugly, deformed, cartoon, anime, 3d render, oversaturated, flat lighting, watermark, text",
        description="SDXL 负向提示词",
    )
    scene_type: SceneType = Field(default=SceneType.NARRATION, description="镜头类型")
    duration: float = Field(default=3.0, ge=1.0, le=10.0, description="镜头时长（秒）")
    ken_burns: KenBurnsEffect = Field(default=KenBurnsEffect.ZOOM_IN, description="Ken Burns 特效")
    image_path: Optional[str] = Field(default=None, description="生成的图片路径")
    video_path: Optional[str] = Field(default=None, description="Ken Burns 视频路径")
    audio_path: Optional[str] = Field(default=None, description="TTS 音频路径")
    order: int = Field(description="镜头顺序")


class Storyboard(BaseModel):
    """分镜模型"""

    model_config = ConfigDict(
        populate_by_name=True,
    )

    id: str = Field(description="分镜 ID")
    project_id: str = Field(description="所属项目 ID")
    scenes: list[StoryboardScene] = Field(default_factory=list, description="镜头列表")
    total_duration: float = Field(default=0.0, description="总时长（秒）")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()

    def calculate_duration(self) -> float:
        """计算总时长"""
        self.total_duration = sum(scene.duration for scene in self.scenes)
        return self.total_duration


class Project(BaseModel):
    """项目模型"""

    id: str = Field(description="项目 ID")
    name: str = Field(description="项目名称")
    description: Optional[str] = Field(default=None, description="项目描述")
    script: str = Field(description="用户输入的文案")
    storyboard: Optional[Storyboard] = Field(default=None, description="分镜数据")
    video_output_path: Optional[str] = Field(default=None, description="输出视频路径")
    status: ProjectStatus = Field(default=ProjectStatus.DRAFT, description="项目状态")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class GenerationTask(BaseModel):
    """生成任务模型"""

    id: str = Field(description="任务 ID")
    project_id: str = Field(description="关联项目 ID")
    stage: TaskStage = Field(description="当前阶段")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="进度（0.0 - 1.0）")
    current_scene: Optional[int] = Field(default=None, description="当前处理的镜头索引")
    total_scenes: int = Field(default=0, description="总镜头数")
    message: str = Field(default="", description="状态消息")
    error: Optional[str] = Field(default=None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


# ==================== API 请求/响应模型 ====================


class CreateProjectRequest(BaseModel):
    """创建项目请求"""

    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    description: Optional[str] = Field(default=None, description="项目描述")
    script: str = Field(..., min_length=10, description="输入文案")


class UpdateProjectRequest(BaseModel):
    """更新项目请求"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="项目名称")
    description: Optional[str] = Field(default=None, description="项目描述")
    script: Optional[str] = Field(default=None, min_length=10, description="输入文案")


class AnalyzeScriptRequest(BaseModel):
    """分析文案请求"""

    script: str = Field(..., min_length=10, description="待分析的文案")


class GenerateVideoRequest(BaseModel):
    """生成视频请求"""

    project_id: str = Field(..., description="项目 ID")
    use_sovits: bool = Field(default=False, description="是否使用 GPT-SoVITS（否则使用 Edge TTS）")
    enable_subtitles: bool = Field(default=True, description="是否启用字幕")


class ProjectListResponse(BaseModel):
    """项目列表响应"""

    projects: list[Project]
    total: int


class StoryboardResponse(BaseModel):
    """分镜响应"""

    storyboard: Storyboard
    scenes: list[StoryboardScene]


class TaskProgressResponse(BaseModel):
    """任务进度响应"""

    task_id: str
    stage: TaskStage
    progress: float
    message: str
    current_scene: Optional[int] = None
    total_scenes: int = 0


# ==================== 数据库模型 ====================


class ProjectDB(BaseModel):
    """数据库中的项目模型"""

    id: str
    name: str
    description: Optional[str] = None
    script: str
    storyboard_data: Optional[str] = None  # JSON 序列化的分镜数据
    video_output_path: Optional[str] = None
    status: ProjectStatus = ProjectStatus.DRAFT
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
