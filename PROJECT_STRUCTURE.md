# AI 视频生成系统 V1.0

## 项目结构（清理后）

```
D:\code\generation\
├── v1.0_generate_video.py       # 主生成脚本 ⭐
├── README_V1.0.md                # 使用文档 📖
├── backend/                      # 核心服务模块
│   ├── services/
│   │   ├── video_matching.py   # Pexels API 视频匹配
│   │   └── audio_synthesis.py  # 音频生成服务
│   ├── integrations/
│   │   ├── indextts_client.py  # IndexTTS 客户端
│   │   └── deepseek_client.py  # LLM 客户端
│   └── config.py                # 配置管理
├── storage/
│   ├── cache/                   # 临时缓存
│   └── output/                  # 最终输出
├── frontend/                     # Web 界面（可选）
├── .env                          # 环境配置
└── requirements.txt             # Python 依赖
```

## 快速开始

```bash
# 1. 启动 IndexTTS 服务
cd G:\index\index-tts-windows
.venv\Scripts\python.exe indextts_server.py

# 2. 生成视频
cd D:\code\generation
python v1.0_generate_video.py
```

## 核心功能

| 功能 | 技术栈 |
|------|--------|
| 视频素材匹配 | Pexels API + LLM |
| 语音合成 | IndexTTS |
| 视频处理 | FFmpeg |
| AI 分析 | DeepSeek API |

## 配置要求

- **Pexels API Key**: 在 `.env` 中配置
- **IndexTTS**: 运行在 `http://127.0.0.1:7861`
- **FFmpeg**: 需要安装并加入 PATH

详细说明请查看 [README_V1.0.md](README_V1.0.md)

## 版本

- **V1.0** (2026-02-06): 初始稳定版本
  - 成功输出: anchoring_effect_v1.1.mp4 (25.1 MB, 36.6s)
  - 12 场景完整流程
