#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen API调用模块
支持阿里云DashScope和OpenAI兼容接口
"""

import os
import time
import json
import asyncio
from typing import Dict, List, Optional, Union
from loguru import logger

# API客户端导入
try:
    import dashscope
    from dashscope import Generation
    HAS_DASHSCOPE = True
except ImportError:
    logger.warning("DashScope库未安装，将不支持阿里云API")
    HAS_DASHSCOPE = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    logger.warning("OpenAI库未安装，将不支持OpenAI兼容API")
    HAS_OPENAI = False


class QwenAPIManager:
    """Qwen API管理器"""
    
    def __init__(self, config: Dict):
        """
        初始化Qwen API管理器
        
        Args:
            config: API配置参数
        """
        self.config = config
        self.qwen_config = config.get('qwen_api', {})
        
        # API配置
        self.provider = self.qwen_config.get('provider', 'dashscope')
        self.model_name = self.qwen_config.get('model_name', 'qwen-plus')
        self.timeout = config.get('timeout', 10)
        self.max_retries = config.get('max_retries', 3)
        
        # 生成参数
        self.max_tokens = config.get('max_tokens', 150)
        self.temperature = config.get('temperature', 0.8)
        self.top_p = config.get('top_p', 0.9)
        
        # 初始化API客户端
        self.client = None
        self._init_client()
        
        logger.info(f"Qwen API管理器初始化完成 - 提供商: {self.provider}, 模型: {self.model_name}")
    
    def _init_client(self):
        """初始化API客户端"""
        try:
            if self.provider == 'dashscope':
                self._init_dashscope()
            elif self.provider == 'openai-compatible':
                self._init_openai_client()
            else:
                raise ValueError(f"不支持的API提供商: {self.provider}")
                
        except Exception as e:
            logger.error(f"API客户端初始化失败: {e}")
            raise
    
    def _init_dashscope(self):
        """初始化DashScope客户端"""
        if not HAS_DASHSCOPE:
            raise ImportError("DashScope库未安装，请运行: pip install dashscope")
        
        # 从环境变量获取API密钥
        api_key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('QWEN_API_KEY')
        if not api_key:
            raise ValueError("未找到DashScope API密钥，请设置环境变量 DASHSCOPE_API_KEY 或 QWEN_API_KEY")
        
        # 设置API密钥
        dashscope.api_key = api_key
        
        logger.info("DashScope客户端初始化成功")
    
    def _init_openai_client(self):
        """初始化OpenAI兼容客户端"""
        if not HAS_OPENAI:
            raise ImportError("OpenAI库未安装，请运行: pip install openai")
        
        # 从环境变量获取API密钥
        api_key = os.getenv('QWEN_API_KEY')
        if not api_key:
            raise ValueError("未找到API密钥，请设置环境变量 QWEN_API_KEY")
        
        # 获取基础URL
        base_url = self.qwen_config.get('base_url', '')
        if not base_url:
            raise ValueError("使用OpenAI兼容接口需要配置base_url")
        
        # 创建客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=self.timeout
        )
        
        logger.info(f"OpenAI兼容客户端初始化成功 - URL: {base_url}")
    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        生成AI回复
        
        Args:
            prompt: 用户输入提示
            system_prompt: 系统提示（可选）
            
        Returns:
            AI生成的回复文本
        """
        for attempt in range(self.max_retries):
            try:
                if self.provider == 'dashscope':
                    return self._generate_with_dashscope(prompt, system_prompt)
                elif self.provider == 'openai-compatible':
                    return self._generate_with_openai(prompt, system_prompt)
                else:
                    raise ValueError(f"不支持的API提供商: {self.provider}")
                    
            except Exception as e:
                logger.warning(f"API调用失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"API调用最终失败: {e}")
                    raise
                time.sleep(1)  # 等待1秒后重试
    
    def _generate_with_dashscope(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """使用DashScope API生成回复"""
        try:
            # 构建消息
            messages = []
            
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            
            messages.append({
                'role': 'user',
                'content': prompt
            })
            
            # 调用API
            response = Generation.call(
                model=self.model_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                result_format='message'
            )
            
            # 检查响应
            if response.status_code == 200:
                # 提取回复内容
                content = response.output.choices[0].message.content
                logger.debug(f"DashScope API调用成功: {content[:50]}...")
                return content.strip()
            else:
                raise Exception(f"API错误: {response.code} - {response.message}")
                
        except Exception as e:
            logger.error(f"DashScope API调用失败: {e}")
            raise
    
    def _generate_with_openai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """使用OpenAI兼容API生成回复"""
        try:
            # 构建消息
            messages = []
            
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            
            messages.append({
                'role': 'user',
                'content': prompt
            })
            
            # 调用API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p
            )
            
            # 提取回复内容
            content = response.choices[0].message.content
            logger.debug(f"OpenAI兼容API调用成功: {content[:50]}...")
            return content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI兼容API调用失败: {e}")
            raise
    
    async def generate_response_async(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        异步生成AI回复
        
        Args:
            prompt: 用户输入提示
            system_prompt: 系统提示（可选）
            
        Returns:
            AI生成的回复文本
        """
        # 在异步环境中运行同步API调用
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_response, prompt, system_prompt)
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            连接是否成功
        """
        try:
            test_prompt = "你好"
            response = self.generate_response(test_prompt)
            
            if response and len(response) > 0:
                logger.info("✅ API连接测试成功")
                return True
            else:
                logger.error("❌ API连接测试失败：回复为空")
                return False
                
        except Exception as e:
            logger.error(f"❌ API连接测试失败: {e}")
            return False
    
    def get_model_info(self) -> Dict:
        """获取模型信息"""
        return {
            'provider': self.provider,
            'model_name': self.model_name,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'timeout': self.timeout
        }


class EnhancedResponseGenerator:
    """增强的回复生成器（使用Qwen API）"""
    
    def __init__(self, personality: str, api_manager: QwenAPIManager):
        """
        初始化增强回复生成器
        
        Args:
            personality: AI人格描述
            api_manager: Qwen API管理器
        """
        self.personality = personality
        self.api_manager = api_manager
        
        # 缓存系统提示
        self.system_prompt = self._build_system_prompt()
        
        logger.info("增强回复生成器初始化完成")
    
    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        system_prompt = f"""
{self.personality}

你现在是一个抖音直播间的AI主播助手，请根据以下要求回复：

1. 保持你的人格特征，说话要自然生动
2. 回复要简短有力，不超过30个字
3. 根据不同情况给出合适的回应：
   - 弹幕互动：热情回应，体现人格特色
   - 礼物感谢：表达真诚感激，对高价值礼物要特别兴奋
   - 欢迎新人：热情欢迎，让人感到温暖
   - 游戏互动：给出鼓励或有趣的评论

4. 语言要求：
   - 使用简体中文
   - 语言要活泼有趣，符合直播间氛围
   - 可以使用表情词汇，如"哇！"、"太棒了！"等
   - 避免重复和机械化的回复

请直接回复内容，不需要解释。
        """.strip()
        
        return system_prompt
    
    def generate_response(self, event_data: Dict, context: Optional[List[Dict]] = None) -> str:
        """
        生成智能回复
        
        Args:
            event_data: 事件数据
            context: 对话上下文（可选）
            
        Returns:
            生成的回复文本
        """
        try:
            # 构建用户提示
            user_prompt = self._build_user_prompt(event_data, context)
            
            # 调用API生成回复
            response = self.api_manager.generate_response(
                prompt=user_prompt,
                system_prompt=self.system_prompt
            )
            
            # 后处理回复
            processed_response = self._post_process_response(response)
            
            logger.debug(f"AI生成回复: {processed_response}")
            return processed_response
            
        except Exception as e:
            logger.error(f"回复生成失败: {e}")
            # 返回备用回复
            return self._get_fallback_response(event_data)
    
    def _build_user_prompt(self, event_data: Dict, context: Optional[List[Dict]] = None) -> str:
        """构建用户提示"""
        event_type = event_data.get('type', '')
        username = event_data.get('username', '观众')
        
        if event_type == 'comment':
            content = event_data.get('content', '')
            prompt = f"观众{username}发送弹幕：{content}\n请给出合适的回复。"
            
        elif event_type == 'gift':
            gift_name = event_data.get('gift_name', '礼物')
            gift_count = event_data.get('gift_count', 1)
            is_expensive = event_data.get('is_expensive', False)
            
            if is_expensive:
                prompt = f"观众{username}送出了{gift_count}个{gift_name}（高价值礼物）！请表达特别感激和兴奋。"
            else:
                prompt = f"观众{username}送出了{gift_count}个{gift_name}。请表达感谢。"
                
        elif event_type == 'member_join':
            prompt = f"新观众{username}进入了直播间。请热情欢迎。"
            
        else:
            prompt = f"发生了{event_type}事件，涉及用户{username}。请给出合适的回应。"
        
        # 添加上下文信息（如果有）
        if context and len(context) > 0:
            prompt += f"\n\n最近的互动：{context[-3:]}"  # 只包含最近3条
        
        return prompt
    
    def _post_process_response(self, response: str) -> str:
        """后处理回复"""
        # 去除多余的空白字符
        response = response.strip()
        
        # 限制长度
        if len(response) > 50:
            response = response[:47] + "..."
        
        # 去除可能的引号
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        if response.startswith("'") and response.endswith("'"):
            response = response[1:-1]
        
        return response
    
    def _get_fallback_response(self, event_data: Dict) -> str:
        """获取备用回复（当API失败时使用）"""
        event_type = event_data.get('type', '')
        username = event_data.get('username', '朋友')
        
        fallback_responses = {
            'comment': [
                f"谢谢{username}的评论！",
                f"和{username}想的一样！",
                "说得好！"
            ],
            'gift': [
                f"感谢{username}的礼物！",
                f"谢谢{username}的支持！",
                "太感动了！"
            ],
            'member_join': [
                f"欢迎{username}！",
                f"大家欢迎{username}！",
                "新朋友来了！"
            ]
        }
        
        import random
        responses = fallback_responses.get(event_type, ["谢谢大家！"])
        return random.choice(responses)


if __name__ == "__main__":
    # 测试代码
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # 测试配置
    config = {
        'qwen_api': {
            'provider': 'dashscope',
            'model_name': 'qwen-turbo'
        },
        'max_tokens': 100,
        'temperature': 0.8,
        'top_p': 0.9,
        'timeout': 10,
        'max_retries': 3
    }
    
    try:
        # 创建API管理器
        api_manager = QwenAPIManager(config)
        
        # 测试连接
        if api_manager.test_connection():
            print("✅ API连接测试成功")
            
            # 测试生成回复
            personality = "你是一个活泼可爱的AI主播助手，说话风趣幽默。"
            generator = EnhancedResponseGenerator(personality, api_manager)
            
            # 测试不同类型的事件
            test_events = [
                {
                    'type': 'comment',
                    'username': '测试用户',
                    'content': '主播声音好听！'
                },
                {
                    'type': 'gift',
                    'username': '大佬666',
                    'gift_name': '火箭',
                    'gift_count': 1,
                    'is_expensive': True
                }
            ]
            
            for event in test_events:
                response = generator.generate_response(event)
                print(f"事件: {event}")
                print(f"回复: {response}")
                print("-" * 30)
        else:
            print("❌ API连接测试失败")
            
    except Exception as e:
        print(f"测试失败: {e}")