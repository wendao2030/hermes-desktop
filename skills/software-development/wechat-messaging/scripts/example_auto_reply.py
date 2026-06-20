#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信自动回复 - 使用示例

这个模块是对原有 wechat-messaging 技能的扩展，不影响原有功能。
原有功能依然可以正常使用。

新增功能：
1. 自动检测未读消息红点
2. 自动切换到未读好友
3. 识别好友名称，只回复监控列表中的好友
4. 读取聊天记录，根据上下文生成回复
5. 置信度评估，80%以上自动回复
6. 保存对话历史，保持上下文连贯性
7. 截图保存到临时目录，用完自动清理

使用方法：
    python example_auto_reply.py
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wechat_window import find_wechat_window, restore_and_focus, force_foreground
from screenshot_utils import capture_window, cleanup_temp_screenshots
from message_sender import send_wechat_message
from chat_history import add_message, get_recent_context
from auto_reply_config import MONITOR_FRIENDS, CONFIDENCE_THRESHOLD


def print_header():
    """打印标题"""
    print("=" * 60)
    print("微信自动回复系统 v1.0")
    print("=" * 60)
    print(f"监控好友列表: {MONITOR_FRIENDS}")
    print(f"置信度阈值: {CONFIDENCE_THRESHOLD}%")
    print()


def main():
    """主函数 - 单次执行示例"""
    print_header()
    
    # 1. 查找并置顶微信窗口
    print("[步骤 1] 查找微信窗口...")
    wechat = find_wechat_window()
    if not wechat:
        print("❌ 未找到微信窗口，请确保微信已启动")
        return
    
    hwnd = wechat['hwnd']
    window_width = wechat['right'] - wechat['left']
    window_height = wechat['bottom'] - wechat['top']
    print(f"✅ 找到微信窗口: {hwnd}")
    print(f"   窗口大小: {window_width} x {window_height}")
    
    # 置顶窗口
    restore_and_focus(hwnd)
    force_foreground(hwnd)
    print("✅ 微信窗口已置顶")
    print()
    
    # 2. 截图
    print("[步骤 2] 截取微信窗口...")
    screenshot_path = capture_window(hwnd, prefix="check")
    print(f"✅ 截图已保存: {screenshot_path}")
    print()
    print("⚠  接下来需要:")
    print("   1. 调用 vision_analyze 检测红色未读数字")
    print("   2. 如果有未读，点击红点切换好友")
    print("   3. 识别好友名称")
    print("   4. 如果是监控好友，读取聊天记录")
    print("   5. 生成回复 + 置信度评估")
    print("   6. 置信度 >= 80% 自动发送")
    print("   7. 清理临时截图")
    print()
    
    print("💡 提示：")
    print("   由于 Hermes 工具只能在对话中调用，实际的轮询脚本")
    print("   需要把 vision_analyze 的调用集成到 Hermes 工作流中。")
    print()
    print("   这个示例展示了除视觉识别之外的所有底层功能。")
    print()
    
    # 3. 清理临时截图（实际使用时在流程结束后调用）
    # deleted = cleanup_temp_screenshots()
    # print(f"✅ 清理了 {deleted} 张临时截图")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断，退出程序")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
