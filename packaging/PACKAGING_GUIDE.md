# MindVideo 打包部署指南

## 项目结构

```
MindVideo/
├── backend/              # 应用代码
│   ├── services/        # 视频匹配、生成服务
│   ├── integrations/    # IndexTTS客户端
│   └── config.py        # 配置文件
├── storage/             # 输出目录
├── packaging/           # 打包脚本
└── [IndexTTS模型]       # 外部依赖 (4.4GB)
```

## IndexTTS 模型说明

IndexTTS 是一个深度学习语音合成模型，包含以下大文件：

| 文件 | 大小 | 说明 |
|------|------|------|
| checkpoints/gpt.pth | 3.3GB | GPT模型权重 |
| checkpoints/s2mel.pth | 1.2GB | 声音转换模型 |
| 总计 | **~4.4GB** | 无法打包进exe |

---

## 方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **Docker容器** | 环境一致、部署简单 | 需要Docker | 服务器部署 |
| **PyInstaller** | 单文件分发 | 模型需外部配置 | 个人用户 |
| **独立服务** | 解耦、可扩展 | 架构复杂 | 多用户 |

---

## 方案1：Docker容器（推荐服务器部署）

### 步骤

1. **构建镜像**
```bash
docker build -t mindvideo:latest .
```

2. **启动服务**
```bash
docker-compose up -d
```

3. **访问**
- 应用: http://localhost:8000
- IndexTTS: http://localhost:7861

### 配置文件

`docker-compose.yml` 已配置：
- 端口映射
- 目录挂载（模型、存储）
- 服务编排

---

## 方案2：PyInstaller打包（推荐个人用户）

### 步骤

1. **安装PyInstaller**
```bash
pip install pyinstaller
```

2. **执行打包**
```bash
cd D:/code/generation
python packaging/pyinstaller_build.py
```

3. **分发目录结构**
```
dist/
├── MindVideo.exe          # 主程序
├── install.bat            # 安装脚本
└── README.txt             # 用户说明
```

### 用户安装流程

1. 解压到任意目录
2. 运行 `install.bat`
3. 按提示输入IndexTTS模型路径
4. 自动启动服务

---

## 方案3：独立服务部署

### 架构

```
┌─────────────┐      HTTP      ┌──────────────┐
│  MindVideo  │ ──────────────> │ IndexTTS API │
│  (端口8000) │ ◄────────────── │  (端口7861)  │
└─────────────┘                └──────────────┘
       ▲                              ▲
       │                              │
    用户访问                      模型服务
```

### 部署步骤

1. **IndexTTS服务**（作为Windows服务）
```bash
# 使用NSSM注册为系统服务
nssm install IndexTTS python "G:\index\index-tts-windows\indextts_server.py"
nssm start IndexTTS
```

2. **MindVideo应用**（作为Web服务）
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

3. **前端界面**（可选）
- 打包为React/静态页面
- 通过8000端口API访问

---

## 配置文件

### backend/config.py
```python
# IndexTTS配置
INDEX_TTS_HOST: str = "127.0.0.1"
INDEX_TTS_PORT: int = 7861

# 存储路径
STORAGE_DIR: Path = Path("storage")
CACHE_DIR: Path = STORAGE_DIR / "cache"
OUTPUT_DIR: Path = STORAGE_DIR / "output"
```

### .env
```
# IndexTTS模型路径（可选，默认使用内置）
INDEX_TTS_PATH=G:/index/index-tts-windows

# API密钥
PEXELS_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here
```

---

## 常见问题

### Q1: IndexTTS模型太大怎么办？
A: 方案1和方案2都支持外部挂载模型路径，不需要打包进程序。

### Q2: 如何在没有Python环境运行？
A: 使用PyInstaller打包的exe是独立的，不需要Python环境。

### Q3: 可以部署到云端吗？
A: 可以。Docker方案最适合云部署（阿里云、AWS等）。

### Q4: 多用户怎么处理？
A: 建议使用独立服务方案，IndexTTS服务可同时处理多个请求。

---

## 推荐方案

| 场景 | 推荐方案 |
|------|----------|
| 个人电脑使用 | PyInstaller打包 |
| 公司内部服务器 | Docker容器 |
| 公网云服务 | Docker + Nginx |
| 分发给客户 | PyInstaller + 安装脚本 |
