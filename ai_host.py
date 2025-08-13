#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI主持人核心模块
功能：智能交互逻辑、游戏主持、人格化回复
"""

import random
import time
import re
from typing import Dict, List, Optional, Callable
from loguru import logger
import threading
import queue
import asyncio


class AIGameHost:
    """AI游戏主持人"""
    
    def __init__(self, config: Dict, audio_callback: Optional[Callable] = None):
        """
        初始化AI主持人
        
        Args:
            config: 配置字典
            audio_callback: 音频输出回调函数
        """
        self.config = config
        self.audio_callback = audio_callback
        
        # 从配置中加载设置
        self.ai_config = config.get('ai_personality', {})
        self.interaction_config = config.get('interaction', {})
        self.system_config = config.get('system', {})
        
        # AI人格设定
        self.personality = self._load_personality()
        
        # 消息队列（用于异步处理）
        self.message_queue = queue.Queue()
        self.is_running = False
        
        # 最近消息记录（用于避免重复回复）
        self.recent_messages = []
        self.max_recent_messages = 50
        
        # 互动计数器
        self.interaction_stats = {
            'total_comments': 0,
            'total_gifts': 0,
            'total_members': 0,
            'responses_sent': 0
        }
        
        # 启动消息处理线程
        self.processing_thread = None
        
        logger.info("AI主持人初始化完成")
    
    def _load_personality(self) -> str:
        """加载AI人格设定"""
        custom_personality = self.ai_config.get('custom_personality', '')
        if custom_personality.strip():
            return custom_personality.strip()
        
        # 预设人格类型
        character_type = self.ai_config.get('character_type', '活泼少女')
        
        personalities = {
            '活泼少女': """
你是一个充满活力的游戏主播助手，性格开朗活泼，说话风趣幽默。
你喜欢用"哇！"、"太棒了！"、"小伙伴们"这样的词汇。
对待粉丝非常热情，特别喜欢和观众互动，会根据弹幕内容给出有趣的回应。
当有人送礼物时，你会特别兴奋和感激。
你的回复要简短有力，不超过30个字，充满正能量。
            """,
            
            '幽默段子手': """
你是一个风趣幽默的游戏解说员，擅长说段子和吐槽。
你经常用网络流行语，喜欢开玩笑，但不会伤害任何人。
对于游戏中的失误，你会用幽默的方式化解尴尬。
你的回复要机智有趣，让直播间充满欢声笑语。
回复要简洁明了，不超过25个字。
            """,
            
            '温柔大姐姐': """
你是一个温柔亲和的主播助手，说话温和耐心。
你会用"亲爱的"、"小可爱"、"没关系"这样温暖的词汇。
对于新人特别照顾，会给出鼓励和指导。
你的声音让人感到安心和温暖。
回复要温馨贴心，不超过35个字。
            """,
            
            '搞怪萌妹': """
