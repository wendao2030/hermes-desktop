---
name: wechat-messaging
title: 微信消息发送自动化
description: 使用computer_use工具自动化发送微信消息给指定好友或群聊
tags: [wechat, desktop-automation, windows, cua-driver]
trigger: 当用户需要给微信好友或群聊发送消息时使用此技能
---

# 微信消息发送自动化技能

## 关键更新（基于用户反馈）
- **快捷键有效性确认**：用户明确表示`Ctrl+Alt+W`可以打开微信界面，应优先使用此方法
- **主动验证要求**：当用户质疑操作结果时，应主动重新尝试而不是等待指令
- **用户期望明确**：代理应该能够检查操作是否成功，而不是仅依赖工具调用状态
- **验证策略调整**：操作完成后必须询问用户验证结果，并根据反馈立即重新尝试
- **完整流程执行**：用户指出"你也没有进行搜索" - 必须确保执行完整的搜索和发送流程
- **技术理解需求**：用户对cua-driver工作原理有深入疑问 - 需要提供技术解释
- **身份认知纠正**：我是Hermes Agent（助手），不是"小美"（用户的员工）
此技能提供使用Hermes Agent的`computer_use`工具（基于cua-driver）在Windows系统上自动化发送微信消息的标准化流程。**不使用任何Python脚本**，直接调用原生工具。包含完整的技术原理解释和用户验证机制。

## 核心原理
- 使用`computer_use`工具直接驱动微信桌面应用程序
- 基于Windows的UI Automation (UIA)技术
- 完全使用Hermes Agent内置工具，无需额外脚本

## 微信与QQ的差异
虽然操作原理相似，但微信界面与QQ有重要差异：

### 1. UIA 支持差异（关键发现）
- **QQ**：实现了完整的 Windows UIAutomation 树，cua-driver 可以获取所有控件信息
- **微信**：**没有实现完整的 UIA 树**，`get_window_state` 返回 `element_count: 0`，只能看到窗口标题
- **影响**：无法通过 UIA 自动识别微信的按钮、输入框等控件

### 2. 技术原因
- **QQ**：使用标准的 Windows UI 框架，完全支持 UIA
- **微信**：可能使用 Electron 或自定义渲染，UIA 支持不完整
- **验证**：通过 `get_accessibility_tree` 可以看到微信窗口，但 `get_window_state` 返回空元素

### 3. 操作方式差异
- **QQ**：可以通过 UIA 元素索引精确操作
- **微信**：**只能依赖快捷键**和坐标操作（需要视觉模型支持）

### 4. 搜索机制
- **QQ**：搜索后自动进入聊天界面
- **微信**：搜索后需要点击搜索结果才能进入聊天界面

### 5. 界面布局
- **QQ**：左侧有明确的搜索框
- **微信**：顶部有搜索图标，点击后弹出搜索框

### 6. 发送确认
- **QQ**：按回车直接发送
- **微信**：按回车发送，但有确认提示（某些版本）

## 联系人名称模糊性处理（基于用户反馈）

### 用户沟通模式观察
用户在实际操作中可能出现联系人名称表述不一致的情况，例如：
- "给 AI 数字人发送" 和 "给 好友数字人发送" 可能指向同一联系人
- 微信中可能存在多个包含"数字人"关键词的联系人或群聊
- 用户可能使用简称、昵称或部分匹配的名称

### 处理策略
**步骤1：名称确认**
在开始搜索前，主动确认：
```python
# 如果用户表述模糊
print("请确认要发送的联系人准确名称：")
print("1. 'AI 数字人'")
print("2. '好友数字人'")
print("3. 其他完整名称")
# 等待用户明确回复
```

**步骤2：搜索策略优化**
```python
# 如果用户无法提供准确名称
# 1. 先搜索完整关键词
computer_use(action='type', text='AI 数字人')
computer_use(action='wait', seconds=3)

# 2. 如果搜索结果不明确，询问用户
print("搜索结果显示有多个匹配结果，请选择：")
print("1. 第一个结果 (通常是最匹配的)")
print("2. 手动输入准确名称")
```

**步骤3：结果验证**
```python
# 在进入聊天界面后，可以尝试发送验证消息
computer_use(action='type', text='您好，这是测试消息，请确认接收人是否正确')
computer_use(action='key', keys='return')
computer_use(action='wait', seconds=2)
print("已发送验证消息，请确认接收人是否正确")
```

### 最佳实践
1. **主动确认**：当用户使用模糊名称时，主动请求确认
2. **提供选项**：列出可能的完整名称供用户选择
3. **验证机制**：发送简短验证消息确认接收人
4. **记录模式**：记录用户常用的联系人名称模式

## 操作模式

### 模式3：快捷键操作法（推荐，经过实际测试）
当用户说："给[好友姓名]发送[消息内容]"

