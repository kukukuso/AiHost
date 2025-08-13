#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音直播间数据监听模块
功能：实时捕获直播间弹幕、礼物、用户进入等事件
"""

import json
import time
import asyncio
import websocket
import threading
from typing import Dict, List, Callable, Optional
from loguru import logger
import re


class DouyinLiveListener:
    """抖音直播间监听器"""
    
    def __init__(self, room_id: str, config: Dict):
        """
        初始化监听器
        
        Args:
            room_id: 直播间房间号
            config: 配置参数
        """
        self.room_id = str(room_id)
        self.config = config
        self.ws = None
        self.is_running = False
        self.callbacks = {
            'comment': [],      # 弹幕回调
            'gift': [],         # 礼物回调  
            'member': [],       # 用户进入回调
            'like': [],         # 点赞回调
            'follow': [],       # 关注回调
        }
        
        # 抖音直播间WebSocket连接配置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }
        
        # 重连设置
        self.max_retries = config.get('max_retries', 3)
        self.heartbeat_interval = config.get('heartbeat_interval', 30)
        
    def add_callback(self, event_type: str, callback: Callable):
        """
        添加事件回调函数
        
        Args:
            event_type: 事件类型 ('comment', 'gift', 'member', 'like', 'follow')
            callback: 回调函数
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            logger.info(f"已添加 {event_type} 事件回调")
        else:
            logger.warning(f"不支持的事件类型: {event_type}")
    
    def _get_websocket_url(self) -> str:
        """
        构建WebSocket连接URL
        注意：这是一个示例实现，实际的抖音WebSocket连接需要更复杂的认证过程
        """
        # 实际使用时需要根据抖音的API文档获取正确的WebSocket URL
        # 这里提供一个示例格式
        base_url = "wss://webcast3-ws-web-lq.douyin.com/webcast/im/push/v2/"
        
        # 构建参数（示例参数，实际使用时需要参考抖音官方文档）
        params = {
            'app_name': 'douyin_web',
            'version_code': '180800',
            'webcast_sdk_version': '1.3.0',
            'update_version_code': '1.3.0',
            'compress': 'gzip',
            'internal_ext': '',
            'device_platform': 'web',
            'cookie_enabled': 'true',
            'screen_width': '1920',
            'screen_height': '1080',
            'browser_language': 'zh-CN',
            'browser_platform': 'Win32',
            'browser_name': 'Mozilla',
            'browser_version': '5.0',
            'room_id': self.room_id,
            'heartbeatDuration': '0',
            'signature': '',  # 需要计算签名
        }
        
        # 注意：实际部署时，您需要：
        # 1. 研究抖音的WebSocket协议
        # 2. 实现正确的签名算法
        # 3. 处理cookie和token认证
        # 4. 或者使用现有的开源库如 douyin-live-recorder
        
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_str}"
    
    def _parse_message(self, message: str) -> Optional[Dict]:
        """
        解析WebSocket消息
        
        Args:
            message: 原始消息
            
        Returns:
            解析后的消息字典，如果解析失败则返回None
        """
        try:
            # 尝试解析JSON消息
            data = json.loads(message)
            return data
        except json.JSONDecodeError:
            # 如果不是JSON格式，尝试其他解析方式
            logger.debug(f"非JSON消息: {message[:100]}...")
            return None
        except Exception as e:
            logger.error(f"消息解析错误: {e}")
            return None
    
    def _handle_comment(self, data: Dict):
        """处理弹幕消息"""
        try:
            # 解析弹幕数据（示例结构）
            user_info = data.get('user', {})
            username = user_info.get('nickname', '匿名用户')
            content = data.get('content', '')
            
            comment_data = {
                'type': 'comment',
                'username': username,
                'content': content,
                'user_id': user_info.get('id', ''),
                'timestamp': int(time.time()),
                'raw_data': data
            }
            
            logger.info(f"收到弹幕: {username}: {content}")
            
            # 调用所有弹幕回调函数
            for callback in self.callbacks['comment']:
                try:
                    callback(comment_data)
                except Exception as e:
                    logger.error(f"弹幕回调执行错误: {e}")
                    
        except Exception as e:
            logger.error(f"弹幕处理错误: {e}")
    
    def _handle_gift(self, data: Dict):
        """处理礼物消息"""
        try:
            # 解析礼物数据（示例结构）
            user_info = data.get('user', {})
            gift_info = data.get('gift', {})
            
            username = user_info.get('nickname', '匿名用户')
            gift_name = gift_info.get('name', '未知礼物')
            gift_count = data.get('count', 1)
            gift_value = gift_info.get('price', 0)  # 礼物价值（单位：抖币）
            
            gift_data = {
                'type': 'gift',
                'username': username,
                'gift_name': gift_name,
                'gift_count': gift_count,
                'gift_value': gift_value,
                'is_expensive': gift_value >= 1000,  # 判断是否为高价值礼物
                'user_id': user_info.get('id', ''),
                'timestamp': int(time.time()),
                'raw_data': data
            }
            
            logger.info(f"收到礼物: {username} 送出 {gift_count}个 {gift_name}")
            
            # 调用所有礼物回调函数
            for callback in self.callbacks['gift']:
                try:
                    callback(gift_data)
                except Exception as e:
                    logger.error(f"礼物回调执行错误: {e}")
                    
        except Exception as e:
            logger.error(f"礼物处理错误: {e}")
    
    def _handle_member_join(self, data: Dict):
        """处理用户进入消息"""
        try:
            # 解析用户进入数据（示例结构）
            user_info = data.get('user', {})
            username = user_info.get('nickname', '新用户')
            
            member_data = {
                'type': 'member_join',
                'username': username,
                'user_id': user_info.get('id', ''),
                'timestamp': int(time.time()),
                'raw_data': data
            }
            
            logger.info(f"用户进入: {username}")
            
            # 调用所有用户进入回调函数
            for callback in self.callbacks['member']:
                try:
                    callback(member_data)
                except Exception as e:
                    logger.error(f"用户进入回调执行错误: {e}")
                    
        except Exception as e:
            logger.error(f"用户进入处理错误: {e}")
    
    def _on_message(self, ws, message):
        """WebSocket消息处理"""
        try:
            # 解析消息
            data = self._parse_message(message)
            if not data:
                return
            
            # 根据消息类型分发处理
            msg_type = data.get('method', '')
            
            if msg_type == 'WebcastChatMessage':
                # 弹幕消息
                self._handle_comment(data)
            elif msg_type == 'WebcastGiftMessage':
                # 礼物消息
                self._handle_gift(data)
            elif msg_type == 'WebcastMemberMessage':
                # 用户进入消息
                self._handle_member_join(data)
            elif msg_type == 'WebcastLikeMessage':
                # 点赞消息（可选处理）
                pass
            elif msg_type == 'WebcastSocialMessage':
                # 关注消息（可选处理）
                pass
            else:
                logger.debug(f"未处理的消息类型: {msg_type}")
                
        except Exception as e:
            logger.error(f"消息处理错误: {e}")
    
    def _on_error(self, ws, error):
        """WebSocket错误处理"""
        logger.error(f"WebSocket错误: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket连接关闭处理"""
        logger.warning(f"WebSocket连接已关闭: {close_status_code} {close_msg}")
        self.is_running = False
    
    def _on_open(self, ws):
        """WebSocket连接打开处理"""
        logger.info(f"已连接到抖音直播间: {self.room_id}")
        self.is_running = True
        
        # 启动心跳
        def send_heartbeat():
            while self.is_running:
                try:
                    if ws:
                        # 发送心跳包（格式需要根据抖音协议调整）
                        heartbeat_msg = json.dumps({
                            'type': 'heartbeat',
                            'timestamp': int(time.time())
                        })
                        ws.send(heartbeat_msg)
                        logger.debug("发送心跳包")
                except Exception as e:
                    logger.error(f"心跳发送失败: {e}")
                    break
                time.sleep(self.heartbeat_interval)
        
        # 在新线程中启动心跳
        heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
        heartbeat_thread.start()
    
    def start(self):
        """启动监听器"""
        logger.info(f"开始监听抖音直播间: {self.room_id}")
        
        retries = 0
        while retries < self.max_retries:
            try:
                # 获取WebSocket URL
                ws_url = self._get_websocket_url()
                logger.info(f"连接WebSocket: {ws_url}")
                
                # 创建WebSocket连接
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    header=self.headers,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open
                )
                
                # 启动连接（阻塞式）
                self.ws.run_forever()
                
                # 如果正常退出，不重试
                if not self.is_running:
                    break
                    
            except Exception as e:
                retries += 1
                logger.error(f"连接失败 (尝试 {retries}/{self.max_retries}): {e}")
                if retries < self.max_retries:
                    logger.info(f"等待5秒后重试...")
                    time.sleep(5)
                else:
                    logger.error("连接重试次数已用完，停止监听")
                    break
    
    def stop(self):
        """停止监听器"""
        logger.info("正在停止监听器...")
        self.is_running = False
        if self.ws:
            self.ws.close()