你是一个天真可爱的萌妹子，说话有点呆萌。
你会用"诶？"、"哈？"、"好奇怪呀"这样的口癖。
有时候会说错话，但很可爱。
对什么都感到好奇和惊讶。
回复要萌萌哒，不超过20个字。
            """
        }
        
        return personalities.get(character_type, personalities['活泼少女']).strip()
    
    def start(self):
        """启动AI主持人"""
        if self.is_running:
            logger.warning("AI主持人已经在运行中")
            return
        
        self.is_running = True
        
        # 启动消息处理线程
        self.processing_thread = threading.Thread(target=self._process_messages, daemon=True)
        self.processing_thread.start()
        
        logger.info("AI主持人已启动")
    
    def stop(self):
        """停止AI主持人"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        logger.info("AI主持人已停止")
    
    def handle_event(self, event_data: Dict):
        """
        处理直播间事件
        
        Args:
            event_data: 事件数据
        """
        try:
            # 将事件放入队列等待处理
            self.message_queue.put(event_data)
        except Exception as e:
            logger.error(f"事件处理失败: {e}")
    
    def _process_messages(self):
        """消息处理主循环"""
        while self.is_running:
            try:
                # 从队列获取消息（阻塞式，超时1秒）
                try:
                    event_data = self.message_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # 处理事件
                response = self._generate_response(event_data)
                if response:
                    self._send_response(response)
                
                # 标记任务完成
                self.message_queue.task_done()
                
            except Exception as e:
                logger.error(f"消息处理循环错误: {e}")
                time.sleep(1)
    
    def _generate_response(self, event_data: Dict) -> Optional[str]:
        """
        生成回复内容
        
        Args:
            event_data: 事件数据
            
        Returns:
            回复文本，如果不需要回复则返回None
        """
        try:
            event_type = event_data.get('type', '')
            
            if event_type == 'comment':
                return self._handle_comment_event(event_data)
            elif event_type == 'gift':
                return self._handle_gift_event(event_data)
            elif event_type == 'member_join':
                return self._handle_member_event(event_data)
            else:
                logger.debug(f"未知事件类型: {event_type}")
                return None
                
        except Exception as e:
            logger.error(f"响应生成错误: {e}")
            return None
    
    def _handle_comment_event(self, event_data: Dict) -> Optional[str]:
        """处理弹幕事件"""
        username = event_data.get('username', '观众')
        content = event_data.get('content', '')
        
        # 更新统计
        self.interaction_stats['total_comments'] += 1
        
        # 检查是否包含禁用词汇
        banned_words = self.system_config.get('banned_words', [])
        if any(word in content for word in banned_words):
            logger.warning(f"弹幕包含禁用词汇: {content}")
            return None
        
        # 检查是否需要回复
        if not self._should_reply_to_comment(content):
            return None
        
        # 根据弹幕内容生成回复
        response = self._generate_comment_response(username, content)
        return response
    
    def _should_reply_to_comment(self, content: str) -> bool:
        """判断是否应该回复弹幕"""
        # 检查回复开关
        if not self.interaction_config.get('comment_reply', {}).get('reply_normal_comments', True):
            return False
        
        # 检查回复概率
        reply_probability = self.interaction_config.get('comment_reply', {}).get('reply_probability', 0.3)
        if random.random() > reply_probability:
            return False
        
        # 检查是否包含触发关键词
        trigger_keywords = self.interaction_config.get('comment_reply', {}).get('trigger_keywords', [])
        if trigger_keywords and any(keyword in content for keyword in trigger_keywords):
            return True
        
        # 检查游戏相关内容
        game_keywords = ['答案', '选择', 'A', 'B', 'C', 'D', '对', '错', '难', '简单', '厉害']
        if any(keyword in content for keyword in game_keywords):
            return True
        
        # 其他情况按概率决定
        return True
    
    def _generate_comment_response(self, username: str, content: str) -> str:
        """生成弹幕回复"""
        # 分析弹幕内容类型
        if any(word in content for word in ['答案', 'A', 'B', 'C', 'D']):
            # 游戏答题类型
            return self._get_answer_response(content)
        elif any(word in content for word in ['难', '困难', '太难了']):
            # 游戏难度吐槽
            responses = self.interaction_config.get('game_interaction', {}).get('complaint_reactions', [
                "哈哈哈，这个游戏确实有点难！",
                "我懂我懂，这题目太坑了！",
                "别着急，慢慢来～"
            ])
            return random.choice(responses)
        elif any(word in content for word in ['666', '厉害', '棒', '好']):
            # 称赞类型
            responses = [
                f"谢谢{username}的夸奖！",
                f"{username}也很棒呀！",
                "哈哈，一起加油！",
                "大家都很厉害！"
            ]
            return random.choice(responses)
        elif any(word in content for word in ['主播', '声音', '好听']):
            # 夸主播类型
            responses = [
                f"谢谢{username}！你的话让我好开心！",
                f"{username}真的太贴心了！",
                "哇，被夸了好害羞～",
                "你们的支持是我最大的动力！"
            ]
            return random.choice(responses)
        else:
            # 通用回复
            responses = [
                f"哈喽{username}！",
                f"{username}说得对！",
                f"和{username}想的一样！",
                "有道理有道理！",
                "哇，好有趣的想法！"
            ]
            return random.choice(responses)
    
    def _get_answer_response(self, content: str) -> str:
        """获取答题相关回复"""
        answer_reactions = self.interaction_config.get('game_interaction', {}).get('answer_reactions', {})
        
        # 简单判断答案正确性（这里只是示例，实际可以更复杂）
        if any(word in content for word in ['对了', '正确', '答对']):
            correct_responses = answer_reactions.get('correct', ["太棒了！答对了！", "厉害厉害！", "聪明！"])
            return random.choice(correct_responses)
        elif any(word in content for word in ['错了', '不对', '答错']):
            wrong_responses = answer_reactions.get('wrong', ["哎呀，差一点点！", "没关系，下次一定行！", "再想想～"])
            return random.choice(wrong_responses)
        else:
            # 答题猜测
            responses = [
                "嗯嗯，我觉得也有可能！",
                "这个选择很有想法！",
                "让我们看看对不对～",
                "好紧张，是这个答案吗？"
            ]
            return random.choice(responses)
    
    def _handle_gift_event(self, event_data: Dict) -> str:
        """处理礼物事件"""
        username = event_data.get('username', '神秘观众')
        gift_name = event_data.get('gift_name', '礼物')
        gift_count = event_data.get('gift_count', 1)
        is_expensive = event_data.get('is_expensive', False)
        
        # 更新统计
        self.interaction_stats['total_gifts'] += 1
        
        # 根据礼物价值选择回复模板
        if is_expensive:
            # 高价值礼物
            responses = self.interaction_config.get('gift_thanks', {}).get('expensive_gifts', [
                "哇！感谢{username}大哥的{gift_name}！太慷慨了！",
                "天哪！{username}大哥真的太豪气了！谢谢您的{gift_name}！",
                "{username}大哥威武！谢谢您的{gift_name}，我太感动了！"
            ])
        else:
            # 普通礼物
            responses = self.interaction_config.get('gift_thanks', {}).get('normal_gifts', [
                "谢谢{username}的{gift_name}！",
                "感谢{username}的支持！"
            ])
        
        # 选择回复并格式化
        response_template = random.choice(responses)
        
        # 处理多个礼物的情况
        if gift_count > 1:
            gift_display = f"{gift_count}个{gift_name}"
        else:
            gift_display = gift_name
        
        response = response_template.format(
            username=username,
            gift_name=gift_display
        )
        
        return response
    
    def _handle_member_event(self, event_data: Dict) -> Optional[str]:
        """处理用户进入事件"""
        username = event_data.get('username', '新朋友')
        
        # 更新统计
        self.interaction_stats['total_members'] += 1
        
        # 检查是否启用欢迎功能
        if not self.interaction_config.get('welcome_new_users', True):
            return None
        
        # 选择欢迎词
        welcome_messages = self.interaction_config.get('welcome_messages', [
            "欢迎{username}来到直播间！",
            "哇！{username}来了！欢迎欢迎~",
            "新朋友{username}来啦！大家快欢迎一下！"
        ])
        
        response_template = random.choice(welcome_messages)
        response = response_template.format(username=username)
        
        return response
    
    def _send_response(self, response_text: str):
        """发送回复（转换为语音）"""
        try:
            if not response_text:
                return
            
            # 记录回复到最近消息
            self._add_to_recent_messages(response_text)
            
            # 更新统计
            self.interaction_stats['responses_sent'] += 1
            
            logger.info(f"AI回复: {response_text}")
            
            # 调用音频输出回调
            if self.audio_callback:
                self.audio_callback(response_text)
            else:
                logger.warning("未设置音频输出回调，无法播放语音")
                
        except Exception as e:
            logger.error(f"发送回复失败: {e}")
    
    def _add_to_recent_messages(self, message: str):
        """添加到最近消息记录"""
        self.recent_messages.append({
            'text': message,
            'timestamp': time.time()
        })
        
        # 保持最近消息数量限制
        if len(self.recent_messages) > self.max_recent_messages:
            self.recent_messages.pop(0)
    
    def get_stats(self) -> Dict:
        """获取互动统计"""
        return self.interaction_stats.copy()
    
    def update_personality(self, new_personality: str):
        """更新AI人格"""
        self.personality = new_personality
        logger.info("AI人格已更新")
    
    def clear_recent_messages(self):
        """清空最近消息记录"""
        self.recent_messages.clear()
        logger.info("最近消息记录已清空")