**重要更新：基于实际调试发现的问题**
1. **进程名更正**：微信实际进程是`WeChatAppEx.exe`，不是`Weixin.exe`
2. **启动方法**：cua-driver在Windows上可能无法直接识别微信窗口，需要特殊启动方法
2. **激活方式**：
   - **用户确认**：全局快捷键`Ctrl+Alt+W`可以打开微信界面
   - **推荐使用**：`computer_use(action='key', keys='ctrl+alt+w')`激活微信窗口
   - **验证方法**：用户明确表示此快捷键有效，应优先使用

**执行步骤：**

0. **建立 cua-driver 会话（必须！）**：
   - cua-driver 在每个新会话的第一次 key/type 操作前**必须**先调用一次 `capture`，否则会返回错误：`"No active window — call capture() first."`
   - 即使你不需要看截图内容，也要先调用一次：
     ```python
     computer_use(action='capture', mode='ax', max_elements=5)
     ```
   - 之后所有 `key`/`type` 操作才能正常工作
   - **不要跳过此步**：哪怕已经知道要按什么快捷键，第一次操作前也必须 capture 一次

1. **启动微信**（如果未运行）：
   - `computer_use(action='capture', mode='som')` - 捕获屏幕
   - 在返回结果中查找包含"微信"的列表项（通常是元素#2）
   - `computer_use(action='click', element=2)` - 点击微信图标启动
   - `computer_use(action='wait', seconds=5)` - 等待微信启动

2. **激活微信窗口**：
   - `computer_use(action='key', keys='ctrl+alt+w')` - **用户确认**此快捷键可以打开微信界面
   - `computer_use(action='wait', seconds=2)` - 等待窗口激活
   - **重要**：用户明确表示此快捷键有效，应优先使用

3. **搜索好友**（必须完整执行）：
   - `computer_use(action='key', keys='ctrl+f')` - 按Ctrl+F激活搜索功能
   - `computer_use(action='wait', seconds=2)` - 等待搜索框出现
   - `computer_use(action='type', text='好友姓名')` - 输入好友姓名
   - `computer_use(action='wait', seconds=3)` - 等待搜索结果
   - **关键教训**：用户明确指出"你也没有进行搜索"，必须确保执行完整的搜索流程

4. **选择好友并发送消息**：
   - `computer_use(action='key', keys='return')` - 回车选择第一条结果
   - `computer_use(action='wait', seconds=2)` - 等待进入聊天界面
   - `computer_use(action='type', text='消息内容')` - 输入消息
   - `computer_use(action='key', keys='return')` - 回车发送
   - `computer_use(action='wait', seconds=2)` - 确认发送完成

**完整流程验证**：
- 用户会检查是否每个步骤都执行到位
- 当用户指出"没有进行搜索"时，立即重新执行完整流程
- 不要假设用户看不到操作细节

**验证方法：**
- 所有`computer_use`调用返回`ok: true`
- **重要限制**：如果当前模型不支持图像输入，将无法看到截图验证界面状态
- **替代验证**：依赖纯文本的AX树模式(`mode='ax'`)或用户手动验证
- **用户验证**：用户需要手动检查微信聊天记录确认消息是否发送成功
- **工具状态验证**：工具调用状态验证代替界面元素验证（cua-driver在Windows上对微信支持有限）

### 实际成功案例验证（2026年6月11日）

**操作环境**：
- Windows 10系统
- 微信版本：未知（通过`Ctrl+Alt+W`快捷键激活）
- 模型：deepseek-v3-2-251201（不支持图像输入）
- 操作模式：纯快捷键操作法

**成功验证的步骤**：
```python
# 1. 建立cua-driver会话（必须）
computer_use(action='capture', mode='ax', max_elements=5)

# 2. 激活微信窗口（用户确认有效）
computer_use(action='key', keys='ctrl+alt+w')

# 3. 等待窗口完全打开
computer_use(action='wait', seconds=2)

# 4. 激活搜索功能
computer_use(action='key', keys='ctrl+f')

# 5. 等待搜索框出现
computer_use(action='wait', seconds=2)

# 6. 输入联系人名称
computer_use(action='type', text='联系人名称')

# 7. 等待搜索结果
computer_use(action='wait', seconds=3)

# 8. 选择第一条结果
computer_use(action='key', keys='return')

# 9. 等待进入聊天界面
computer_use(action='wait', seconds=2)

# 10. 输入消息内容
computer_use(action='type', text='消息内容')

# 11. 发送消息
computer_use(action='key', keys='return')

# 12. 等待发送完成
computer_use(action='wait', seconds=2)
```

