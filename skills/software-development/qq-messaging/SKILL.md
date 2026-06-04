---
name: qq-messaging
title: QQ消息发送自动化
description: 使用computer_use工具自动化发送QQ消息给指定好友
tags: [qq, desktop-automation, windows, cua-driver]
trigger: 当用户需要给QQ好友发送消息时使用此技能
---

# QQ消息发送自动化技能

## 概述
此技能提供使用Hermes Agent的`computer_use`工具（基于cua-driver）在Windows系统上自动化发送QQ消息的标准化流程。**不使用任何Python脚本**，直接调用原生工具。

## 核心原理
- 使用`computer_use`工具直接驱动QQ桌面应用程序
- 基于Windows的UI Automation (UIA)技术
- 完全使用Hermes Agent内置工具，无需额外脚本
- **已验证在Windows 10系统上正常工作**，尽管工具文档标注"macOS only"，但实际测试通过

## 操作模式

### 模式1：直接执行（推荐）
当用户说："给[好友姓名]发送[消息内容]"

**执行步骤：**
1. `computer_use(action='capture', app='QQ', mode='ax')` - 确认QQ在前台
2. `computer_use(action='click', element=42)` - 点击搜索框（元素#42，标签"搜索"）
3. `computer_use(action='type', text='好友姓名')` - 输入好友姓名
4. `computer_use(action='key', keys='return')` - 回车搜索
5. `computer_use(action='wait', seconds=2)` - 等待搜索完成
6. `computer_use(action='type', text='消息内容')` - 输入消息
7. `computer_use(action='key', keys='return')` - 回车发送
8. `computer_use(action='capture', app='QQ', mode='ax', max_elements=150)` - 验证发送结果

### 模式2：参数化调用
当需要批量发送或灵活控制时，按上述步骤逐个调用工具。

## 通用性保证

### 1. 换好友
- 只需将步骤3中的`text='好友姓名'`替换为目标好友姓名
- 示例：`computer_use(action='type', text='张三')`

### 2. 换消息
- 只需将步骤6中的`text='消息内容'`替换为目标消息
- 示例：`computer_use(action='type', text='你好，这是测试消息')`

### 3. 完全通用
- 每个工具调用都是独立的
- 参数可动态替换
- 无需修改代码结构

## 实际工具调用示例

### 示例1：给"张志文"发送测试消息
```
1. computer_use(action='capture', app='QQ', mode='ax')
2. computer_use(action='click', element=42)
3. computer_use(action='type', text='张志文')
4. computer_use(action='key', keys='return')
5. computer_use(action='wait', seconds=2)
6. computer_use(action='type', text='测试消息：这是通过qq-messaging技能发送的测试')
7. computer_use(action='key', keys='return')
8. computer_use(action='capture', app='QQ', mode='ax', max_elements=150)
```

### 示例2：给"李四"发送不同消息
```
1. computer_use(action='capture', app='QQ', mode='ax')
2. computer_use(action='click', element=42)
3. computer_use(action='type', text='李四')
4. computer_use(action='key', keys='return')
5. computer_use(action='wait', seconds=2)
6. computer_use(action='type', text='会议改到明天下午3点')
7. computer_use(action='key', keys='return')
8. computer_use(action='capture', app='QQ', mode='ax', max_elements=150)
```

## 关键注意事项

### 搜索后自动进入
- 搜索完成后QQ会自动进入目标好友的聊天界面
- **不需要**点击搜索结果按钮
- 点击按钮反而可能导致进入好友卡片界面

### 避免使用ESC键
- **不要按ESC键**，这会导致退出QQ界面
- 如果意外退出，重新搜索即可

### 元素索引验证
Answer: 搜索框是元素#42（标签为"搜索"）
- 使用前建议先捕获界面确认：`computer_use(action='capture', app='QQ', mode='ax')`
- 查看元素标签是否为"搜索"

## 常见问题解决

### Q1：搜索框元素索引变化怎么办？
A：先捕获界面查看当前元素结构：
```python
computer_use(action='capture', app='QQ', mode='ax')
```
在结果中查找标签为"搜索"的Edit元素

