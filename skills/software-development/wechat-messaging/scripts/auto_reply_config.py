#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信自动回复配置文件
"""

import os

# 基础路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(BASE_DIR)

# 临时截图目录（用完自动删除）
TEMP_SCREENSHOT_DIR = os.path.join(SKILL_DIR, "temp_screenshots")

# 监控的好友列表（可以在这里添加需要监控的好友）
MONITOR_FRIENDS = [
    "AI数字人",
    # 可以在这里添加更多需要监控的好友
]

# 置信度阈值（0-100），超过这个值自动回复
CONFIDENCE_THRESHOLD = 80

# 轮询间隔（秒）
POLL_INTERVAL = 5

# 预设回复模板
PRESET_REPLIES = {
    "默认": "你好！我现在有点忙，稍后回复你。",
    "问候": "你好呀！很高兴收到你的消息！",
    "开心": "哈哈，听起来很不错！",
    "疑问": "这个问题我需要想一想，稍后回复你。",
    "感谢": "不客气！能帮到你我很开心。",
}

# 对话历史保存文件
CHAT_HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")