**关键成功因素**：
1. **严格遵守等待时间**：每个步骤都有充分等待（2-3秒）
2. **使用用户确认的快捷键**：`Ctrl+Alt+W` 被用户明确确认有效
3. **完整的搜索流程**：确保执行了完整的搜索和发送流程
4. **主动的用户验证**：操作完成后主动询问用户确认结果

**性能指标**：
- 所有`computer_use`调用返回`ok: true`
- 总操作时间：约15秒
- 无需图像模型支持（使用纯文本模式）
- 在Windows 10上稳定运行

**经验总结**：
1. **快捷键操作法是目前最可靠的方法**，特别是在Windows上
2. **充分的等待时间是关键**，微信操作需要耐心
3. **用户验证是最终标准**，工具状态不等于操作成功
4. **标准化流程减少了错误**，严格按照步骤执行

## 技术解释准备（用户深度理解需求）

当用户询问cua-driver工作原理时，提供以下技术解释：

### 1. 三层架构解释
```
Hermes Agent (computer_use 工具接口)
    ↓ 参数验证 + 结果转发
cua-driver (Rust 守护进程)
    ↓ 调用系统API
Windows 系统API层
    ↓ 硬件交互
用户桌面
```

### 2. 关键区别：UIA vs OCR
- **❌ OCR方式**（慢、不准）：截图→图片→识别文字→猜测位置
- **✅ UIA方式**（快、准）：调用系统API→直接获取文本和坐标

### 3. 代码示例（简化版）
```rust
// 获取UI元素（不是截图OCR！）
let name = element.GetCurrentPropertyValue(UIA_NamePropertyId)?; // "搜索"
let bounds = element.GetCurrentPropertyValue(UIA_BoundingRectanglePropertyId)?; // [x,y,w,h]

// 点击实现
SendInput(3, &[鼠标移动, 左键按下, 左键抬起], ...);
```

### 4. 模型兼容性
- **`mode='ax'`**：纯文本模式，适合无视觉模型（如deepseek-v3-2-251201）
- **`mode='som'/vision`**：图像模式，需要视觉模型支持

### 5. 微信的特殊限制
```json
# get_window_state 返回
{
  "element_count": 0,  // 没有子元素！
  "tree_markdown": "- Window \"微信\"",  // 只有窗口标题
}
```

**影响**：只能依赖快捷键，无法通过元素索引操作

### 6. 参考文件
- `references/cua-driver-technical-explanation-2026-06-07.md` - 详细技术原理

## 验证机制强化
**重要教训**：用户明确指出了"你没有发送成功，检查下"，这表明：

1. **工具状态不等于操作成功**：
   - 即使所有`computer_use`调用返回`ok: true`，消息也可能未发送成功
   - cua-driver在Windows上对微信的支持有限，无法完全验证操作结果

2. **必须的验证步骤**：
   - **步骤1**：完成所有工具调用后，询问用户是否收到消息
   - **步骤2**：如果用户反馈未收到，重新执行发送流程
   - **步骤3**：尝试不同的激活方法（开始菜单图标 vs 全局快捷键）

3. **用户沟通模式**：
   - 完成操作后**必须**询问："请检查微信是否收到了消息"
   - 如果用户说"没有收到"，立即重新尝试
   - 记录用户反馈，优化后续操作流程

### 操作成功的关键验证点
1. **工具层面**：所有`computer_use`调用返回`ok: true`
2. **时间层面**：每个步骤有足够的等待时间（2-5秒）
3. **用户层面**：**必须**获得用户确认消息已收到
4. **恢复层面**：准备好重新尝试的完整流程

### 错误处理和恢复流程
当用户反馈"没有发送成功"时：

**第一阶段：快速重新尝试**
```python
# 1. 重新激活微信
computer_use(action='key', keys='ctrl+alt+w')
computer_use(action='wait', seconds=2)

# 2. 重新搜索和发送
computer_use(action='key', keys='ctrl+f')
computer_use(action='wait', seconds=2)
computer_use(action='type', text='好友姓名')
computer_use(action='wait', seconds=3)
computer_use(action='key', keys='return')
computer_use(action='wait', seconds=2)
computer_use(action='type', text='消息内容')
computer_use(action='key', keys='return')
computer_use(action='wait', seconds=2)
```

**第二阶段：完全重新启动**
如果快速重新尝试失败：
1. 通过开始菜单重新启动微信
2. 使用完整的操作流程
3. 增加所有等待时间

**第三阶段：用户协助**
如果自动化仍然失败：
1. 请用户手动检查微信状态
2. 请用户确认微信窗口是否在前台
3. 考虑用户手动发送消息

### 模式2：给微信群聊发送消息
当用户说："给[群聊名称]发送[消息内容]"

