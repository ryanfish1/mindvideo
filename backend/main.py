"""
MindVideo 后端服务

FastAPI 应用入口
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .config import settings
from .database import database, init_database
from .models import (
    AnalyzeScriptRequest,
    CreateProjectRequest,
    GenerateVideoRequest,
    GenerationTask,
    Project,
    ProjectDB,
    ProjectListResponse,
    ProjectStatus,
    Storyboard,
    TaskProgressResponse,
    TaskStage,
    UpdateProjectRequest,
)
from .repositories.project_repo import project_repo
from .repositories.task_repo import task_repo
from .services.script_analysis import script_analysis_service
from .services.video_generation import video_generation_workflow


# ========== WebSocket 连接管理 ==========


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, project_id: str, websocket: WebSocket):
        """连接 WebSocket"""
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        logger.info(f"WebSocket connected for project {project_id}")

    def disconnect(self, project_id: str, websocket: WebSocket):
        """断开 WebSocket"""
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        logger.info(f"WebSocket disconnected for project {project_id}")

    async def send_progress(self, project_id: str, progress: TaskProgressResponse):
        """发送进度更新"""
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(progress.model_dump())
                except Exception as e:
                    logger.error(f"Error sending progress: {e}")


manager = ConnectionManager()


# ========== 应用生命周期 ==========


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting MindVideo backend...")
    logger.add(
        settings.LOG_FILE,
        rotation="10 MB",
        retention="7 days",
        level=settings.LOG_LEVEL,
    )
    await init_database()
    logger.info("Database initialized")
    yield
    # 关闭时
    logger.info("Shutting down MindVideo backend...")


# ========== FastAPI 应用 ==========


app = FastAPI(
    title="MindVideo API",
    description="本地化认知科普视频自动化生成系统",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 根路由 ==========


@app.get("/")
async def root():
    """根路由"""
    return {
        "name": "MindVideo API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


# ========== 项目路由 ==========


@app.post("/api/projects", response_model=Project)
async def create_project(request: CreateProjectRequest):
    """创建新项目"""
    project = Project(
        id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        script=request.script,
        status=ProjectStatus.DRAFT,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    return await project_repo.create(project)


@app.get("/api/projects", response_model=ProjectListResponse)
async def list_projects(
    status: Optional[ProjectStatus] = None,
    limit: int = 50,
    offset: int = 0,
):
    """获取项目列表"""
    projects = await project_repo.list(status, limit, offset)
    total = await project_repo.count(status)

    return ProjectListResponse(projects=projects, total=total)


@app.get("/api/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """获取项目详情"""
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.put("/api/projects/{project_id}", response_model=Project)
async def update_project(project_id: str, request: UpdateProjectRequest):
    """更新项目"""
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if request.name is not None:
        project.name = request.name
    if request.description is not None:
        project.description = request.description
    if request.script is not None:
        project.script = request.script

    return await project_repo.update(project)


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""
    success = await project_repo.delete(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted"}


# ========== 分析和生成路由 ==========


@app.post("/api/projects/{project_id}/analyze", response_model=Storyboard)
async def analyze_script(project_id: str, request: AnalyzeScriptRequest):
    """分析文案，生成分镜"""
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # 使用脚本分析服务
        storyboard = await script_analysis_service.analyze_script(request.script, project_id)

        # 保存分镜到项目
        await project_repo.update_storyboard(project_id, storyboard)

        return storyboard

    except Exception as e:
        logger.error(f"Script analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Script analysis failed: {str(e)}")


def _run_video_generation(project_id: str, use_sovits: bool, enable_subtitles: bool, task_id: str):
    """后台任务：运行视频生成"""
    async def _run():
        try:
            # 进度回调（发送 WebSocket 更新）
            async def progress_callback(stage, progress, current, total):
                # 获取任务状态
                task = await task_repo.get_by_id(task_id)
                if task:
                    response = TaskProgressResponse(
                        task_id=task.id,
                        stage=task.stage,
                        progress=task.progress,
                        message=task.message,
                        current_scene=task.current_scene,
                        total_scenes=task.total_scenes,
                    )
                    await manager.send_progress(project_id, response)

            # 执行工作流
            output_path = await video_generation_workflow.execute(
                project_id=project_id,
                use_sovits=use_sovits,
                enable_subtitles=enable_subtitles,
                progress_callback=progress_callback,
            )

            logger.info(f"Video generation completed: {output_path}")

        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            # 更新任务状态为失败
            task = await task_repo.get_by_id(task_id)
            if task:
                task.error = str(e)
                await task_repo.update(task)

    # 运行异步任务
    asyncio.run(_run())


@app.post("/api/projects/{project_id}/generate", response_model=GenerationTask)
async def generate_video(project_id: str, request: GenerateVideoRequest, background_tasks: BackgroundTasks):
    """生成视频"""
    # 检查项目是否存在
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 检查项目是否有分镜
    if not project.storyboard:
        raise HTTPException(status_code=400, detail="Project has no storyboard. Please analyze script first.")

    # 创建任务
    task = GenerationTask(
        id=str(uuid.uuid4()),
        project_id=project_id,
        stage=TaskStage.ANALYZING,
        progress=0.0,
        total_scenes=len(project.storyboard.scenes) if project.storyboard else 0,
        message="任务已创建",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    task = await task_repo.create(task)

    # 更新项目状态
    await project_repo.update_status(project_id, ProjectStatus.GENERATING)

    # 启动后台任务
    background_tasks.add_task(
        _run_video_generation,
        project_id,
        request.use_sovits,
        request.enable_subtitles,
        task.id,
    )

    return task


@app.get("/api/projects/{project_id}/tasks/{task_id}", response_model=TaskProgressResponse)
async def get_task_progress(project_id: str, task_id: str):
    """获取任务进度"""
    task = await task_repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskProgressResponse(
        task_id=task.id,
        stage=task.stage,
        progress=task.progress,
        message=task.message,
        current_scene=task.current_scene,
        total_scenes=task.total_scenes,
    )


@app.get("/api/projects/{project_id}/tasks/latest", response_model=TaskProgressResponse)
async def get_latest_task(project_id: str):
    """获取项目的最新任务"""
    task = await task_repo.get_by_project(project_id)
    if not task:
        raise HTTPException(status_code=404, detail="No task found for this project")

    return TaskProgressResponse(
        task_id=task.id,
        stage=task.stage,
        progress=task.progress,
        message=task.message,
        current_scene=task.current_scene,
        total_scenes=task.total_scenes,
    )


# ========== WebSocket 路由 ==========


@app.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """WebSocket 进度推送"""
    await manager.connect(project_id, websocket)
    try:
        while True:
            # 保持连接
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(project_id, websocket)


# ========== 启动服务器 ==========


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