# 模拟数据生成器（用于测试）
class MockDouyinListener:
    """
    模拟抖音监听器，用于测试和演示
    在实际部署前可以使用此类进行功能测试
    """
    
    def __init__(self, room_id: str, config: Dict):
        self.room_id = room_id
        self.config = config
        self.is_running = False
        self.callbacks = {
            'comment': [],
            'gift': [],
            'member': [],
            'like': [],
            'follow': [],
        }
        
        # 模拟数据
        self.mock_users = ['小明', '小红', '游戏高手', '新手玩家', '大佬666', '萌新求带']
        self.mock_comments = [
            '666', '主播厉害', '这游戏好难', '我也想玩', '加油加油',
            '答案是A！', '选B', 'C应该对', '这题太难了', '主播声音好听'
        ]
        self.mock_gifts = [
            {'name': '小心心', 'value': 10},
            {'name': '玫瑰花', 'value': 50},
            {'name': '跑车', 'value': 500},
            {'name': '火箭', 'value': 1000},
            {'name': '嘉年华', 'value': 3000},
        ]
    
    def add_callback(self, event_type: str, callback: Callable):
        """添加事件回调函数"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            logger.info(f"[模拟器] 已添加 {event_type} 事件回调")
    
    async def _generate_events(self):
        """生成模拟事件"""
        import random
        
        while self.is_running:
            try:
                # 随机生成事件类型
                event_type = random.choice(['comment', 'gift', 'member'])
                username = random.choice(self.mock_users)
                
                if event_type == 'comment':
                    # 生成弹幕事件
                    content = random.choice(self.mock_comments)
                    data = {
                        'type': 'comment',
                        'username': username,
                        'content': content,
                        'user_id': f'user_{random.randint(1000, 9999)}',
                        'timestamp': int(time.time()),
                        'raw_data': {}
                    }
                    
                    logger.info(f"[模拟] 弹幕: {username}: {content}")
                    for callback in self.callbacks['comment']:
                        callback(data)
                
                elif event_type == 'gift':
                    # 生成礼物事件
                    gift = random.choice(self.mock_gifts)
                    count = random.randint(1, 5)
                    
                    data = {
                        'type': 'gift',
                        'username': username,
                        'gift_name': gift['name'],
                        'gift_count': count,
                        'gift_value': gift['value'],
                        'is_expensive': gift['value'] >= 1000,
                        'user_id': f'user_{random.randint(1000, 9999)}',
                        'timestamp': int(time.time()),
                        'raw_data': {}
                    }
                    
                    logger.info(f"[模拟] 礼物: {username} 送出 {count}个 {gift['name']}")
                    for callback in self.callbacks['gift']:
                        callback(data)
                
                elif event_type == 'member':
                    # 生成用户进入事件
                    data = {
                        'type': 'member_join',
                        'username': username,
                        'user_id': f'user_{random.randint(1000, 9999)}',
                        'timestamp': int(time.time()),
                        'raw_data': {}
                    }
                    
                    logger.info(f"[模拟] 用户进入: {username}")
                    for callback in self.callbacks['member']:
                        callback(data)
                
                # 随机等待2-8秒
                await asyncio.sleep(random.uniform(2, 8))
                
            except Exception as e:
                logger.error(f"模拟事件生成错误: {e}")
                await asyncio.sleep(1)
    
    def start(self):
        """启动模拟监听器"""
        logger.info(f"[模拟器] 开始模拟抖音直播间: {self.room_id}")
        self.is_running = True
        
        # 在异步循环中运行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._generate_events())
    
    def stop(self):
        """停止模拟监听器"""
        logger.info("[模拟器] 正在停止模拟监听器...")
        self.is_running = False


if __name__ == "__main__":
    # 测试代码
    def test_comment_callback(data):
        print(f"收到弹幕: {data['username']}: {data['content']}")
    
    def test_gift_callback(data):
        print(f"收到礼物: {data['username']} -> {data['gift_name']} x{data['gift_count']}")
    
    def test_member_callback(data):
        print(f"用户进入: {data['username']}")
    
    # 使用模拟监听器进行测试
    config = {
        'max_retries': 3,
        'heartbeat_interval': 30
    }
    
    listener = MockDouyinListener("123456", config)
    listener.add_callback('comment', test_comment_callback)
    listener.add_callback('gift', test_gift_callback)
    listener.add_callback('member', test_member_callback)
    
    try:
        listener.start()
    except KeyboardInterrupt:
        listener.stop()
        print("测试结束")