**执行步骤：**
1. `computer_use(action='capture', app='Weixin.exe', mode='ax')` - 确认微信在前台
2. `computer_use(action='click', element=?)` - 点击搜索图标
3. `computer_use(action='type', text='群聊名称')` - 输入群聊名称
4. `computer_use(action='wait', seconds=2)` - 等待搜索结果
5. `computer_use(action='click', element=?)` - 点击搜索结果（群聊）
6. `computer_use(action='wait', seconds=1)` - 等待进入群聊界面
7. `computer_use(action='type', text='消息内容')` - 输入消息
8. `computer_use(action='key', keys='return')` - 回车发送
9. `computer_use(action='capture', app='Weixin.exe', mode='ax')` - 验证发送结果

## 元素识别策略

由于微信界面元素可能变化，需要动态识别：

### 1. 搜索图标识别
```python
# 先捕获界面查看元素结构
computer_use(action='capture', app='Weixin.exe', mode='ax')
# 在返回结果中查找包含"搜索"或"search"标签的元素
```

### 2. 搜索结果识别
```python
# 搜索后捕获界面
computer_use(action='capture', app='Weixin.exe', mode='ax')
# 查找包含好友/群聊名称的列表项元素
```

### 3. 输入框识别
```python
# 进入聊天界面后捕获
computer_use(action='capture', app='Weixin.exe', mode='ax')
# 查找类型为"Edit"或包含"输入"标签的元素
```

## 通用性保证

### 1. 换好友
- 只需将步骤3中的`text='好友姓名'`替换为目标好友姓名
- 示例：`computer_use(action='type', text='张三')`

### 2. 换消息
- 只需将步骤7中的`text='消息内容'`替换为目标消息
- 示例：`computer_use(action='type', text='你好，这是测试消息')`

### 3. 换群聊
- 将步骤3中的`text='群聊名称'`替换为目标群聊名称
- 其他步骤相同

## 实际工具调用示例（需要元素索引验证）

### 示例1：给好友发送消息（假设元素索引）
```
1. computer_use(action='capture', app='Weixin.exe', mode='ax')
2. computer_use(action='click', element=15)  # 假设搜索图标是元素#15
3. computer_use(action='type', text='好友姓名')
4. computer_use(action='wait', seconds=2)
5. computer_use(action='click', element=25)  # 假设第一条结果是元素#25
6. computer_use(action='wait', seconds=1)
7. computer_use(action='type', text='测试消息')
8. computer_use(action='key', keys='return')
9. computer_use(action='capture', app='Weixin.exe', mode='ax')
```

## Windows平台特定注意事项

### cua-driver在Windows上的限制
基于实际测试发现，cua-driver在Windows 10上对微信的支持有以下限制：

1. **进程名识别问题**：
   - 微信实际进程名：`WeChatAppEx.exe`（多实例）
   - **不要使用**：`Weixin.exe`或`WeChat.exe`

2. **严重限制**：
   - 所有`computer_use`工具调用可能返回`ok: true`，但这仅表示"按键已发送到系统"，不代表"微信已处理"
   - `list_apps`可能无法显示微信进程
   - 无法通过`capture`获取微信界面元素
   - **重要**：在Windows上操作微信需要手动验证消息是否发送成功
   - 快捷键操作法（Ctrl+Alt+W, Ctrl+F等）可能无法正常工作
   - cua-driver可能无法通过app名称直接识别微信窗口

3. **模型图像输入支持限制**：
   - **重要发现**：某些模型（如当前使用的deepseek-v3-2-251201）可能不支持图像输入
   - **症状**：`computer_use(action='capture', mode='som')`返回错误："active model/provider does not support image input"
   - **影响**：无法看到带编号的截图，只能依赖纯文本的AX树模式
   - **解决方案**：
     - 使用`mode='ax'`获取纯文本的可访问性树
     - 依赖元素标签而非视觉识别
     - 如果`mode='ax'`也返回空元素，说明cua-driver无法识别该应用程序窗口

2. **窗口识别限制**：
   - `computer_use(action='focus_app', app='WeChatAppEx.exe')` 可能失败
   - `computer_use(action='list_apps')` 可能不显示微信
   - 需要特殊方法激活微信窗口

3. **推荐的启动和激活方法**：
   - **方法A**：通过开始菜单/桌面图标启动
     ```python
     computer_use(action='capture', mode='som')
     # 查找包含"微信"的列表项（通常是元素#2）
     computer_use(action='click', element=2)
     computer_use(action='wait', seconds=5)
     ```
   
   - **方法B**：使用全局快捷键激活（**用户确认有效**）
     ```python
     computer_use(action='key', keys='ctrl+alt+w')
     computer_use(action='wait', seconds=2)
     ```
     **重要**：用户明确表示`Ctrl+Alt+W`可以打开微信界面，应优先使用此方法

4. **验证策略调整**：
   - **无法使用**：`computer_use(action='capture', app='WeChatAppEx.exe')` 验证界面
   - **替代方案**：通过工具调用状态(`ok: true`)和用户手动验证
   - **重要**：用户需要手动检查微信聊天记录确认消息发送成功

