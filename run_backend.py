"""
MindVideo 后端启动脚本
"""
import uvicorn

if __name__ == "__main__":
    from backend.config import settings

    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
