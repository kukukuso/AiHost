# 🎮 AI抖音弹幕游戏主持人

> 一个低成本、高互动性的AI虚拟主持人，专门用于抖音平台的弹幕互动游戏直播

## 📋 目录

- [项目概述](#项目概述)
- [系统特性](#系统特性)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [API接入说明](#api接入说明)
- [使用教程](#使用教程)
- [故障排除](#故障排除)
- [更新日志](#更新日志)

## 🎯 项目概述

本项目是一个智能的抖音直播间弹幕互动助手，通过接入Qwen API实现智能对话，具备以下核心功能：

- **实时弹幕监听**：捕获直播间弹幕、礼物、用户进入等事件
- **智能AI回复**：基于Qwen API生成个性化、情境化的语音回复
- **多种人格设定**：支持活泼少女、幽默段子手、温柔大姐姐等多种AI人设
- **语音输出**：支持Edge-TTS等多种TTS引擎，实现自然流畅的语音播报
- **低成本运营**：主要使用云端API，无需高性能本地硬件

## ✨ 系统特性

### 🤖 智能交互
- **AI人格化回复**：根据预设人格生成符合角色特征的回复
- **场景感知**：识别弹幕内容、礼物类型，给出相应回应
- **情绪表达**：针对不同情况调整语调和情感

### 🎁 礼物互动
- **实时感谢**：收到礼物立即语音感谢
- **价值识别**：区分普通礼物和高价值礼物，给出不同程度的回应
- **个性化互动**：针对送礼用户进行特别互动

### 🎮 游戏主持
- **答题互动**：识别观众的游戏答案，给出评论和鼓励
- **游戏解说**：对游戏过程进行有趣的点评
- **氛围烘托**：通过语音营造直播间活跃氛围

### 🔧 技术特性
- **模块化设计**：各功能模块独立，易于扩展和维护
- **异步处理**：高效处理并发事件，低延迟响应
- **容错机制**：API失败时自动降级为预设回复
- **日志系统**：完整的运行日志，便于调试和监控

## 💻 环境要求

### 硬件要求
- **CPU**：双核心及以上
- **内存**：4GB及以上
- **网络**：稳定的互联网连接
- **音频设备**：用于语音播放的音响或耳机

### 软件要求
- **操作系统**：Windows 10/11、macOS 10.15+、Ubuntu 18.04+
- **Python**：3.7或更高版本
- **依赖库**：见 `requirements.txt`

### API服务
- **Qwen API**：阿里云DashScope API密钥（推荐）
- **Edge-TTS**：微软免费TTS服务（无需API密钥）

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/your-repo/ai-douyin-host.git
cd ai-douyin-host

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置设置

```bash
# 复制配置文件
cp .env.example .env
cp config.yaml config.yaml

# 编辑环境变量文件
# 在 .env 文件中设置你的API密钥
```

### 3. 基础配置

编辑 `.env` 文件：
```env
# 抖音直播间ID（必填）
DOUYIN_ROOM_ID=你的直播间ID

# Qwen API密钥（必填）
DASHSCOPE_API_KEY=你的DashScope API密钥
```

### 4. 启动测试

```bash
# 运行测试模式（使用模拟数据）
python main.py
```

如果看到以下输出，说明系统启动成功：
```
🎮 AI抖音弹幕游戏主持人
📧 作者: AI助手
🔗 项目: https://github.com/your-repo
--------------------------------------------------
✅ 直播间ID: 模拟模式
✅ Qwen API回复生成器初始化成功
🚀 AI主持人系统启动完成，开始监听直播间...
```

## ⚙️ 详细配置

### config.yaml 配置详解

```yaml
# AI人格设定
ai_personality:
  # 预设人格类型
  character_type: "活泼少女"  # 可选: 活泼少女、幽默段子手、温柔大姐姐、搞怪萌妹
  
  # 自定义人格（会覆盖预设类型）
  custom_personality: |
    你是一个充满活力的游戏主播助手，性格开朗活泼...
  
  # 语音风格
  voice_style: "甜美女声"

# 抖音直播间设置
douyin_live:
  room_id: "YOUR_ROOM_ID_HERE"  # 必填：你的直播间房间号
  max_retries: 3                # 连接重试次数
  heartbeat_interval: 30        # 心跳间隔（秒）

# AI模型设置
model_config:
  primary_model: "qwen-api"     # 使用API模式
  
  qwen_api:
    provider: "dashscope"       # API提供商
    model_name: "qwen-plus"     # 模型名称
    
  max_tokens: 150               # 最大生成长度
  temperature: 0.8              # 创意度
  top_p: 0.9                   # 多样性
```

### 人格设定详细说明

#### 预设人格类型

1. **活泼少女**
   - 特点：开朗活泼，说话风趣幽默
   - 常用词汇："哇！"、"太棒了！"、"小伙伴们"
   - 适合：游戏直播、娱乐互动

2. **幽默段子手**
   - 特点：风趣幽默，擅长说段子和吐槽
   - 常用词汇：网络流行语，搞笑表达
   - 适合：脱口秀、搞笑内容

3. **温柔大姐姐**
   - 特点：温和耐心，声音温暖
   - 常用词汇："亲爱的"、"小可爱"、"没关系"
   - 适合：教学直播、安慰互动

4. **搞怪萌妹**
   - 特点：天真可爱，说话呆萌
   - 常用词汇："诶？"、"哈？"、"好奇怪呀"
   - 适合：萌系内容、可爱互动

#### 自定义人格

你可以通过 `custom_personality` 字段完全自定义AI的人格特征：

```yaml
custom_personality: |
  你是一个专业的游戏解说员，对各种游戏都很了解。
  你说话幽默风趣，经常用游戏术语，喜欢和观众开玩笑。
  当观众答错题目时，你会用轻松的方式化解尴尬。
  你的回复要简洁有力，充满游戏梗。
```

## 🔗 API接入说明

### DashScope API 申请

1. **注册阿里云账号**
   - 访问 [阿里云官网](https://www.aliyun.com/)
   - 注册并完成实名认证

2. **开通DashScope服务**
   - 访问 [DashScope控制台](https://dashscope.console.aliyun.com/)
   - 开通服务并获取API密钥

3. **选择合适的模型**
   - `qwen-turbo`：速度快，成本低，适合高频交互
   - `qwen-plus`：平衡性能，推荐使用
   - `qwen-max`：最高质量，成本较高

### API成本估算

以DashScope为例（价格可能变动，请以官网为准）：

| 模型 | 输入价格 | 输出价格 | 适用场景 |
|------|----------|----------|----------|
| qwen-turbo | ¥0.3/千tokens | ¥0.6/千tokens | 高频互动 |
| qwen-plus | ¥2/千tokens | ¥6/千tokens | 日常使用 |
| qwen-max | ¥20/千tokens | ¥60/千tokens | 高质量回复 |

**成本优化建议**：
- 使用 `qwen-turbo` 进行日常互动
- 限制回复长度（30字以内）
- 设置合理的回复频率
- 启用缓存机制避免重复生成

## 📖 使用教程

### 第一次运行

1. **配置检查**
```bash
# 检查配置文件
python -c "import yaml; print(yaml.safe_load(open('config.yaml')))"
```

2. **API测试**
```bash
# 测试Qwen API连接
python qwen_api.py
```

3. **启动系统**
```bash
python main.py
```

### 实际直播使用

1. **获取直播间ID**
   - 打开你的抖音直播间
   - 从URL中提取房间号
   - 配置到 `config.yaml` 或 `.env` 文件

2. **调整回复频率**
```yaml
interaction:
  comment_reply:
    reply_probability: 0.3  # 30%的概率回复弹幕
```

3. **设置礼物阈值**
```yaml
interaction:
  gift_thanks:
    expensive_gift_threshold: 1000  # 超过1000抖币算高价值礼物
```

### 监控和调试

1. **查看日志**
```bash
# 实时查看日志
tail -f logs/ai_host.log
```

2. **性能监控**
   - 系统会每30秒输出运行统计
   - 包括处理的弹幕数、礼物数、回复数等

3. **调试模式**
```yaml
system:
  debug_mode: true
  log_level: "DEBUG"
```

## 🛠️ 故障排除

### 常见问题

#### 1. API密钥错误
**现象**：`API调用失败: 401 Unauthorized`
**解决**：
- 检查 `.env` 文件中的 `DASHSCOPE_API_KEY` 是否正确
- 确认API密钥未过期
- 检查账户余额是否充足

#### 2. 直播间连接失败
**现象**：`WebSocket连接失败`
**解决**：
- 确认直播间ID正确
- 检查网络连接
- 尝试使用模拟模式测试

#### 3. 音频播放失败
**现象**：`音频播放失败`
**解决**：
```bash
# 安装音频驱动
# Windows: 确保安装了音频设备驱动
# macOS: 检查系统音频设置
# Linux: 安装ALSA或PulseAudio
sudo apt-get install alsa-utils pulseaudio
```

#### 4. 依赖安装失败
**现象**：`pip install` 报错
**解决**：
```bash
# 更新pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 分别安装问题依赖
pip install dashscope
pip install edge-tts
```

### 日志分析

常见日志信息含义：

```
✅ API连接测试成功          # API工作正常
⚠️ API连接测试失败         # 需要检查API配置
🔧 使用模拟模式            # 未配置直播间ID，在测试模式
📊 系统运行状态            # 定期输出的统计信息
❌ 组件健康检查失败        # 系统组件异常，需要重启
```

### 性能优化

1. **降低API调用频率**
```yaml
interaction:
  comment_reply:
    reply_probability: 0.2  # 从0.3降到0.2
```

2. **启用音频缓存**
```yaml
audio_output:
  audio_cache_size: 100     # 增加缓存大小
```

3. **调整超时时间**
```yaml
model_config:
  timeout: 5                # 减少超时时间
```

## 📅 更新日志

### v1.0.0 (2024-01-15)
- ✨ 首次发布
- 🤖 集成Qwen API智能回复
- 🎵 支持Edge-TTS语音合成
- 📱 实现抖音直播间数据监听
- 🎭 多种AI人格预设
- 📊 完整的监控和统计系统

### 计划中的功能
- 🎮 更多游戏类型支持
- 🔊 更多TTS引擎选择
- 📈 数据分析和报表
- 🌐 Web管理界面
- 🤝 多平台支持（B站、快手等）

## 💡 高级使用技巧

### 1. 人格调教

通过与AI的互动，你可以观察并调整人格设定：

```yaml
custom_personality: |
  你是一个资深游戏玩家，对FPS游戏特别了解。
  你说话直接，喜欢用"兄弟"、"老铁"这样的称呼。
  当有人问游戏技巧时，你会给出专业建议。
  遇到萌新时，你会耐心指导。
```

### 2. 场景定制

针对不同类型的直播，调整AI的回复策略：

**教学类直播**：
```yaml
interaction:
  comment_reply:
    trigger_keywords:
      - "怎么"
      - "为什么"
      - "不懂"
      - "教教我"
```

**娱乐类直播**：
```yaml
interaction:
  comment_reply:
    trigger_keywords:
      - "666"
      - "哈哈"
      - "笑死"
      - "有趣"
```

### 3. 动态调整

系统运行过程中，你可以通过修改配置文件并重启来调整行为，无需重新部署。

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发环境搭建
```bash
git clone https://github.com/your-repo/ai-douyin-host.git
cd ai-douyin-host
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖
```

### 代码规范
- 使用Python 3.7+语法
- 遵循PEP 8代码风格
- 添加必要的类型注解
- 编写详细的文档字符串

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系我们

- 📧 邮箱：your-email@example.com
- 💬 QQ群：123456789
- 🐛 问题反馈：[GitHub Issues](https://github.com/your-repo/issues)

---

<div align="center">

**🎉 感谢使用 AI抖音弹幕游戏主持人！**

如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！

</div>