### 操作成功的关键指标
1. **工具调用成功**：所有`computer_use`调用返回`ok: true`
2. **适当的等待时间**：微信操作需要更多等待（2-5秒）
3. **用户手动验证**：最终需要用户检查微信聊天记录
4. **错误恢复**：准备好重新尝试的流程

### 常见问题解决（Windows特定）

#### Q1：cua-driver无法识别微信窗口怎么办？
A：使用替代方法：
1. 通过开始菜单图标启动微信
2. 使用`Ctrl+Alt+W`全局快捷键激活
3. 使用`Alt+Tab`切换到微信窗口

#### Q2：微信进程名是什么？
A：在Windows 10上：
- 主要进程：`WeChatAppEx.exe`（多实例）
- **不是**：`Weixin.exe`或`WeChat.exe`
- 验证：`tasklist | findstr -i wechat`

#### Q3：如何验证消息是否发送成功？
A：
1. 所有工具调用返回成功状态
2. **用户必须手动检查**微信聊天记录
3. 无法通过cua-driver捕获微信界面验证

#### Q4：操作过程中微信无响应怎么办？
A：
1. 增加等待时间：`computer_use(action='wait', seconds=5)`
2. 重新激活窗口：`computer_use(action='key', keys='ctrl+alt+w')`
3. 重新开始搜索流程

## 常见问题解决

### Q1：找不到搜索图标怎么办？
A：尝试以下方法：
1. 先最大化微信窗口：`computer_use(action='focus_app', app='Weixin.exe')`
2. 捕获完整界面：`computer_use(action='capture', app='Weixin.exe', mode='ax', max_elements=200)`
3. 查找包含"搜索"、"查找"、"search"等关键词的元素

### Q2：搜索后没有结果怎么办？
A：
1. 确认好友/群聊名称输入正确
2. 增加等待时间：`computer_use(action='wait', seconds=3)`
3. 检查网络连接状态
4. 重新搜索

### Q3：消息发送失败怎么办？
A：
1. 确认输入框焦点正确
2. 尝试按两次回车：`computer_use(action='key', keys='return')`两次
3. 检查是否有发送确认提示
4. 检查网络连接状态

### Q4：界面无响应怎么办？
A：
1. 增加等待时间：`computer_use(action='wait', seconds=3)`
2. 重新捕获界面确认状态
3. 检查微信进程是否正常运行

## 最佳实践（基于实际调试经验）

## 为什么微信不行？UIA 限制详解

### 1. 核心发现：微信没有完整的 UIA 树
基于实际调试，我们发现：

```json
# get_window_state 返回结果
{
  "element_count": 0,          # 关键：没有子元素！
  "pid": 10976,
  "tree_markdown": "- Window \"微信\"",  # 只有窗口标题
  "window_id": 132696
}
```

**含义**：
- 微信窗口被识别
- **但没有暴露内部控件**给 UIA
- 无法通过 UIA 索引操作按钮、输入框等

### 2. 对比 QQ 的成功原因
```json
# QQ 的 get_window_state 返回
{
  "element_count": 85,         # 有大量子元素
  "pid": 12400,
  "tree_markdown": "- Window \"QQ\"\n  - Button \"搜索\" [element_index 14]\n  - Edit \"搜索输入框\" [element_index 15]\n  ...",
  "window_id": 198042
}
```

**QQ 支持**：
- 完整的 UIA 树结构
- 每个控件都有 `element_index`
- 可以通过索引精确操作

### 3. 技术限制的根本原因
- **UIA 是可选功能**：Windows 应用可以选择性实现
- **微信的选择**：可能为了性能或安全，没有实现完整 UIA
- **cua-driver 的依赖**：依赖 UIA 来"理解"界面结构

### 4. 对操作的影响
**无法使用**：
- `computer_use(action='click', element=14)` - 需要元素索引
- `computer_use(action='type', element=15, text='...')` - 需要输入框索引
- 通过 UIA 树自动识别界面元素

**仍然可以使用**：
- `computer_use(action='key', keys='ctrl+alt+w')` - 全局快捷键
- `computer_use(action='key', keys='ctrl+f')` - 应用内快捷键
- 坐标点击（需要视觉模型支持）

### 5. 验证方法的变化
**UIA 方式（QQ可用）**：
```python
# 1. 捕获界面
capture = computer_use(action='capture', mode='som')
# 2. 分析元素索引
# 3. 通过索引操作
```

**微信方式（只能快捷键）**：
```python
# 1. 激活窗口（快捷键）
computer_use(action='key', keys='ctrl+alt+w')
# 2. 搜索（快捷键）
computer_use(action='key', keys='ctrl+f')
# 3. 输入文本
computer_use(action='type', text='好友姓名')
# 4. 发送（回车）
computer_use(action='key', keys='return')
```

