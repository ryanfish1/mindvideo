"""
项目数据仓库

处理项目的数据库 CRUD 操作
"""

import json
from datetime import datetime
from typing import Optional

from loguru import logger
from pydantic import ValidationError

from ..database import database
from ..models import Project, ProjectDB, ProjectStatus, Storyboard


class ProjectRepository:
    """项目数据仓库"""

    async def create(self, project: Project) -> Project:
        """创建项目"""
        async with database.get_connection() as db:
            await db.execute(
                """
                INSERT INTO projects (id, name, description, script, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    project.id,
                    project.name,
                    project.description,
                    project.script,
                    project.status.value,
                    project.created_at,
                    project.updated_at,
                ),
            )
            await db.commit()

        logger.info(f"Project created: {project.id}")
        return project

    async def get_by_id(self, project_id: str) -> Optional[Project]:
        """根据 ID 获取项目"""
        async with database.get_connection() as db:
            cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_project(row)

    async def list(
        self,
        status: Optional[ProjectStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Project]:
        """获取项目列表"""
        async with database.get_connection() as db:
            if status:
                cursor = await db.execute(
                    "SELECT * FROM projects WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (status.value, limit, offset),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM projects ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            rows = await cursor.fetchall()

        return [self._row_to_project(row) for row in rows]

    async def count(self, status: Optional[ProjectStatus] = None) -> int:
        """统计项目数量"""
        async with database.get_connection() as db:
            if status:
                cursor = await db.execute("SELECT COUNT(*) FROM projects WHERE status = ?", (status.value,))
            else:
                cursor = await db.execute("SELECT COUNT(*) FROM projects")
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def update(self, project: Project) -> Project:
        """更新项目"""
        project.updated_at = datetime.now()

        async with database.get_connection() as db:
            await db.execute(
                """
                UPDATE projects
                SET name = ?, description = ?, script = ?, status = ?,
                    video_output_path = ?, error_message = ?, storyboard_data = ?, updated_at = ?
                WHERE id = ?
            """,
                (
                    project.name,
                    project.description,
                    project.script,
                    project.status.value,
                    project.video_output_path,
                    project.error_message,
                    json.dumps(project.storyboard.model_dump()) if project.storyboard else None,
                    project.updated_at,
                    project.id,
                ),
            )
            await db.commit()

        logger.info(f"Project updated: {project.id}")
        return project

    async def delete(self, project_id: str) -> bool:
        """删除项目"""
        async with database.get_connection() as db:
            cursor = await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            await db.commit()

        if cursor.rowcount > 0:
            logger.info(f"Project deleted: {project_id}")
            return True
        return False

    async def update_status(
        self,
        project_id: str,
        status: ProjectStatus,
        error_message: Optional[str] = None,
    ) -> Optional[Project]:
        """更新项目状态"""
        project = await self.get_by_id(project_id)
        if not project:
            return None

        project.status = status
        project.error_message = error_message
        return await self.update(project)

    async def update_storyboard(self, project_id: str, storyboard: Storyboard) -> Optional[Project]:
        """更新项目分镜"""
        project = await self.get_by_id(project_id)
        if not project:
            return None

        project.storyboard = storyboard
        project.status = ProjectStatus.READY
        return await self.update(project)

    async def set_video_output(self, project_id: str, video_path: str) -> Optional[Project]:
        """设置视频输出路径"""
        project = await self.get_by_id(project_id)
        if not project:
            return None

        project.video_output_path = video_path
        project.status = ProjectStatus.COMPLETED
        return await self.update(project)

    def _row_to_project(self, row) -> Project:
        """将数据库行转换为 Project 对象"""
        data = dict(row)

        # 解析分镜数据
        storyboard_data = data.pop("storyboard_data", None)
        storyboard = None
        if storyboard_data:
            try:
                storyboard_dict = json.loads(storyboard_data)
                storyboard = Storyboard(**storyboard_dict)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Failed to parse storyboard data: {e}")

        return Project(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            script=data["script"],
            storyboard=storyboard,
            video_output_path=data["video_output_path"],
            status=ProjectStatus(data["status"]),
            error_message=data["error_message"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


# 全局仓库实例
project_repo = ProjectRepository()
