#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音输出系统
功能：TTS语音合成、音频播放、语音缓存
"""

import os
import time
import threading
import queue
import hashlib
from typing import Dict, Optional, Callable
from loguru import logger
import asyncio

# 音频处理库
try:
    import pyaudio
    import wave
    import soundfile as sf
    from pydub import AudioSegment
    from pydub.playback import play
    HAS_AUDIO_LIBS = True
except ImportError as e:
    logger.warning(f"音频库导入失败: {e}")
    HAS_AUDIO_LIBS = False

# TTS引擎导入
try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    logger.warning("Edge-TTS 未安装，将使用其他TTS引擎")
    HAS_EDGE_TTS = False


class AudioOutputManager:
    """音频输出管理器"""
    
    def __init__(self, config: Dict):
        """
        初始化音频输出管理器
        
        Args:
            config: 音频配置参数
        """
        self.config = config
        self.audio_config = config.get('audio_output', {})
        self.model_config = config.get('model_config', {})
        
        # 音频设备配置
        self.device_index = self.audio_config.get('device_index', None)
        self.sample_rate = self.audio_config.get('sample_rate', 22050)
        self.channels = self.audio_config.get('channels', 1)
        self.chunk_size = self.audio_config.get('chunk_size', 1024)
        
        # 语音缓存设置
        self.cache_dir = "audio_cache"
        self.cache_size = self.audio_config.get('audio_cache_size', 50)
        self.save_audio_files = config.get('system', {}).get('save_audio_files', False)
        
        # 创建缓存目录
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # 音频播放队列
        self.play_queue = queue.Queue()
        self.is_running = False
        self.play_thread = None
        
        # TTS引擎选择
        self.primary_tts = self._init_primary_tts()
        self.fallback_tts = self._init_fallback_tts()
        
        # PyAudio实例
        self.audio_instance = None
        if HAS_AUDIO_LIBS:
            try:
                self.audio_instance = pyaudio.PyAudio()
                logger.info("PyAudio初始化成功")
            except Exception as e:
                logger.error(f"PyAudio初始化失败: {e}")
        
        logger.info("音频输出管理器初始化完成")
    
    def _init_primary_tts(self):
        """初始化主要TTS引擎"""
        primary_model = self.model_config.get('primary_model', 'qwen2.5-omni')
        
        if primary_model == 'qwen2.5-omni':
            # 尝试初始化Qwen2.5-Omni模型
            try:
                tts_engine = Qwen25OmniTTS(self.model_config)
                logger.info("Qwen2.5-Omni TTS引擎初始化成功")
                return tts_engine
            except Exception as e:
                logger.warning(f"Qwen2.5-Omni TTS初始化失败: {e}")
                return None
        else:
            logger.warning(f"未知的主要TTS模型: {primary_model}")
            return None
    
    def _init_fallback_tts(self):
        """初始化备用TTS引擎"""
        fallback_model = self.model_config.get('fallback_tts', 'edge-tts')
        
        if fallback_model == 'edge-tts' and HAS_EDGE_TTS:
            tts_engine = EdgeTTS(self.audio_config)
            logger.info("Edge-TTS 备用引擎初始化成功")
            return tts_engine
        else:
            # 创建一个简单的模拟TTS
            tts_engine = MockTTS(self.audio_config)
            logger.info("模拟TTS引擎初始化成功")
            return tts_engine
    
    def start(self):
        """启动音频输出系统"""
        if self.is_running:
            logger.warning("音频输出系统已经在运行")
            return
        
        self.is_running = True
        
        # 启动音频播放线程
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
        
        logger.info("音频输出系统已启动")
    
    def stop(self):
        """停止音频输出系统"""
        self.is_running = False
        if self.play_thread:
            self.play_thread.join(timeout=5)
        
        if self.audio_instance:
            self.audio_instance.terminate()
        
        logger.info("音频输出系统已停止")
    
    def speak(self, text: str, priority: bool = False):
        """
        将文本转换为语音并播放
        
        Args:
            text: 要转换的文本
            priority: 是否为高优先级（插队播放）
        """
        try:
            if not text.strip():
                return
            
            # 生成音频
            audio_data = self._generate_audio(text)
            if audio_data:
                # 添加到播放队列
                if priority:
                    # 优先级播放：插入队列前端
                    temp_queue = queue.Queue()
                    temp_queue.put(audio_data)
                    while not self.play_queue.empty():
                        temp_queue.put(self.play_queue.get())
                    self.play_queue = temp_queue
                else:
                    # 正常播放：添加到队列末尾
                    self.play_queue.put(audio_data)
                
                logger.info(f"语音已加入播放队列: {text[:30]}...")
            
        except Exception as e:
            logger.error(f"语音合成失败: {e}")
    
    def _generate_audio(self, text: str) -> Optional[bytes]:
        """
        生成音频数据
        
        Args:
            text: 输入文本
            
        Returns:
            音频数据（bytes）或None
        """
        try:
            # 检查缓存
            cache_key = self._get_cache_key(text)
            cached_audio = self._get_cached_audio(cache_key)
            if cached_audio:
                logger.debug(f"使用缓存音频: {text[:30]}...")
                return cached_audio
            
            # 尝试主要TTS引擎
            audio_data = None
            if self.primary_tts:
                try:
                    audio_data = self.primary_tts.synthesize(text)
                    logger.debug("使用主要TTS引擎生成音频")
                except Exception as e:
                    logger.warning(f"主要TTS引擎失败: {e}")
            
            # 如果主要引擎失败，使用备用引擎
            if not audio_data and self.fallback_tts:
                try:
                    audio_data = self.fallback_tts.synthesize(text)
                    logger.debug("使用备用TTS引擎生成音频")
                except Exception as e:
                    logger.error(f"备用TTS引擎失败: {e}")
            
            # 缓存音频
            if audio_data:
                self._cache_audio(cache_key, audio_data)
                
                # 保存音频文件（如果启用）
                if self.save_audio_files:
                    self._save_audio_file(text, audio_data)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"音频生成失败: {e}")
            return None
    
    def _play_loop(self):
        """音频播放主循环"""
        while self.is_running:
            try:
                # 从队列获取音频数据
                try:
                    audio_data = self.play_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # 播放音频
                self._play_audio(audio_data)
                
                # 标记任务完成
                self.play_queue.task_done()
                
            except Exception as e:
                logger.error(f"音频播放循环错误: {e}")
                time.sleep(0.1)
    
    def _play_audio(self, audio_data: bytes):
        """
        播放音频数据
        
        Args:
            audio_data: 音频数据
        """
        try:
            if not HAS_AUDIO_LIBS:
                logger.warning("音频库未安装，无法播放音频")
                return
            
            # 这里可以根据音频数据格式选择不同的播放方式
            # 简化实现：假设音频数据是WAV格式
            
            # 保存为临时文件并播放
            temp_file = f"{self.cache_dir}/temp_play.wav"
            with open(temp_file, 'wb') as f:
                f.write(audio_data)
            
            # 使用pydub播放音频
            try:
                audio = AudioSegment.from_wav(temp_file)
                play(audio)
                logger.debug("音频播放完成")
            except Exception as e:
                logger.error(f"音频播放失败: {e}")
            finally:
                # 清理临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
        except Exception as e:
            logger.error(f"音频播放错误: {e}")
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        # 使用文本和语音配置生成哈希键
        voice_style = self.config.get('ai_personality', {}).get('voice_style', 'default')
        cache_string = f"{text}_{voice_style}_{self.sample_rate}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_cached_audio(self, cache_key: str) -> Optional[bytes]:
        """获取缓存的音频"""
        cache_file = f"{self.cache_dir}/{cache_key}.wav"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"读取缓存音频失败: {e}")
        return None
    
    def _cache_audio(self, cache_key: str, audio_data: bytes):
        """缓存音频数据"""
        try:
            cache_file = f"{self.cache_dir}/{cache_key}.wav"
            with open(cache_file, 'wb') as f:
                f.write(audio_data)
            
            # 清理过期缓存
            self._cleanup_cache()
            
        except Exception as e:
            logger.error(f"缓存音频失败: {e}")
    
    def _cleanup_cache(self):
        """清理过期缓存"""
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.wav')]
            if len(cache_files) > self.cache_size:
                # 按修改时间排序，删除最旧的文件
                cache_files.sort(key=lambda x: os.path.getmtime(f"{self.cache_dir}/{x}"))
                files_to_delete = cache_files[:-self.cache_size]
                
                for file_name in files_to_delete:
                    file_path = f"{self.cache_dir}/{file_name}"
                    os.remove(file_path)
                    logger.debug(f"删除过期缓存: {file_name}")
                    
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
    
    def _save_audio_file(self, text: str, audio_data: bytes):
        """保存音频文件（用于调试）"""
        try:
            timestamp = int(time.time())
            filename = f"audio_{timestamp}_{text[:10].replace(' ', '_')}.wav"
            filepath = f"{self.cache_dir}/{filename}"
            
            with open(filepath, 'wb') as f:
                f.write(audio_data)
            
            logger.debug(f"音频文件已保存: {filepath}")
            
        except Exception as e:
            logger.error(f"保存音频文件失败: {e}")


class Qwen25OmniTTS:
    """Qwen2.5-Omni TTS引擎"""
    
    def __init__(self, config: Dict):
        """
        初始化Qwen2.5-Omni TTS引擎
        
        Args:
            config: 模型配置
        """
        self.config = config
        self.model_path = config.get('model_path', './models')
        self.device = config.get('device', 'auto')
        
        # 这里应该初始化Qwen2.5-Omni模型
        # 由于模型较大，这里提供一个模拟实现
        logger.warning("Qwen2.5-Omni 模型初始化 - 当前为模拟实现")
        
        # 实际使用时的初始化代码示例：
        # from transformers import AutoModel, AutoTokenizer
        # self.model = AutoModel.from_pretrained(self.model_path)
        # self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        
    def synthesize(self, text: str) -> bytes:
        """
        合成语音
        
        Args:
            text: 输入文本
            
        Returns:
            音频数据（WAV格式）
        """
        try:
            # 这里应该调用Qwen2.5-Omni模型进行语音合成
            # 当前提供模拟实现
            
            logger.info(f"[模拟] Qwen2.5-Omni 正在合成语音: {text}")
            
            # 实际使用时的代码示例：
            # inputs = self.tokenizer(text, return_tensors="pt")
            # with torch.no_grad():
            #     audio_output = self.model.generate_speech(inputs, voice_style="甜美女声")
            # return audio_output.cpu().numpy().tobytes()
            
            # 模拟返回空的WAV文件头
            import struct
            
            # 简单的WAV文件头（44字节）
            sample_rate = 22050
            channels = 1
            bits_per_sample = 16
            duration = len(text) * 0.1  # 简单估算时长
            num_samples = int(sample_rate * duration)
            
            wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
                b'RIFF',
                36 + num_samples * channels * bits_per_sample // 8,
                b'WAVE',
                b'fmt ',
                16,  # PCM
                1,   # format
                channels,
                sample_rate,
                sample_rate * channels * bits_per_sample // 8,
                channels * bits_per_sample // 8,
                bits_per_sample,
                b'data',
                num_samples * channels * bits_per_sample // 8
            )
            
            # 生成静音数据（实际应该是合成的语音）
            audio_data = b'\x00' * (num_samples * channels * bits_per_sample // 8)
            
            return wav_header + audio_data
            
        except Exception as e:
            logger.error(f"Qwen2.5-Omni 语音合成失败: {e}")
            raise


class EdgeTTS:
    """Edge-TTS引擎"""
    
    def __init__(self, config: Dict):
        """
        初始化Edge-TTS引擎
        
        Args:
            config: 音频配置
        """
        self.config = config
        
        # Edge-TTS 语音配置
        voice_style = config.get('voice_style', '甜美女声')
        self.voice = self._get_edge_voice(voice_style)
        
        logger.info(f"Edge-TTS 引擎初始化，使用语音: {self.voice}")
    
    def _get_edge_voice(self, voice_style: str) -> str:
        """根据语音风格选择Edge-TTS语音"""
        voice_map = {
            '甜美女声': 'zh-CN-XiaoxiaoNeural',
            '活泼女声': 'zh-CN-XiaomoNeural',
            '温柔女声': 'zh-CN-XiaoyouNeural',
            '中性声音': 'zh-CN-YunxiNeural'
        }
        return voice_map.get(voice_style, 'zh-CN-XiaoxiaoNeural')
    
    def synthesize(self, text: str) -> bytes:
        """
        使用Edge-TTS合成语音
        
        Args:
            text: 输入文本
            
        Returns:
            音频数据（WAV格式）
        """
        try:
            import asyncio
            
            # 创建异步循环来运行Edge-TTS
            async def _synthesize():
                communicate = edge_tts.Communicate(text, self.voice)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                return audio_data
            
            # 运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_data = loop.run_until_complete(_synthesize())
            loop.close()
            
            logger.debug(f"Edge-TTS 语音合成完成: {len(audio_data)} bytes")
            return audio_data
            
        except Exception as e:
            logger.error(f"Edge-TTS 语音合成失败: {e}")
            raise


class MockTTS:
    """模拟TTS引擎（用于测试）"""
    
    def __init__(self, config: Dict):
        """
        初始化模拟TTS引擎
        
        Args:
            config: 音频配置
        """
        self.config = config
        logger.info("模拟TTS引擎初始化完成")
    
    def synthesize(self, text: str) -> bytes:
        """
        模拟语音合成
        
        Args:
            text: 输入文本
            
        Returns:
            空的音频数据（用于测试）
        """
        try:
            logger.info(f"[模拟TTS] 正在合成语音: {text}")
            
            # 模拟处理时间
            time.sleep(0.5)
            
            # 返回简单的WAV文件头（静音）
            import struct
            
            sample_rate = 22050
            channels = 1
            bits_per_sample = 16
            duration = max(len(text) * 0.08, 1.0)  # 至少1秒
            num_samples = int(sample_rate * duration)
            
            wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
                b'RIFF',
                36 + num_samples * channels * bits_per_sample // 8,
                b'WAVE',
                b'fmt ',
                16,
                1,
                channels,
                sample_rate,
                sample_rate * channels * bits_per_sample // 8,
                channels * bits_per_sample // 8,
                bits_per_sample,
                b'data',
                num_samples * channels * bits_per_sample // 8
            )
            
            # 生成静音数据
            audio_data = b'\x00' * (num_samples * channels * bits_per_sample // 8)
            
            return wav_header + audio_data
            
        except Exception as e:
            logger.error(f"模拟TTS合成失败: {e}")
            raise


if __name__ == "__main__":
    # 测试代码
    config = {
        'audio_output': {
            'device_index': None,
            'sample_rate': 22050,
            'channels': 1,
            'chunk_size': 1024,
            'audio_cache_size': 10
        },
        'model_config': {
            'primary_model': 'qwen2.5-omni',
            'fallback_tts': 'edge-tts',
            'device': 'auto'
        },
        'ai_personality': {
            'voice_style': '甜美女声'
        },
        'system': {
            'save_audio_files': True
        }
    }
    
    # 创建音频输出管理器
    audio_manager = AudioOutputManager(config)
    audio_manager.start()
    
    # 测试语音合成
    test_texts = [
        "欢迎大家来到直播间！",
        "谢谢大佬的礼物！",
        "这个游戏确实有点难呢～",
        "大家一起加油！"
    ]
    
    for text in test_texts:
        audio_manager.speak(text)
        time.sleep(3)
    
    # 等待播放完成
    time.sleep(10)
    
    audio_manager.stop()
    print("音频测试完成")