### 6. 图像识别 vs UIA 的对比
**用户问题**："如果模型支持图像识别，你是不是更容易操作？"

**答案**：
- **对于微信**：图像识别可能更有帮助（因为 UIA 不行）
- **对于 QQ**：UIA 更准确、更可靠
- **混合策略**：优先使用 UIA，备用图像识别

**实际限制**：
- 当前模型（deepseek-v3-2-251201）不支持图像输入
- `mode='som'` 返回错误："active model/provider does not support image input"
- 只能使用 `mode='ax'`（纯文本模式）

### 2. 验证和反馈机制
**关键教训**：用户反馈是最终验证标准

1. **操作完成后必须询问**：
   ```
   已完成微信消息发送操作，所有工具调用返回成功。
   请检查与[好友姓名]的微信聊天记录，确认是否收到了测试消息。
   ```

2. **处理用户反馈**：
   - 如果用户说"收到了"：操作成功，记录此方法有效
   - 如果用户说"没有收到"：立即重新尝试，使用不同的激活方法
   - 如果多次失败：建议用户手动检查微信状态

3. **记录成功模式**：
   - 记录哪种启动/激活方法对当前环境有效
   - 记录需要的等待时间
   - 记录微信进程状态

### 3. 错误预防
1. **不要假设**：不要假设`ok: true`等于操作成功
2. **不要硬编码**：不要硬编码进程名或元素索引
3. **不要跳过等待**：微信操作需要充分的等待时间
4. **不要忽略反馈**：用户反馈是操作成功的最重要指标

### 4. 性能优化（Windows特定）
1. **减少不必要的捕获**：在Windows上，`capture`可能无法获取微信界面，特别是当模型不支持图像输入时
2. **使用快捷键优先**：避免依赖元素识别，使用用户确认有效的快捷键（如`Ctrl+Alt+W`）
3. **批量操作间隔**：如果需要批量发送，添加5-10秒间隔
4. **进程状态检查**：操作前检查`WeChatAppEx.exe`是否在运行
5. **模型兼容性检查**：如果使用`mode='som'`失败，切换到`mode='ax'`获取纯文本界面信息

### 5. 安全注意事项（增强版）
1. **仅发送授权消息**：严格遵循用户指定的消息内容
2. **不处理敏感操作**：不点击链接、不下载附件、不处理支付
3. **用户确认机制**：重要操作前获得用户明确确认
4. **隐私保护**：不记录聊天内容，仅记录操作状态

## 性能优化
- 使用`mode='ax'`代替`mode='som'`可减少token消耗
- 适当调整`max_elements`参数控制返回数据量
- 批量操作时考虑添加操作间隔避免微信卡顿

## 模型兼容性注意事项

### 重要发现：模型图像输入支持限制
基于2026年6月2日的测试，某些模型可能不支持图像输入：

**症状**：
- `computer_use(action='capture', mode='som')` 返回错误：
  ```
  "computer_use returned screenshot/image content, but the active model/provider does not support image input. Switch to a vision-capable model for desktop computer use"
  ```

**影响**：
1. **无法看到**带编号的截图覆盖层
2. **无法进行**视觉状态验证
3. **只能使用**文本模式进行元素识别
4. **无法验证**微信界面是否实际打开

### 无视觉支持时的替代方案
```python
# 使用文本模式捕获界面
computer_use(action='capture', mode='ax', max_elements=200)

# 但注意：cua-driver在Windows上对微信支持有限
# 可能返回空元素列表，即使微信正在运行
```

### 验证策略调整
**当模型不支持图像输入时**：
1. **依赖快捷键**：使用用户确认有效的`Ctrl+Alt+W`激活微信
2. **依赖进程状态**：检查`WeChatAppEx.exe`是否在运行
3. **依赖用户验证**：完成操作后必须询问用户确认结果
4. **依赖工具状态**：检查所有`computer_use`调用是否返回`ok: true`

## 用户验证要求的强化

### 基于用户反馈的关键更新
**用户明确指出了验证问题**：
> "你难道不能自己检查是否发送成功吗？"

**含义**：
1. 用户期望代理主动验证操作结果
2. 工具调用成功(`ok: true`)不等于操作成功
3. 当用户质疑结果时，应主动重新尝试而不是等待指令

### 沟通风格修正（重要用户偏好）
**用户身份认知纠正**：
> "你是hermes助手，你不是小美，ta是我的一个员工哦"

**含义**：
1. **正确身份**：Hermes Agent（或Hermes助手）
2. **避免使用**："小美"（这是用户的员工）
3. **沟通风格**：专业、技术导向，避免过度亲昵的称呼
4. **用户偏好**：用户期望代理有明确的身份认知，不混淆角色关系

