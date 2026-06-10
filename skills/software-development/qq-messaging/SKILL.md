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
5. `computer_use(action='wait', seconds=2)` - **等待搜索完成**（重要！）
6. `computer_use(action='key', keys='return')` - **再次按回车键**，选择搜索结果中的第一个（通常是搜索的联系人）
7. `computer_use(action='wait', seconds=2)` - **等待进入聊天界面**
8. `computer_use(action='type', text='消息内容')` - 输入消息
9. `computer_use(action='key', keys='return')` - 回车发送
10. `computer_use(action='capture', app='QQ', mode='ax', max_elements=150)` - 验证发送结果

**重要警告**：
- **步骤6绝对不能省略**：必须按回车键选择搜索结果
- **绝对不要按方向键**：方向键↓会选中第二个结果，导致消息发错人
- **必须等待足够时间**：步骤5和7的等待确保界面完全加载

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
4. computer_use(action='key', keys='return')  # 搜索
5. computer_use(action='wait', seconds=2)     # 等待搜索完成
6. computer_use(action='key', keys='return')  # **重要**：选择搜索结果中的第一个
7. computer_use(action='wait', seconds=2)     # 等待进入聊天界面
8. computer_use(action='type', text='测试消息：这是通过qq-messaging技能发送的测试')
9. computer_use(action='key', keys='return')  # 发送
10. computer_use(action='capture', app='QQ', mode='ax', max_elements=150)
```

### 示例2：给"李四"发送不同消息
```
1. computer_use(action='capture', app='QQ', mode='ax')
2. computer_use(action='click', element=42)
3. computer_use(action='type', text='李四')
4. computer_use(action='key', keys='return')  # 搜索
5. computer_use(action='wait', seconds=2)     # 等待搜索完成
6. computer_use(action='key', keys='return')  # **重要**：选择搜索结果中的第一个
7. computer_use(action='wait', seconds=2)     # 等待进入聊天界面
8. computer_use(action='type', text='会议改到明天下午3点')
9. computer_use(action='key', keys='return')  # 发送
10. computer_use(action='capture', app='QQ', mode='ax', max_elements=150)
```

## 关键注意事项

### cua-driver 新会话必须先 capture（重要）
cua-driver 在每个新 Hermes 会话里第一次执行 `key`/`type` 操作前，**必须**先调用一次 `capture`，否则返回错误：
```
"No active window — call capture() first."
```
本技能步骤1的 `capture(app='QQ', mode='ax')` 同时承担了这个作用，**不要为了"节省 token"把步骤1跳过直接发快捷键**。即使你已经知道目标窗口和元素索引，第一次操作前的 capture 也是必需的。

### 搜索后必须按回车键选择（重要更新）
基于2026年6月4日的经验教训：
- **搜索后第一个结果默认被选中**（通常是搜索的联系人）
- **必须按一次回车键**选择这个结果
- **绝对不要按方向键**（方向键↓会选中第二个结果，导致错误）
- 等待2秒让界面加载完成

**正确流程**：
```
搜索 → 回车（搜索） → 等待2秒 → 回车（选择第一个结果） → 等待2秒 → 输入消息
```

**错误流程**（避免）：
```
搜索 → 回车（搜索） → 方向键↓ → 回车（选择第二个结果） ❌
```

详细教训见：`references/2026-06-04-qq-search-enter-key-lesson.md`

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
5. **用户验证优先**：`ok: true`不等于成功，必须获得用户最终确认
6. **标准化操作**：严格遵循技能中的步骤，避免凭记忆操作

## 沟通风格要求（重要用户偏好）

### 用户身份认知纠正
**用户明确反馈**：
> "你是hermes助手，你不是小美，ta是我的一个员工哦"

**含义**：
1. **正确身份**：Hermes Agent（或Hermes助手）
2. **避免使用**："小美"（这是用户的员工）
3. **沟通风格**：专业、技术导向，避免过度亲昵的称呼
4. **用户偏好**：用户期望代理有明确的身份认知，不混淆角色关系

### 实施指南
1. **自我介绍**：使用"我是Hermes Agent"或"我是Hermes助手"
2. **避免称呼**：不使用"小美"等用户员工的名字
3. **技术沟通**：保持专业、清晰的技术解释风格
4. **身份明确**：让用户清楚知道正在与AI助手对话，不是人类员工

### 技能使用纪律
**用户明确期望**：代理必须优先使用现有技能而不是凭记忆操作

**历史反馈**：
> "你没有发送成功，你是不是没有用之前自己提炼的qq-message这个技能？导致你犯了之前返国的错误"

**核心原则**：
- **技能优先**：必须使用已创建的技能
- **避免凭记忆**：凭记忆操作可能导致重复已知错误
- **技能包含改进**：技能中已经包含了改进方法

**实施纪律**：
1. **执行QQ操作前**：首先加载`skill_view(name='qq-messaging')`
2. **严格遵循流程**：按照技能中的标准化步骤执行
3. **避免重复错误**：技能中的经验教训可以防止重复已知错误
4. **主动技能维护**：发现技能问题或改进点时立即更新

### 验证流程
1. **完成所有发送步骤**后，请求用户检查QQ聊天记录
2. **如果用户说"没有收到"**：立即重新尝试完整流程
3. **检查常见错误**：
   - 是否按了方向键？（导致选中错误联系人）
   - 是否按了足够的回车键？（需要两次：搜索一次，选择一次）
   - 是否等待足够时间？（界面加载需要2秒）

### 用户反馈处理
**用户说"没有收到"时的应对**：
1. **立即道歉**："抱歉，让我重新尝试"
2. **重新执行完整流程**：从步骤1开始
3. **特别注意**：确保步骤6（选择搜索结果）被执行
4. **再次请求验证**：完成后再请用户检查

### 成功模式记录
当用户确认消息成功发送时：
1. **记录成功模式**：使用的具体步骤和参数
2. **更新技能**：将成功经验添加到技能中
3. **建立信心**：相同模式可以重复使用

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