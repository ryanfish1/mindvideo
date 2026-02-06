# AI 视频生成系统 V1.0 使用文档

## 📋 概述

这是一个使用 Pexels API + IndexTTS 的 AI 视频自动生成系统，可以根据文案自动匹配视频素材、生成语音并合成最终视频。

**生成流程：**
```
文案输入 → 智能匹配视频(Pexels) → 生成TTS音频(IndexTTS) → 合成视频 → 输出
```

---

## 🚀 快速开始

### 1. 环境要求

```bash
# Python 依赖
pip install -r requirements.txt

# 外部服务
- IndexTTS: 运行在 http://127.0.0.1:7861
- FFmpeg: 需要安装并加入 PATH
- Pexels API Key: 配置在 .env 文件中
```

### 2. 启动 IndexTTS 服务

```bash
cd G:\index\index-tts-windows
.venv\Scripts\python.exe indextts_server.py
```

### 3. 生成视频

```bash
cd D:\code\generation
python v1.0_generate_video.py
```

---

## 📝 配置说明

打开 `v1.0_generate_video.py`，修改配置区域：

### 修改文案

```python
SCRIPT = '''你的文案内容'''
```

### 修改分镜

在 `get_storyboard()` 函数中添加/修改场景：

```python
{
    "narration": "旁白文案",
    "keyword_hint": "关键词提示（用空格分隔）",
    "duration": 5.0  # 预期时长（秒）
}
```

### TTS 配置

| 参数 | 说明 | 可选值 |
|------|------|--------|
| TTS_EMOTION | 情感 | neutral, clean, happy, sad, angry |
| TTS_SPEED | 语速倍率 | 0.5 ~ 2.0 (1.0=正常) |
| TTS_VOLUME | 音量倍率 | 0.5 ~ 2.0 (1.0=正常) |

---

## 📁 项目结构

```
D:\code\generation\
├── v1.0_generate_video.py          # 主生成脚本
├── backend/
│   ├── services/
│   │   ├── video_matching.py      # Pexels API 视频匹配
│   │   └── ...
│   └── integrations/
│       └── indextts_client.py     # IndexTTS 客户端
├── storage/
│   ├── cache/                     # 临时文件
│   └── output/                    # 最终输出
└── .env                           # 环境配置
```

---

## 🔧 环境变量配置

在 `.env` 文件中配置：

```bash
# Pexels API (必需)
PEXELS_API_KEY=your_pexels_api_key_here

# LLM API (用于生成搜索关键词)
SILICONFLOW_API_KEY=your_siliconflow_key_here

# IndexTTS (自动配置)
INDEXTTS_URL=http://127.0.0.1:7861
INDEXTTS_REFERENCE_AUDIO=G:\index\index-tts-windows\prompts\my_voice.wav
```

---

## 🎬 生成步骤详解

### 步骤 1: 智能匹配视频

- 使用 LLM 分析文案，生成英文搜索关键词
- 从 Pexels API 搜索匹配视频
- 按分辨率、时长等指标选择最佳素材

### 步骤 2: 生成 TTS 音频

- 使用 IndexTTS 生成中文语音
- 支持情感、语速、音量调节
- 自动返回音频时长

### 步骤 3: 处理视频片段

- 精确裁剪到音频长度
- 重新编码 (H.264, 30fps)
- 移除原始音频

### 步骤 4: 合并音视频

- 使用 `-shortest` 确保音画同步
- AAC 编码音频

### 步骤 5: 拼接最终视频

- 使用 FFmpeg concat 协议
- 无损合并所有场景

---

## ⚙️ 故障排除

### IndexTTS 连接失败

```bash
# 检查服务是否运行
curl http://127.0.0.1:7861/health

# 预期输出
{"status":"healthy","model_loaded":true}
```

### Pexels API 无结果

- 检查 API Key 是否正确
- 尝试修改 `keyword_hint` 关键词
- 降低 `duration` 时长要求

### 视频卡顿/不同步

- 确保使用 `-c:v libx264 -preset medium` 重新编码
- 使用 `-shortest` 参数同步音视频

---

## 📊 输出示例

```
============================================================
AI 视频生成系统 V1.0
Emotion: neutral, Speed: 1.25x, Volume: 1.5x
============================================================

[1/4] 智能匹配视频 (12 个场景)...

[2/4] 生成 TTS 音频 (IndexTTS)...

[3/4] 处理视频片段...

[4/4] 合并音频到视频...

[5/5] 拼接最终视频...

============================================================
生成完成!
输出文件: D:\code\generation\storage\output\video_v1.0_20260206_215200.mp4
视频时长: 36.58s
场景数量: 12
============================================================
```

---

## 🔄 版本历史

- **V1.0** (2026-02-06): 初始版本
  - Pexels API 智能视频匹配
  - IndexTTS TTS 语音合成
  - FFmpeg 视频处理和合成

---

## 📞 技术支持

如有问题，请检查：
1. IndexTTS 服务是否正常运行
2. FFmpeg 是否正确安装
3. 网络连接是否正常
4. .env 配置是否正确