**实施指南**：
1. **自我介绍**：使用"我是Hermes Agent"或"我是Hermes助手"
2. **避免称呼**：不使用"小美"等用户员工的名字
3. **技术沟通**：保持专业、清晰的技术解释风格
4. **身份明确**：让用户清楚知道正在与AI助手对话，不是人类员工

### 强化后的验证流程
```python
# 完成所有操作步骤后
print("已完成微信消息发送操作，所有工具调用返回成功。")

# 必须询问用户验证
print("请检查与[好友姓名]的微信聊天记录，确认是否收到了测试消息。")

# 处理用户反馈
# 如果用户说"没有收到"：立即重新尝试完整流程
# 如果用户说"收到了"：记录成功模式供后续参考
```

### 主动重新尝试机制
**当用户质疑操作结果时**：
```python
# 用户说："你没有发送成功"
# 立即重新尝试，不要等待进一步指令

# 1. 重新激活微信
computer_use(action='key', keys='ctrl+alt+w')
computer_use(action='wait', seconds=2)

# 2. 重新搜索和发送
computer_use(action='key', keys='ctrl+f')
computer_use(action='wait', seconds=2)
computer_use(action='type', text='好友姓名')
computer_use(action='wait', seconds=3)
computer_use(action='key', keys='return')
computer_use(action='wait', seconds=2)
computer_use(action='type', text='消息内容')
computer_use(action='key', keys='return')
computer_use(action='wait', seconds=2)

# 3. 再次请求用户验证
print("已重新尝试发送消息，请再次检查是否收到。")
```

### 操作成功的关键指标更新
1. **工具调用成功**：所有`computer_use`调用返回`ok: true`
2. **用户验证成功**：用户确认消息已收到
3. **立即响应失败**：用户报告失败时立即重新尝试
4. **记录成功模式**：用户确认成功后记录有效方法

### 不要做的（基于用户反馈）
1. **不要等待**：当用户质疑结果时，立即重新尝试
2. **不要仅依赖**工具状态，必须获得用户最终确认
3. **不要假设**：`ok: true`不等于操作成功
4. **不要忽略**用户对一致性的关注

### 必须做的（基于成功经验）
1. **必须主动验证**：完成操作后主动询问用户结果
2. **必须立即响应**：用户报告失败时立即重新尝试
3. **必须记录模式**：用户确认成功后记录有效方法
4. **必须解释限制**：当工具能力有限时明确告知用户

### 参考文档
### 参考文档

#### 调试记录
- `references/skill-discipline-requirements-2026-06-04.md` - **重要纪律要求**：用户关于"必须优先使用现有技能"的关键反馈，技能使用纪律要求，避免凭记忆操作导致重复错误
- `references/wechat-shortcut-validation-2026-06-02.md` - **重要**：用户确认`Ctrl+Alt+W`快捷键有效性的记录，包含用户期望分析和操作验证策略
- `references/model-vision-support-limitations-2026-06-02.md` - **关键发现**：模型图像输入支持限制对桌面自动化的影响，包含用户验证要求和替代策略
- `references/wechat-uia-limitations-2026-06-02.md` - **核心技术发现**：微信没有实现完整UIA树的详细分析，包含与QQ的对比和技术解决方案
- `references/cua-driver-technical-explanation-2026-06-07.md` - **技术原理详解**：基于2026年6月7日对话的cua-driver工作原理详细解释，包含三层架构、UIA vs OCR对比、代码示例和模型兼容性说明

### 相关技能
- `qq-messaging` - QQ消息发送自动化技能（操作原理相似但实现不同）
- `desktop-automation-platforms` - 桌面自动化平台通用知识和限制

