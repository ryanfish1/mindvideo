"""
任务数据仓库

处理视频生成任务的数据库操作
"""

import asyncio
from datetime import datetime
from typing import Optional

from loguru import logger

from ..database import database
from ..models import GenerationTask, TaskStage


class TaskRepository:
    """任务数据仓库"""

    async def create(self, task: GenerationTask) -> GenerationTask:
        """创建任务"""
        async with database.get_connection() as db:
            await db.execute(
                """
                INSERT INTO tasks (id, project_id, stage, progress, current_scene, total_scenes, message, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    task.id,
                    task.project_id,
                    task.stage.value,
                    task.progress,
                    task.current_scene,
                    task.total_scenes,
                    task.message,
                    task.error,
                    task.created_at,
                    task.updated_at,
                ),
            )
            await db.commit()

        logger.info(f"Task created: {task.id} for project {task.project_id}")
        return task

    async def get_by_id(self, task_id: str) -> Optional[GenerationTask]:
        """根据 ID 获取任务"""
        async with database.get_connection() as db:
            cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_task(row)

    async def get_by_project(self, project_id: str) -> Optional[GenerationTask]:
        """根据项目 ID 获取任务"""
        async with database.get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
                (project_id,),
            )
            row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_task(row)

    async def update(
        self,
        task: GenerationTask,
    ) -> GenerationTask:
        """更新任务"""
        task.updated_at = datetime.now()

        async with database.get_connection() as db:
            await db.execute(
                """
                UPDATE tasks
                SET stage = ?, progress = ?, current_scene = ?, total_scenes = ?, message = ?, error = ?, updated_at = ?
                WHERE id = ?
            """,
                (
                    task.stage.value,
                    task.progress,
                    task.current_scene,
                    task.total_scenes,
                    task.message,
                    task.error,
                    task.updated_at,
                    task.id,
                ),
            )
            await db.commit()

        return task

    async def update_progress(
        self,
        task_id: str,
        stage: TaskStage,
        progress: float,
        message: str = "",
        current_scene: Optional[int] = None,
        error: Optional[str] = None,
    ) -> Optional[GenerationTask]:
        """更新任务进度"""
        task = await self.get_by_id(task_id)
        if not task:
            return None

        task.stage = stage
        task.progress = progress
        task.message = message
        if current_scene is not None:
            task.current_scene = current_scene
        if error is not None:
            task.error = error

        return await self.update(task)

    async def delete(self, task_id: str) -> bool:
        """删除任务"""
        async with database.get_connection() as db:
            cursor = await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            await db.commit()

        return cursor.rowcount > 0

    def _row_to_task(self, row) -> GenerationTask:
        """将数据库行转换为 GenerationTask 对象"""
        data = dict(row)
        return GenerationTask(
            id=data["id"],
            project_id=data["project_id"],
            stage=TaskStage(data["stage"]),
            progress=data["progress"],
            current_scene=data["current_scene"],
            total_scenes=data["total_scenes"],
            message=data["message"] or "",
            error=data["error"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


# 全局仓库实例
task_repo = TaskRepository()