### Q2：消息发送失败怎么办？
A：检查步骤：
1. 确认输入框焦点正确
2. 消息输入后必须按回车键
3. 检查网络连接状态
4. 重新执行发送步骤

### Q3：界面无响应怎么办？
A：
1. 增加等待时间：`computer_use(action='wait', seconds=3)`
2. 重新捕获界面确认状态
3. 检查QQ进程是否正常运行

## 最佳实践

1. **先捕获后操作**：每次重要操作前先捕获界面确认状态
2. **使用元素索引**：优先使用元素索引而非坐标点击
3. **适当等待**：操作间添加合理等待时间（2-3秒）
4. **验证结果**：关键操作后验证执行结果

## 性能优化
- 使用`mode='ax'`代替`mode='som'`可减少token消耗
- 适当调整`max_elements`参数控制返回数据量
- 批量操作时考虑添加操作间隔避免QQ卡顿

## 模型兼容性注意事项

### 重要发现：模型图像输入支持限制
基于2026年6月2日的测试，某些模型可能不支持图像输入：

**当前不兼容的模型**：
- `deepseek-v3-2-251201`（测试配置）
- 症状：`mode='som'`失败，`mode='vision'`失败，只有`mode='ax'`工作

**影响的操作**：
1. **无法看到**带编号的截图覆盖层
2. **无法进行**视觉状态验证
3. **只能使用**文本模式进行元素识别

### 无视觉支持时的替代方案
```python
# 使用文本模式捕获界面
computer_use(action='capture', app='QQ', mode='ax', max_elements=150)

# 在返回结果中查找元素
# 搜索框：查找标签包含"搜索"的Edit元素
# 联系人：查找标签包含联系人姓名的ListItem元素
# 输入框：查找标签包含"输入"的Edit元素
```

## 用户验证要求

### 基于实际界面的操作
**用户明确要求**：操作必须基于实际看到的界面元素，而不是假设或推断。

**关键用户反馈**：
> "你没打开界面你怎么截图的？你怎么知道有搜索按钮的？难道是推断的？"

**正确做法**：
1. **始终先捕获**当前界面状态
2. **验证元素存在**于当前捕获中
3. **基于验证结果**执行操作
4. **请求用户确认**关键操作结果

### 操作验证流程
```python
# 1. 捕获当前界面
result = computer_use(action='capture', app='QQ', mode='ax')

# 2. 验证搜索框存在
search_box_found = False
for elem in result['elements']:
    if '搜索' in elem.get('label', ''):
        search_box_found = True
        search_box_idx = elem['index']
        break

if not search_box_found:
    print("找不到搜索框，请确认QQ界面已打开")
    return

# 3. 执行操作
computer_use(action='click', element=search_box_idx)

# 4. 请求用户验证
print("已点击搜索框，请确认搜索框已获得焦点并可以输入")
```

### 消息发送后的验证
```python
# 完成所有发送步骤后
print("已完成消息发送操作，所有工具调用返回成功。")
print("请检查与[好友姓名]的QQ聊天记录，确认是否收到了消息。")

# 处理用户反馈
# 如果用户说"没有收到"：立即重新尝试完整流程
# 如果用户说"收到了"：记录成功模式
```

## 工具行为一致性期望

### 用户对一致性的关注
**用户反馈**：
> "我是5.31号让你操作qq的，你是可以识别qq界面的按钮，应该是截图的吧，我的模型一直是deepseek"

**含义**：
1. 用户注意并跟踪工具行为的一致性
2. 期望在不同会话中保持相同能力
3. 当出现不一致时，需要立即调查和解释

### 一致性检查清单
1. **元素识别**：搜索框是否仍然是元素#42？
2. **界面布局**：QQ界面是否发生变化？
3. **操作流程**：搜索后是否仍然自动进入聊天？
4. **模型能力**：当前模型是否支持必要的功能？

### 处理不一致性
当用户指出不一致时：
1. **立即调查**：检查当前界面状态
2. **对比历史**：参考5月31日的成功记录
3. **解释原因**：说明可能的变化（界面更新、模型限制等）
4. **调整方法**：根据当前情况调整操作流程