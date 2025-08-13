#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI抖音弹幕游戏主持人 - 主程序
整合直播间监听、AI交互、语音输出等功能
"""

import os
import sys
import time
import signal
import yaml
import threading
from typing import Dict, Optional
from loguru import logger
from dotenv import load_dotenv

# 导入项目模块
from douyin_listener import DouyinLiveListener, MockDouyinListener
from ai_host import AIGameHost
from audio_output import AudioOutputManager


class AIDouyinHost:
    """AI抖音主持人主控制器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化AI主持人系统
        
        Args:
            config_path: 配置文件路径
        """
        # 加载环境变量
        load_dotenv()
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化日志
        self._setup_logging()
        
        # 系统组件
        self.douyin_listener = None
        self.ai_host = None
        self.audio_manager = None
        
        # 运行状态
        self.is_running = False
        self.startup_time = None
        
        logger.info("=" * 50)
        logger.info("AI抖音弹幕游戏主持人系统启动")
        logger.info("=" * 50)
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 从环境变量覆盖配置
            room_id = os.getenv('DOUYIN_ROOM_ID')
            if room_id:
                config['douyin_live']['room_id'] = room_id
            
            # 验证必要配置
            self._validate_config(config)
            
            logger.info(f"配置文件加载成功: {config_path}")
            return config
            
        except FileNotFoundError:
            logger.error(f"配置文件不存在: {config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            logger.error(f"配置文件格式错误: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            sys.exit(1)
    
    def _validate_config(self, config: Dict):
        """验证配置文件"""
        # 检查必要的配置项
        required_sections = ['douyin_live', 'ai_personality', 'audio_output', 'model_config']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"缺少必要配置节: {section}")
        
        # 检查直播间ID
        room_id = config['douyin_live'].get('room_id', '')
        if not room_id or room_id == 'YOUR_ROOM_ID_HERE':
            logger.warning("⚠️  未配置直播间ID，将使用模拟模式")
            config['douyin_live']['use_mock'] = True
        else:
            config['douyin_live']['use_mock'] = False
            logger.info(f"✅ 直播间ID: {room_id}")
    
    def _setup_logging(self):
        """设置日志系统"""
        # 从配置获取日志设置
        log_level = self.config.get('system', {}).get('log_level', 'INFO')
        log_file = self.config.get('system', {}).get('log_file', 'logs/ai_host.log')
        
        # 创建日志目录
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 配置loguru
        logger.remove()  # 移除默认处理器
        
        # 控制台输出
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )
        
        # 文件输出
        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8"
        )
        
        logger.info(f"日志系统初始化完成，级别: {log_level}")
    
    def _init_components(self):
        """初始化系统组件"""
        try:
            # 1. 初始化音频输出管理器
            logger.info("📢 初始化音频输出系统...")
            self.audio_manager = AudioOutputManager(self.config)
            self.audio_manager.start()
            
            # 2. 初始化AI主持人
            logger.info("🤖 初始化AI主持人...")
            self.ai_host = AIGameHost(
                config=self.config,
                audio_callback=self.audio_manager.speak
            )
            self.ai_host.start()
            
            # 3. 初始化直播间监听器
            logger.info("📱 初始化直播间监听器...")
            room_id = self.config['douyin_live']['room_id']
            use_mock = self.config['douyin_live'].get('use_mock', False)
            
            if use_mock:
                logger.info("🔧 使用模拟模式（用于测试）")
                self.douyin_listener = MockDouyinListener(room_id, self.config['douyin_live'])
            else:
                logger.info(f"🔗 连接到抖音直播间: {room_id}")
                self.douyin_listener = DouyinLiveListener(room_id, self.config['douyin_live'])
            
            # 4. 注册事件回调
            self._register_callbacks()
            
            logger.success("✅ 所有组件初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 组件初始化失败: {e}")
            raise
    
    def _register_callbacks(self):
        """注册事件回调函数"""
        # 注册直播间事件回调到AI主持人
        self.douyin_listener.add_callback('comment', self.ai_host.handle_event)
        self.douyin_listener.add_callback('gift', self.ai_host.handle_event)
        self.douyin_listener.add_callback('member', self.ai_host.handle_event)
        
        # 注册额外的监控回调
        self.douyin_listener.add_callback('comment', self._on_comment)
        self.douyin_listener.add_callback('gift', self._on_gift)
        self.douyin_listener.add_callback('member', self._on_member)
        
        logger.info("📋 事件回调注册完成")
    
    def _on_comment(self, event_data: Dict):
        """弹幕事件回调（用于监控和统计）"""
        username = event_data.get('username', '未知')
        content = event_data.get('content', '')
        logger.debug(f"💬 弹幕: {username}: {content}")
    
    def _on_gift(self, event_data: Dict):
        """礼物事件回调（用于监控和统计）"""
        username = event_data.get('username', '未知')
        gift_name = event_data.get('gift_name', '未知礼物')
        is_expensive = event_data.get('is_expensive', False)
        
        if is_expensive:
            logger.info(f"🎁💎 高价值礼物: {username} -> {gift_name}")
        else:
            logger.debug(f"🎁 礼物: {username} -> {gift_name}")
    
    def _on_member(self, event_data: Dict):
        """用户进入事件回调（用于监控和统计）"""
        username = event_data.get('username', '未知')
        logger.debug(f"👋 用户进入: {username}")
    
    def start(self):
        """启动AI主持人系统"""
        try:
            if self.is_running:
                logger.warning("⚠️  系统已经在运行中")
                return
            
            # 初始化组件
            self._init_components()
            
            # 设置信号处理器
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # 标记为运行状态
            self.is_running = True
            self.startup_time = time.time()
            
            # 播放启动语音
            self._play_startup_message()
            
            # 启动直播间监听（阻塞式）
            logger.info("🚀 AI主持人系统启动完成，开始监听直播间...")
            self._start_monitoring()
            
            # 在新线程中启动监听器
            listener_thread = threading.Thread(target=self.douyin_listener.start, daemon=True)
            listener_thread.start()
            
            # 主线程保持运行并监控状态
            self._main_loop()
            
        except KeyboardInterrupt:
            logger.info("📱 收到停止信号，正在关闭系统...")
        except Exception as e:
            logger.error(f"❌ 系统启动失败: {e}")
            raise
        finally:
            self.stop()
    
    def _play_startup_message(self):
        """播放启动消息"""
        try:
            character_type = self.config.get('ai_personality', {}).get('character_type', '活泼少女')
            startup_messages = {
                '活泼少女': "大家好！我是你们的AI主播助手！准备开始精彩的直播互动吧！",
                '幽默段子手': "各位观众老爷们好！段子手AI已上线，准备开始整活儿！",
                '温柔大姐姐': "亲爱的朋友们，大家好！我会陪伴大家度过愉快的直播时光～",
                '搞怪萌妹': "哈喽哈喽！萌萌的AI助手上线啦！诶嘿嘿～"
            }
            
            message = startup_messages.get(character_type, startup_messages['活泼少女'])
            self.audio_manager.speak(message, priority=True)
            
        except Exception as e:
            logger.error(f"启动消息播放失败: {e}")
    
    def _start_monitoring(self):
        """启动系统监控"""
        def monitor_loop():
            while self.is_running:
                try:
                    # 每30秒打印一次统计信息
                    time.sleep(30)
                    if self.is_running:
                        self._print_stats()
                except Exception as e:
                    logger.error(f"监控循环错误: {e}")
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def _main_loop(self):
        """主循环"""
        try:
            while self.is_running:
                time.sleep(1)
                
                # 检查组件状态
                if not self._check_components_health():
                    logger.error("❌ 组件健康检查失败，正在重启...")
                    self._restart_components()
                
        except KeyboardInterrupt:
            logger.info("📱 收到停止信号")
        except Exception as e:
            logger.error(f"主循环错误: {e}")
    
    def _check_components_health(self) -> bool:
        """检查组件健康状态"""
        try:
            # 检查AI主持人
            if not self.ai_host or not self.ai_host.is_running:
                logger.warning("AI主持人组件异常")
                return False
            
            # 检查音频管理器
            if not self.audio_manager or not self.audio_manager.is_running:
                logger.warning("音频管理器组件异常")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
    
    def _restart_components(self):
        """重启异常组件"""
        try:
            logger.info("🔄 正在重启异常组件...")
            
            # 重启AI主持人
            if self.ai_host and not self.ai_host.is_running:
                self.ai_host.start()
            
            # 重启音频管理器
            if self.audio_manager and not self.audio_manager.is_running:
                self.audio_manager.start()
            
            logger.info("✅ 组件重启完成")
            
        except Exception as e:
            logger.error(f"组件重启失败: {e}")
    
    def _print_stats(self):
        """打印系统统计信息"""
        try:
            if not self.is_running:
                return
            
            # 运行时间
            uptime = int(time.time() - self.startup_time) if self.startup_time else 0
            uptime_str = f"{uptime // 3600}h {(uptime % 3600) // 60}m {uptime % 60}s"
            
            # AI主持人统计
            ai_stats = self.ai_host.get_stats() if self.ai_host else {}
            
            logger.info("📊 系统运行状态:")
            logger.info(f"  ⏰ 运行时间: {uptime_str}")
            logger.info(f"  💬 处理弹幕: {ai_stats.get('total_comments', 0)}")
            logger.info(f"  🎁 处理礼物: {ai_stats.get('total_gifts', 0)}")
            logger.info(f"  👋 欢迎用户: {ai_stats.get('total_members', 0)}")
            logger.info(f"  🗣️  语音回复: {ai_stats.get('responses_sent', 0)}")
            
        except Exception as e:
            logger.error(f"统计信息打印失败: {e}")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"📱 收到信号 {signum}，正在关闭系统...")
        self.stop()
    
    def stop(self):
        """停止AI主持人系统"""
        if not self.is_running:
            return
        
        logger.info("🛑 正在停止AI主持人系统...")
        self.is_running = False
        
        try:
            # 播放停止消息
            if self.audio_manager:
                self.audio_manager.speak("主播助手即将下线，感谢大家的陪伴！再见～", priority=True)
                time.sleep(3)  # 等待播放完成
            
            # 停止各组件
            if self.douyin_listener:
                self.douyin_listener.stop()
                logger.info("✅ 直播间监听器已停止")
            
            if self.ai_host:
                self.ai_host.stop()
                logger.info("✅ AI主持人已停止")
            
            if self.audio_manager:
                self.audio_manager.stop()
                logger.info("✅ 音频管理器已停止")
            
            # 打印最终统计
            self._print_final_stats()
            
            logger.success("🎉 AI主持人系统已完全停止")
            
        except Exception as e:
            logger.error(f"❌ 系统停止过程中出现错误: {e}")
    
    def _print_final_stats(self):
        """打印最终统计信息"""
        try:
            if self.startup_time:
                total_uptime = int(time.time() - self.startup_time)
                uptime_str = f"{total_uptime // 3600}h {(total_uptime % 3600) // 60}m {total_uptime % 60}s"
                
                ai_stats = self.ai_host.get_stats() if self.ai_host else {}
                
                logger.info("=" * 50)
                logger.info("📊 最终运行统计:")
                logger.info(f"  ⏰ 总运行时间: {uptime_str}")
                logger.info(f"  💬 总处理弹幕: {ai_stats.get('total_comments', 0)}")
                logger.info(f"  🎁 总处理礼物: {ai_stats.get('total_gifts', 0)}")
                logger.info(f"  👋 总欢迎用户: {ai_stats.get('total_members', 0)}")
                logger.info(f"  🗣️  总语音回复: {ai_stats.get('responses_sent', 0)}")
                logger.info("=" * 50)
                
        except Exception as e:
            logger.error(f"最终统计打印失败: {e}")


def main():
    """主函数"""
    try:
        # 检查Python版本
        if sys.version_info < (3, 7):
            print("❌ 错误: 需要Python 3.7或更高版本")
            sys.exit(1)
        
        # 显示启动信息
        print("🎮 AI抖音弹幕游戏主持人")
        print("📧 作者: AI助手")
        print("🔗 项目: https://github.com/your-repo")
        print("-" * 50)
        
        # 检查配置文件
        config_file = "config.yaml"
        if not os.path.exists(config_file):
            print(f"❌ 配置文件不存在: {config_file}")
            print("💡 请复制 config.yaml.example 为 config.yaml 并修改配置")
            sys.exit(1)
        
        # 创建并启动AI主持人系统
        ai_host_system = AIDouyinHost(config_file)
        ai_host_system.start()
        
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()