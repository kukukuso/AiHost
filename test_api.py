#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API测试脚本
用于验证Qwen API连接和功能测试
"""

import os
import sys
import time
from dotenv import load_dotenv
from loguru import logger

# 导入项目模块
try:
    from qwen_api import QwenAPIManager, EnhancedResponseGenerator
    from audio_output import AudioOutputManager
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("💡 请确保在项目根目录运行此脚本")
    sys.exit(1)


def test_environment():
    """测试环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ Python版本过低，需要3.7或更高版本")
        return False
    else:
        print(f"✅ Python版本: {sys.version}")
    
    # 加载环境变量
    load_dotenv()
    
    # 检查API密钥
    api_key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('QWEN_API_KEY')
    if not api_key:
        print("❌ 未找到API密钥")
        print("💡 请在.env文件中设置 DASHSCOPE_API_KEY 或 QWEN_API_KEY")
        return False
    else:
        print(f"✅ API密钥: {api_key[:10]}...{api_key[-4:]}")
    
    print("✅ 环境配置检查通过\n")
    return True


def test_qwen_api():
    """测试Qwen API连接"""
    print("🤖 测试Qwen API连接...")
    
    try:
        # 配置参数
        config = {
            'qwen_api': {
                'provider': 'dashscope',
                'model_name': 'qwen-turbo'  # 使用最便宜的模型进行测试
            },
            'max_tokens': 50,
            'temperature': 0.8,
            'top_p': 0.9,
            'timeout': 10,
            'max_retries': 3
        }
        
        # 创建API管理器
        api_manager = QwenAPIManager(config)
        
        # 测试基础连接
        if api_manager.test_connection():
            print("✅ API连接测试成功")
            
            # 测试不同类型的回复
            test_cases = [
                {
                    'prompt': '用户小明说：主播声音好听',
                    'expected_type': '夸奖回复'
                },
                {
                    'prompt': '用户大佬666送出了火箭（高价值礼物）',
                    'expected_type': '感谢回复'
                },
                {
                    'prompt': '新用户萌新123进入了直播间',
                    'expected_type': '欢迎回复'
                }
            ]
            
            print("\n📝 测试AI回复生成...")
            personality = "你是一个活泼可爱的AI主播助手，说话风趣幽默，回复要简短（不超过20字）。"
            generator = EnhancedResponseGenerator(personality, api_manager)
            
            for i, test_case in enumerate(test_cases, 1):
                print(f"\n测试 {i}: {test_case['expected_type']}")
                print(f"输入: {test_case['prompt']}")
                
                try:
                    response = api_manager.generate_response(
                        test_case['prompt'],
                        personality
                    )
                    print(f"输出: {response}")
                    print(f"长度: {len(response)} 字符")
                    
                    if len(response) > 50:
                        print("⚠️  回复过长，建议调整参数")
                    else:
                        print("✅ 回复长度合适")
                        
                except Exception as e:
                    print(f"❌ 生成失败: {e}")
            
            return True
        else:
            print("❌ API连接测试失败")
            return False
            
    except Exception as e:
        print(f"❌ Qwen API测试失败: {e}")
        return False


def test_audio_system():
    """测试音频系统"""
    print("\n🔊 测试音频系统...")
    
    try:
        # 音频配置
        config = {
            'audio_output': {
                'device_index': None,
                'sample_rate': 22050,
                'channels': 1,
                'chunk_size': 1024,
                'audio_cache_size': 10
            },
            'model_config': {
                'primary_model': 'qwen-api',
                'fallback_tts': 'edge-tts'
            },
            'ai_personality': {
                'voice_style': '甜美女声'
            },
            'system': {
                'save_audio_files': False
            }
        }
        
        # 创建音频管理器
        audio_manager = AudioOutputManager(config)
        print("✅ 音频管理器初始化成功")
        
        # 启动音频系统
        audio_manager.start()
        print("✅ 音频系统启动成功")
        
        # 测试语音合成
        test_texts = [
            "这是一个语音测试",
            "大家好，我是AI主播助手！"
        ]
        
        print("\n📢 测试语音合成...")
        for i, text in enumerate(test_texts, 1):
            print(f"测试 {i}: {text}")
            try:
                audio_manager.speak(text)
                print("✅ 语音合成成功")
                time.sleep(2)  # 等待播放
            except Exception as e:
                print(f"❌ 语音合成失败: {e}")
        
        # 停止音频系统
        audio_manager.stop()
        print("✅ 音频系统停止成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 音频系统测试失败: {e}")
        return False


