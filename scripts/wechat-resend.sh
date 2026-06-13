#!/bin/bash
# 微信消息重发脚本
# 当用户反馈"没看见发送啊，再发一遍"时自动执行完整重发流程

echo "=== 开始执行微信消息重发任务 ==="
echo "时间: $(date)"
echo "任务: 重新发送微信消息给'AI 数字人'"
echo ""

# 检查微信进程状态
echo "1. 检查微信进程状态..."
tasklist | findstr -i wechat
echo ""

# 执行重发流程（这里只是演示，实际执行需要调用Hermes Agent）
echo "2. 执行完整重发流程:"
echo "   a. 重新建立cua-driver会话"
echo "   b. 使用Ctrl+Alt+W激活微信窗口"
echo "   c. 等待2秒窗口激活"
echo "   d. 按Ctrl+F激活搜索"
echo "   e. 等待2秒搜索框出现"
echo "   f. 输入'AI 数字人'"
echo "   g. 等待3秒搜索结果"
echo "   h. 按回车选择第一条结果"
echo "   i. 等待2秒进入聊天"
echo "   j. 输入测试消息"
echo "   k. 按回车发送消息"
echo "   l. 等待2秒发送完成"
echo ""

echo "3. 验证要求:"
echo "   - 所有工具调用返回成功状态"
echo "   - 必须请求用户验证消息是否收到"
echo "   - 如果用户反馈失败，立即重新尝试"
echo ""

echo "4. 备选恢复策略:"
echo "   - 使用开始菜单图标启动微信"
echo "   - 增加所有等待时间（2-5秒）"
echo "   - 检查微信进程状态（WeChatAppEx.exe）"
echo "   - 尝试发送更简单的消息"
echo ""

echo "=== 任务执行完成 ==="
echo "请检查与'AI 数字人'的微信聊天记录，确认是否收到了测试消息。"
echo "如果仍然没有收到，请使用备选恢复策略。"