# 回复生成器（高级版本，可以扩展使用LLM）
class AdvancedResponseGenerator:
    """高级回复生成器，可以集成LLM模型"""
    
    def __init__(self, personality: str, model_config: Dict):
        """
        初始化高级回复生成器
        
        Args:
            personality: AI人格描述
            model_config: 模型配置
        """
        self.personality = personality
        self.model_config = model_config
        
        # 这里可以初始化LLM模型
        # 例如：Qwen、ChatGLM、本地模型等
        # self.model = load_model(model_config)
        
    def generate_response(self, event_data: Dict, context: List[Dict]) -> str:
        """
        使用LLM生成更智能的回复
        
        Args:
            event_data: 当前事件数据
            context: 对话上下文
            
        Returns:
            生成的回复文本
        """
        # 构建提示词
        prompt = self._build_prompt(event_data, context)
        
        # 调用LLM生成回复（这里使用模拟回复）
        response = self._call_llm(prompt)
        
        return response
    
    def _build_prompt(self, event_data: Dict, context: List[Dict]) -> str:
        """构建LLM提示词"""
        event_type = event_data.get('type', '')
        username = event_data.get('username', '观众')
        
        prompt = f"""
{self.personality}

当前直播间情况：
- 事件类型：{event_type}
- 用户：{username}
"""
        
        if event_type == 'comment':
            content = event_data.get('content', '')
            prompt += f"- 弹幕内容：{content}\n"
        elif event_type == 'gift':
            gift_name = event_data.get('gift_name', '')
            prompt += f"- 礼物：{gift_name}\n"
        
        prompt += """
请生成一个符合你人格的简短回复（不超过30个字）：
"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM模型（这里使用模拟回复）"""
        # 实际使用时，这里应该调用真实的LLM模型
        # 例如：
        # response = self.model.generate(prompt, max_tokens=50, temperature=0.8)
        # return response
        
        # 模拟回复
        mock_responses = [
            "哈哈哈，太有趣了！",
            "小伙伴们都很棒！",
            "谢谢大家的支持！",
            "一起加油鸭！",
            "哇，好厉害！"
        ]
        return random.choice(mock_responses)