def test_integration():
    """集成测试"""
    print("\n🔗 进行集成测试...")
    
    try:
        # 模拟事件数据
        test_events = [
            {
                'type': 'comment',
                'username': '测试用户',
                'content': '主播声音真好听！',
                'user_id': 'test_001',
                'timestamp': int(time.time())
            },
            {
                'type': 'gift',
                'username': '大佬666',
                'gift_name': '火箭',
                'gift_count': 1,
                'gift_value': 1000,
                'is_expensive': True,
                'user_id': 'test_002',
                'timestamp': int(time.time())
            },
            {
                'type': 'member_join',
                'username': '新用户123',
                'user_id': 'test_003',
                'timestamp': int(time.time())
            }
        ]
        
        # API配置
        api_config = {
            'qwen_api': {
                'provider': 'dashscope',
                'model_name': 'qwen-turbo'
            },
            'max_tokens': 50,
            'temperature': 0.8,
            'top_p': 0.9,
            'timeout': 10,
            'max_retries': 3
        }
        
        # 音频配置
        audio_config = {
            'audio_output': {
                'device_index': None,
                'sample_rate': 22050,
                'channels': 1,
                'audio_cache_size': 10
            },
            'model_config': {
                'primary_model': 'qwen-api',
                'fallback_tts': 'edge-tts'
            },
            'ai_personality': {
                'voice_style': '甜美女声'
            },
            'system': {
                'save_audio_files': False
            }
        }
        
        # 初始化组件
        api_manager = QwenAPIManager(api_config)
        audio_manager = AudioOutputManager(audio_config)
        
        personality = "你是一个活泼可爱的AI主播助手，说话要简短有趣。"
        generator = EnhancedResponseGenerator(personality, api_manager)
        
        audio_manager.start()
        
        print("✅ 组件初始化成功")
        
        # 测试事件处理流程
        print("\n🎭 测试事件处理流程...")
        for i, event in enumerate(test_events, 1):
            print(f"\n事件 {i}: {event['type']}")
            print(f"详情: {event}")
            
            try:
                # 生成回复
                response = generator.generate_response(event)
                print(f"AI回复: {response}")
                
                # 语音播放
                audio_manager.speak(response)
                print("✅ 语音播放成功")
                
                time.sleep(3)  # 等待播放完成
                
            except Exception as e:
                print(f"❌ 事件处理失败: {e}")
        
        audio_manager.stop()
        print("\n✅ 集成测试完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🎮 AI抖音弹幕游戏主持人 - API测试工具")
    print("=" * 60)
    
    # 测试步骤
    tests = [
        ("环境配置", test_environment),
        ("Qwen API", test_qwen_api),
        ("音频系统", test_audio_system),
        ("集成测试", test_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name}测试 {'='*20}")
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}测试通过")
            else:
                print(f"❌ {test_name}测试失败")
        except KeyboardInterrupt:
            print(f"\n⏹️  用户中断测试")
            break
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
    
    # 输出测试结果
    print("\n" + "="*60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统可以正常使用")
        print("\n💡 下一步:")
        print("1. 配置你的直播间ID到 config.yaml")
        print("2. 调整AI人格和回复策略")
        print("3. 运行 python main.py 启动系统")
    else:
        print("⚠️  部分测试失败，请检查配置和网络连接")
        print("\n💡 建议:")
        print("1. 检查API密钥是否正确")
        print("2. 确认网络连接正常")
        print("3. 查看具体错误信息并修复")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 测试已退出")
    except Exception as e:
        print(f"\n❌ 测试程序异常: {e}")
        sys.exit(1)