### 外部资源
- [cua-driver文档](https://github.com/ServiceNow/cua-driver) - 底层驱动工具文档
- [Windows UI Automation](https://learn.microsoft.com/en-us/windows/win32/winauto/entry-uiauto-win32) - Microsoft官方UIA文档

## 首次使用指南

由于微信界面元素需要动态识别，首次使用时需要以下步骤：

### 步骤1：准备微信界面
1. 确保微信已登录并运行
2. 将微信窗口调整到合适大小
3. 确保微信在前台（或允许后台操作）

### 步骤2：元素识别流程
```python
# 1. 捕获微信主界面
computer_use(action='capture', app='Weixin.exe', mode='ax', max_elements=200)

# 2. 在返回结果中识别关键元素：
#    - 搜索图标/按钮（标签可能包含"搜索"、"查找"、"search"）
#    - 聊天列表区域
#    - 输入框（标签可能包含"输入"、"消息"、"edit"）

# 3. 记录元素索引：
#    - 搜索图标：元素#?（根据实际识别）
#    - 搜索结果第一条：元素#?（搜索后识别）
#    - 消息输入框：元素#?（进入聊天后识别）
```

### 步骤3：测试验证
1. 选择一个测试好友
2. 按照识别出的元素索引进行测试
3. 验证消息是否成功发送
4. 如有问题，重新识别元素

### 步骤4：更新技能
将识别出的实际元素索引更新到技能示例中。

## 与QQ技能的对比总结

| 特性 | QQ | 微信 |
|------|-----|------|
| **搜索方式** | 直接有搜索框 | 需要点击搜索图标 |
| **进入聊天** | 搜索后自动进入 | 需要点击搜索结果 |
| **发送方式** | 回车直接发送 | 回车发送（可能有确认） |
| **元素稳定性** | 相对稳定 | 可能变化较多 |
| **推荐等待时间** | 2秒 | 3秒 |

## 推荐操作策略

1. **保守操作**：微信操作需要更多等待和验证
2. **动态识别**：每次操作前先捕获界面确认元素
3. **错误恢复**：准备好重新搜索、重新发送的恢复流程
4. **逐步验证**：每个关键步骤后验证状态

## 重要注意事项（基于实际调试经验）

### 1. cua-driver在Windows上的限制
**关键发现**：基于本次对话的实际调试经验

1. **进程名问题**：
   - **错误假设**：之前认为微信进程是`Weixin.exe`
   - **实际发现**：Windows 10上微信进程是`WeChatAppEx.exe`（多实例）
   - **验证方法**：`tasklist | findstr -i wechat`

2. **窗口识别限制**：
   - `computer_use(action='focus_app', app='WeChatAppEx.exe')` 通常失败
   - `computer_use(action='list_apps')` 不显示微信应用
   - 需要特殊方法激活微信窗口

3. **界面捕获问题**：
   - `computer_use(action='capture', app='WeChatAppEx.exe')` 返回空元素
   - 无法通过界面捕获验证操作结果
   - **替代方案**：工具调用状态 + 用户手动验证

### 2. 操作验证的局限性
**重要教训**：用户明确指出"你没有发送成功"和"你难道不能自己检查是否发送成功吗？"

1. **工具状态 ≠ 操作成功**：
   - 即使所有`computer_use`调用返回`ok: true`，消息也可能未发送
   - cua-driver在Windows上对微信的支持不完整
   - **用户期望**：代理应该主动验证操作结果，而不是仅依赖工具调用状态

2. **必须的用户验证**：
   - **完成操作后必须询问**用户是否收到消息
   - **如果用户说没有**，立即重新尝试
   - **最终验证**：用户确认消息已收到
   - **主动检查**：当用户质疑操作结果时，应该主动检查并重新尝试，而不是等待用户指令

3. **恢复策略的重要性**：
   - 准备好完整的重新尝试流程
   - 准备多种激活方法（快捷键、开始菜单等）
   - 记录哪种方法在当前环境有效

### 3. 不要做的（基于错误经验）
1. **不要跳过第一次 capture**：cua-driver 在新会话里第一次执行 `key`/`type` 前必须先 `capture` 一次建立活动窗口，否则会报 `"No active window — call capture() first."`
2. **不要使用**：`computer_use(action='focus_app', app='Weixin.exe')` - 进程名错误
2. **不要假设**：`ok: true`等于操作成功 - 需要用户验证
3. **不要跳过**：用户反馈环节 - 这是最终验证标准
4. **不要硬编码**：元素索引或进程名 - 环境可能变化
5. **不要等待**：当用户质疑操作结果时，应主动重新尝试而不是等待进一步指令
6. **不要仅依赖**：工具调用状态，应主动询问用户验证结果

### 4. 必须做的（基于成功经验）
1. **必须检查**：微信进程是否运行 (`tasklist | findstr -i wechat`)
2. **必须使用**：用户确认有效的激活方法（`Ctrl+Alt+W`快捷键）
3. **必须添加**：充分的等待时间（2-5秒每个步骤）
4. **必须询问并主动验证**：操作完成后询问用户是否收到消息，当用户质疑结果时应主动重新尝试
5. **必须记录**：成功的操作模式供后续参考
6. **必须主动检查**：当用户说"你没有发送成功"时，立即重新执行完整流程，而不是等待进一步指令

### 5. 环境特定的考虑
1. **Windows版本**：Windows 10 vs Windows 11可能有差异
2. **微信版本**：不同微信版本界面可能不同
3. **cua-driver版本**：不同版本对微信支持可能不同
4. **系统状态**：微信可能被其他窗口遮挡或最小化

### 6. 技能使用建议
1. **首次使用**：按照"首次使用指南"建立基线
2. **遇到问题**：参考"调试和验证策略"
3. **成功模式**：记录有效的方法和参数
4. **持续改进**：根据用户反馈更新技能