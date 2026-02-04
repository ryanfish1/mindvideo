# MindVideo

AI驱动的认知科普视频生成系统

基于 DeepSeek + IndexTTS + Pexels + FFmpeg 的自动化视频生成工具。

## 功能特点

- 🎬 **智能视频匹配** - AI理解文案语义，自动匹配合适的Pexels素材
- 🗣️ **IndexTTS语音合成** - 本地模型，高质量情感语音
- 🎯 **关键词智能匹配** - AI生成搜索查询，精准匹配视频内容
- ⚡ **语速/音量调节** - 灵活控制语音参数（1.25x语速、1.5x音量）
- 🎭 **情感控制** - 支持中性、开心、悲伤等多种情感
- 🎬 **自动拼接** - 精确裁剪、同步音频视频，一键合成

## 系统要求

- Python 3.10+
- FFmpeg 8.0+
- 8GB+ RAM
- IndexTTS模型（可选，约23GB）

## 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone https://github.com/yourusername/mindvideo.git
cd mindvideo

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入 API 密钥
# PEXELS_API_KEY=your_key
# DEEPSEEK_API_KEY=your_key
```

### 3. 启动服务

**方式1：使用启动脚本（推荐）**
```bash
# Windows
packaging/start_services.bat
```

**方式2：手动启动**
```bash
# 启动IndexTTS服务（如果使用本地模型）
cd G:/index/index-tts-windows
python indextts_server.py --port 7861

# 启动MindVideo应用
cd D:/code/generation
python -m uvicorn backend.main:app --reload
```

访问：http://localhost:8000 | API文档：http://localhost:8000/docs

## 使用示例

### 生成视频脚本

```python
import asyncio
from pathlib import Path
from backend.services.video_matching import video_matching_service
from backend.integrations.indextts_client import indextts_client

async def generate_video():
    # 文案
    script = "你这辈子花的每一笔冤枉钱..."

    # 1. 智能匹配视频
    match = await video_matching_service.find_best_match(
        narration=script,
        text_overlay="",
        preferred_duration=5.0
    )

    # 2. 生成语音
    audio_path = await indextts_client.synthesize(
        text=script,
        emotion="neutral",
        speed=1.25,
        volume=1.5
    )

    print(f"视频已生成")

asyncio.run(generate_video())
```

### 使用预设脚本

直接运行项目中的生成脚本：

```bash
# 锚定效应视频
python generate_anchoring_fixed.py

# 省钱技巧视频
python generate_money_saving.py
```

## 项目结构

```
mindvideo/
├── backend/
│   ├── api/               # API 路由
│   ├── services/          # 核心服务（视频匹配、生成）
│   ├── integrations/      # 第三方集成
│   └── main.py            # FastAPI 入口
├── storage/               # 存储目录
│   ├── cache/             # 缓存
│   ├── output/            # 输出视频
│   └── projects/          # 项目文件
├── packaging/             # 打包脚本
├── generate_*.py          # 生成脚本示例
├── requirements.txt       # Python 依赖
└── .env.example          # 环境变量模板
```

## 配置说明

### IndexTTS模型（可选）

IndexTTS是本地深度学习模型，如需使用：

1. 下载 [IndexTTS](https://github.com/FisherWY/Index-1.9B-Character)
2. 在 `.env` 配置路径：
```env
INDEX_TTS_PATH=G:/index/index-tts-windows
```

### API密钥获取

- **Pexels**（免费视频素材）: https://www.pexels.com/api/
- **DeepSeek**（AI语义理解）: https://platform.deepseek.com/

## V1.1 版本特性

- ✅ 精确视频裁剪 - 视频长度完全匹配音频
- ✅ 关键词智能匹配 - AI理解文案语义生成搜索查询
- ✅ 重新编码防卡顿 - 统一30fps帧率
- ✅ 中性情感 - calm/neutral语调
- ✅ 语速1.25x + 音量1.5x

## 成本估算

单视频成本（30-60秒）：

| 项目 | 成本 |
|------|------|
| Pexels视频素材 | ¥0（免费） |
| IndexTTS语音 | ¥0（本地） |
| FFmpeg处理 | ¥0（本地） |
| DeepSeek API | ¥0.01-0.02 |
| **总计** | **< ¥0.05** |

## 打包部署

详细打包说明见：[packaging/PACKAGING_GUIDE.md](packaging/PACKAGING_GUIDE.md)

- Docker容器（服务器部署）
- PyInstaller打包（个人用户）
- Windows服务脚本（本地开发）

## 开发路线

- [ ] Web前端界面
- [ ] 视频预览功能
- [ ] 批量生成
- [ ] 更多TTS引擎支持
- [ ] 字幕自动生成

## 常见问题

**Q: IndexTTS模型太大怎么办（23GB）？**

A: 模型作为外部依赖，不打包进程序。使用Docker或配置外部路径即可。

**Q: Pexels视频不够用？**

A: Pexels提供海量免费高质量视频，支持商业使用。也可以接入其他素材源。

**Q: 如何调整语音效果？**

A: 修改 `generate_*.py` 中的配置：
```python
TTS_EMOTION = "neutral"  # clean, neutral, happy, sad, angry
TTS_SPEED = 1.25
TTS_VOLUME = 1.5
```

## 许可证

MIT License

## 许可证

MIT License

## 致谢

- [IndexTTS](https://github.com/FisherWY/Index-1.9B-Character) - 语音合成模型
- [Pexels](https://www.pexels.com/) - 免费视频素材
- [DeepSeek](https://www.deepseek.com/) - AI语义理解
- [FFmpeg](https://ffmpeg.org/) - 视频处理
