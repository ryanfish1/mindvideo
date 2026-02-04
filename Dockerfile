# MindVideo with IndexTTS - Docker方案
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY backend/ backend/
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# IndexTTS模型和数据目录（挂载卷）
VOLUME ["/app/index-model", "/app/storage"]

# 暴露端口
EXPOSE 8000 7861

# 启动命令（同时启动IndexTTS服务和应用）
CMD python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
