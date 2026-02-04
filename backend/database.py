"""
数据库模块

SQLite 数据库设置和连接管理
"""

import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from .config import settings


class Database:
    """数据库管理器"""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def init(self) -> None:
        """初始化数据库，创建表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    script TEXT NOT NULL,
                    storyboard_data TEXT,
                    video_output_path TEXT,
                    status TEXT NOT NULL DEFAULT 'draft',
                    error_message TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0.0,
                    current_scene INTEGER,
                    total_scenes INTEGER NOT NULL DEFAULT 0,
                    message TEXT,
                    error TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """
            )

            # 创建索引
            await db.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)")

            await db.commit()

    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接上下文管理器"""
        async with aiosqlite.connect(self.db_path) as db:
            # 启用外键约束
            await db.execute("PRAGMA foreign_keys = ON")
            # 返回行作为字典
            db.row_factory = aiosqlite.Row
            yield db


# 全局数据库实例
db_path = settings.STORAGE_PATH / "mindvideo.db"
database = Database(db_path)


async def init_database() -> None:
    """初始化数据库"""
    await database.init()


async def get_db() -> Database:
    """获取数据库实例（依赖注入用）"""
    return database