if __name__ == "__main__":
    # 测试代码
    config = {
        'ai_personality': {
            'character_type': '活泼少女'
        },
        'interaction': {
            'welcome_new_users': True,
            'welcome_messages': [
                "欢迎{username}来到直播间！",
                "哇！{username}来了！欢迎欢迎~"
            ],
            'gift_thanks': {
                'normal_gifts': ["谢谢{username}的{gift_name}！"],
                'expensive_gifts': ["哇！感谢{username}大哥的{gift_name}！太慷慨了！"]
            },
            'comment_reply': {
                'reply_normal_comments': True,
                'reply_probability': 1.0,
                'trigger_keywords': ['主播', '好听']
            }
        },
        'system': {
            'banned_words': ['广告']
        }
    }
    
    def mock_audio_callback(text):
        print(f"[语音输出] {text}")
    
    # 创建AI主持人
    ai_host = AIGameHost(config, mock_audio_callback)
    ai_host.start()
    
    # 模拟事件
    test_events = [
        {'type': 'member_join', 'username': '新用户123'},
        {'type': 'comment', 'username': '玩家A', 'content': '主播声音好听'},
        {'type': 'gift', 'username': '大佬666', 'gift_name': '火箭', 'gift_count': 1, 'is_expensive': True},
        {'type': 'comment', 'username': '玩家B', 'content': '答案是A！'}
    ]
    
    for event in test_events:
        ai_host.handle_event(event)
        time.sleep(2)
    
    # 等待处理完成
    time.sleep(5)
    
    # 显示统计
    stats = ai_host.get_stats()
    print(f"互动统计: {stats}")
    
    ai_host.stop()