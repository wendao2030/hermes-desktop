#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息发送模块
- 点击输入框
- 剪贴板粘贴
- Enter发送
"""

import time
import win32gui
import win32clipboard
import ctypes
from wechat_window import click_window_point


def set_clipboard_text(text):
    """设置剪贴板文本"""
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()


def send_wechat_message(hwnd, message, window_width, window_height):
    """
    发送微信消息
    
    Args:
        hwnd: 微信窗口句柄
        message: 要发送的消息内容
        window_width: 窗口宽度
        window_height: 窗口高度
    
    Returns:
        bool: 是否发送成功
    """
    keyboard = ctypes.windll.user32
    VK_CONTROL = 0x11
    VK_V = 0x56
    VK_RETURN = 0x0D
    
    # 1. 确保窗口在前台
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    
    # 2. 点击输入框位置（距离底部92像素）
    input_x = window_width // 2
    input_y = window_height - 92
    
    # 多点击几次确保激活
    for i in range(3):
        click_window_point(hwnd, input_x, input_y)
        time.sleep(0.15)
    
    time.sleep(0.3)
    
    # 3. 复制到剪贴板
    set_clipboard_text(message)
    time.sleep(0.3)
    
    # 4. Ctrl+V 粘贴
    keyboard.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.05)
    keyboard.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.1)
    keyboard.keybd_event(VK_V, 0, 2, 0)
    time.sleep(0.05)
    keyboard.keybd_event(VK_CONTROL, 0, 2, 0)
    
    time.sleep(0.6)
    
    # 5. Enter 发送
    keyboard.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.1)
    keyboard.keybd_event(VK_RETURN, 0, 2, 0)
    
    time.sleep(1.0)
    
    return True
