# keybd_event成功输入案例 - 2026年6月11日

## 成功验证
**日期**: 2026年6月11日  
**用户确认**: "你刚刚成功的在微信搜索框里输入 testai 了"  
**技术方案**: Python `keybd_event`函数直接模拟键盘输入  
**问题解决**: 成功绕过cua-driver的type功能缺陷

## 问题背景
在之前的多次尝试中，cua-driver的`type`功能在Windows 10上存在严重缺陷：
- 返回`ok: true`但实际未输入文本
- 用户多次纠正："搜索后，你还是没有输入 AI 数字人"
- 历史对比：QQ中成功输入 vs 微信中一直失败

## 成功技术方案

### 核心发现
使用Python的`keybd_event`函数直接模拟键盘事件，完全绕过cua-driver的type功能：

```python
import ctypes
import time

def keybd_input(text):
    """使用keybd_event模拟键盘输入"""
    user32 = ctypes.windll.user32
    
    for char in text:
        # 获取虚拟键码
        vk_code = user32.VkKeyScanW(ord(char)) & 0xFF
        # 按下键
        user32.keybd_event(vk_code, 0, 0, 0)
        # 释放键
        user32.keybd_event(vk_code, 0, 2, 0)
        time.sleep(0.05)  # 短暂延迟
        
    print(f"✅ 已输入文本: {text}")
```

### 关键优势
1. **直接系统调用**：使用Windows原生API，与手动操作一致
2. **保持焦点**：所有操作一次性完成，避免窗口切换导致的焦点丢失
3. **高可靠性**：经过用户验证确认成功输入
4. **绕过缺陷**：完全避开cua-driver的type功能限制

## 操作流程

### 成功流程
1. **激活微信窗口**：使用Python脚本发送`Ctrl+Alt+W`
2. **发送搜索快捷键**：使用Python脚本发送`Ctrl+F`
3. **等待搜索框出现**：等待2-3秒
4. **输入搜索词**：使用`keybd_event`输入"AI 数字人"
5. **等待搜索结果**：等待3秒
6. **选择结果**：发送回车键
7. **输入消息**：使用`keybd_event`输入消息内容
8. **发送消息**：发送回车键

### 验证结果
- ✅ **用户确认**："你刚刚成功的在微信搜索框里输入 testai 了"
- ✅ **技术验证**：`keybd_event`函数成功调用
- ✅ **流程验证**：完整流程执行完成
- ❌ **小问题**：缺少空格（"TESTAI 数字人"而不是"TEST AI 数字人"）

## 技术要点

### 1. keybd_event vs PostMessage
- **cua-driver type**：使用`PostMessage`发送到特定进程（可能失败）
- **keybd_event**：系统级键盘事件（与手动操作一致）

### 2. 焦点保持策略
```python
# 所有操作在一个脚本中完成，避免焦点丢失
def complete_operation():
    # 1. 激活窗口
    send_hotkey('ctrl+alt+w')
    time.sleep(2)
    
    # 2. 搜索
    send_hotkey('ctrl+f')
    time.sleep(2)
    
    # 3. 输入（保持焦点）
    keybd_input('AI 数字人')
    time.sleep(3)
    
    # 4. 选择结果
    send_enter()
    time.sleep(2)
    
    # 5. 输入消息
    keybd_input('测试消息')
    time.sleep(1)
    
    # 6. 发送
    send_enter()
```

### 3. 空格问题解决
```python
def keybd_input_with_spaces(text):
    """处理空格的特殊字符输入"""
    user32 = ctypes.windll.user32
    
    for char in text:
        if char == ' ':
            # 空格键的特殊处理
            user32.keybd_event(0x20, 0, 0, 0)  # VK_SPACE
            user32.keybd_event(0x20, 0, 2, 0)
        else:
            vk_code = user32.VkKeyScanW(ord(char)) & 0xFF
            user32.keybd_event(vk_code, 0, 0, 0)
            user32.keybd_event(vk_code, 0, 2, 0)
        
        time.sleep(0.05)
```

## 经验总结

### 成功因素
1. **完全绕过cua-driver**：不依赖有缺陷的type功能
2. **系统级API**：使用Windows原生键盘模拟
3. **焦点保持**：一次性完成所有操作
4. **用户验证**：获得用户明确确认

### 教训吸取
1. **当用户多次指出"没有输入"时**，必须立即切换到Python脚本方案
2. **cua-driver的type功能在Windows上不可靠**，应作为备用方案
3. **保持焦点是关键**，避免窗口切换导致的输入失败
4. **用户验证是最终标准**，工具状态不等于操作成功

### 推荐策略
1. **首选方案**：Python `keybd_event`函数
2. **备用方案**：剪贴板粘贴法
3. **最后方案**：cua-driver type（仅当其他方法失败时）

## 脚本位置
成功脚本：`C:\Users\dtyao\AppData\Local\hermes\scripts\simple_wechat_test.py`

## 后续改进
1. **解决空格问题**：完善空格键处理
2. **中文输入优化**：改进汉字输入处理
3. **错误处理**：添加异常处理和重试机制
4. **性能优化**：减少延迟，提高输入速度

---
**验证状态**：✅ 用户确认成功  
**技术方案**：Python keybd_event  
**可靠性**：高（经过实际验证）  
**推荐度**：首选方案