#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天记录持久化管理模块
支持按好友分别存储，JSON格式持久化
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional

# 聊天数据目录
CHAT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chat_data')

# 确保目录存在
os.makedirs(CHAT_DATA_DIR, exist_ok=True)


def get_chat_history_path(friend_name: str) -> str:
    """获取指定好友的聊天记录文件路径"""
    # 清理文件名中的特殊字符
    safe_name = ''.join(c for c in friend_name if c.isalnum() or c in (' ', '-', '_'))
    safe_name = safe_name.strip().replace(' ', '_')
    return os.path.join(CHAT_DATA_DIR, f'{safe_name}.json')


def load_chat_history(friend_name: str) -> Dict:
    """加载指定好友的聊天记录"""
    file_path = get_chat_history_path(friend_name)
    
    if not os.path.exists(file_path):
        # 如果文件不存在，返回空结构
        return {
            "friend_name": friend_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "total_messages": 0,
            "messages": []
        }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载聊天记录失败: {e}")
        return {
            "friend_name": friend_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "total_messages": 0,
            "messages": []
        }


def save_chat_history(friend_name: str, history: Dict) -> bool:
    """保存指定好友的聊天记录"""
    file_path = get_chat_history_path(friend_name)
    
    try:
        history["updated_at"] = datetime.now().isoformat()
        history["total_messages"] = len(history.get("messages", []))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存聊天记录失败: {e}")
        return False


def add_message(friend_name: str, role: str, content: str, msg_time: str = None) -> bool:
    """添加一条新消息到聊天记录
    
    Args:
        friend_name: 好友名称
        role: 消息角色 ('对方' 或 '我')
        content: 消息内容
        msg_time: 消息时间（如果不提供则使用当前时间）
    """
    history = load_chat_history(friend_name)
    
    if msg_time is None:
        msg_time = datetime.now().strftime("%H:%M")
    
    message = {
        "role": role,
        "content": content,
        "time": msg_time,
        "timestamp": datetime.now().isoformat()
    }
    
    history["messages"].append(message)
    
    return save_chat_history(friend_name, history)


def get_recent_messages(friend_name: str, n: int = 10) -> List[Dict]:
    """获取最近n条消息"""
    history = load_chat_history(friend_name)
    messages = history.get("messages", [])
    return messages[-n:] if len(messages) > n else messages


def get_all_friends_with_history() -> List[str]:
    """获取所有有聊天记录的好友列表"""
    friends = []
    if os.path.exists(CHAT_DATA_DIR):
        for filename in os.listdir(CHAT_DATA_DIR):
            if filename.endswith('.json'):
                friend_name = filename[:-5].replace('_', ' ')
                friends.append(friend_name)
    return friends


def print_chat_history(friend_name: str, n: int = None):
    """打印聊天记录（用于调试）"""
    history = load_chat_history(friend_name)
    messages = history.get("messages", [])
    
    print(f"\n{'='*60}")
    print(f"聊天记录: {friend_name}")
    print(f"总消息数: {len(messages)}")
    print(f"最后更新: {history.get('updated_at', 'N/A')}")
    print(f"{'='*60}\n")
    
    messages_to_print = messages[-n:] if n and n > 0 else messages
    
    for msg in messages_to_print:
        role = msg.get('role', '?')
        content = msg.get('content', '')
        time = msg.get('time', '')
        
        if role == '我':
            print(f"[{time}] 🟢 我: {content}")
        else:
            print(f"[{time}] ⚪ {role}: {content}")
    
    print(f"\n{'='*60}\n")


def clear_chat_history(friend_name: str) -> bool:
    """清空指定好友的聊天记录（谨慎使用）"""
    file_path = get_chat_history_path(friend_name)
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"删除聊天记录失败: {e}")
            return False
    return True


# 测试代码
if __name__ == '__main__':
    print("聊天记录管理模块测试\n")
    
    # 测试添加消息
    test_friend = "测试好友"
    print(f"1. 添加消息到 '{test_friend}'...")
    
    add_message(test_friend, "对方", "你好呀！", "10:00")
    add_message(test_friend, "我", "你好，有什么事吗？", "10:01")
    add_message(test_friend, "对方", "哈哈哈，没事，就是打个招呼", "10:02")
    
    print("   ✅ 消息添加完成\n")
    
    # 测试读取最近消息
    print(f"2. 读取最近2条消息...")
    recent = get_recent_messages(test_friend, 2)
    for msg in recent:
        print(f"   [{msg['time']}] {msg['role']}: {msg['content']}")
    print("   ✅ 读取完成\n")
    
    # 测试打印完整历史
    print(f"3. 打印完整聊天记录...")
    print_chat_history(test_friend)
    
    # 查看所有有聊天记录的好友
    print(f"4. 所有有聊天记录的好友:")
    friends = get_all_friends_with_history()
    for friend in friends:
        print(f"   - {friend}")
    
    print("\n✅ 测试完成！")
