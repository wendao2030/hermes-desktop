# 微信中文输入调试记录（2026-06-11）

## 关键结论

在Windows微信自动化中，**中文联系人搜索必须使用剪贴板粘贴法**，不能使用逐字键盘模拟或cua-driver type。

## 发现过程

### 初始误判
- 代理以为成功搜索了"AI 数字人"
- 用户后来指出：实际只输入了"AI"，巧合第一个搜索结果就是"AI 数字人"
- 这说明英文输入成功，但中文部分没有输入

### 用户关键纠正
> "我懂了，你不会搜汉字 黄老师 上次让你搜 AI 数字人， 你只搜索了 AI 巧了第一个搜索结果就是AI 数字人"

### 错误证据
1. 搜索"黄老师"时未能输入中文
2. 搜索框中出现"Hermesagent"而非目标联系人
3. `VkKeyScanW`逐字输入对中文无效
4. 空格也可能丢失："Hermes Agent" → "Hermesagent"

## 技术原因

### `VkKeyScanW`限制
- `VkKeyScanW(ord(char))`适用于ASCII字符
- 对中文汉字返回值不可靠
- 无法模拟中文输入法选字过程

### cua-driver type限制
- Windows上对微信使用PostMessage输入不可靠
- 返回`ok: true`不代表文本实际进入搜索框
- 微信输入框不暴露完整UIA树，无法精确定位输入目标

### 焦点问题
- 如果让用户手动打开搜索框，再运行终端脚本，焦点会从微信转移到终端
- 必须在同一个脚本中连续完成：激活窗口 → 搜索 → 粘贴 → 选择 → 粘贴消息 → 发送

## 正确方案：剪贴板粘贴

```python
import ctypes
import time
import pyperclip

user32 = ctypes.windll.user32
VK_CONTROL = 0x11
VK_F = 0x46
VK_V = 0x56
VK_RETURN = 0x0D
VK_BACK = 0x08

def press_key(vk):
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(vk, 0, 2, 0)

def hotkey(*keys):
    for vk in keys:
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.05)
    for vk in reversed(keys):
        user32.keybd_event(vk, 0, 2, 0)
        time.sleep(0.05)

def paste_text(text):
    pyperclip.copy(text)
    time.sleep(0.5)
    hotkey(VK_CONTROL, VK_V)
    time.sleep(1)

def send_wechat_message(contact, message):
    # 1. 激活微信
    hwnd = user32.FindWindowW(None, "微信")
    if not hwnd:
        raise RuntimeError("未找到微信窗口")
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(2)

    # 2. 打开搜索
    hotkey(VK_CONTROL, VK_F)
    time.sleep(2)

    # 3. 清空可能残留的搜索文本
    for _ in range(20):
        press_key(VK_BACK)
        time.sleep(0.03)

    # 4. 粘贴中文联系人名
    paste_text(contact)
    time.sleep(3)

    # 5. 选择第一个搜索结果
    press_key(VK_RETURN)
    time.sleep(3)

    # 6. 粘贴中文消息
    paste_text(message)
    time.sleep(1)

    # 7. 发送
    press_key(VK_RETURN)
    time.sleep(1)
```

## 操作纪律

1. **搜索中文联系人时，永远使用剪贴板粘贴法**
2. **不要声称成功，直到用户确认看到正确联系人或消息**
3. **用户指出搜索框内容不对时，先承认并重新执行，不要解释已成功**
4. **不要把英文输入成功误判为中文输入成功**
5. **搜索"AI 数字人"这类中英混合名时，必须验证完整文本是否输入，而不是只看英文部分**

## 验证点

完成后必须询问用户：
- 搜索框是否显示完整联系人名（包括汉字）？
- 是否进入了正确联系人聊天？
- 消息内容是否正确显示？
- 对方是否收到消息？

## 反例：不要这样做

```python
# 错误：逐字输入中文
for char in "黄老师":
    vk_code = user32.VkKeyScanW(ord(char))
    user32.keybd_event(vk_code & 0xFF, ...)

# 错误：cua-driver type输入中文
computer_use(action='type', text='黄老师')

# 错误：让用户手动打开搜索框后再运行脚本
# 因为运行终端命令会让微信失去焦点
```

## 成功案例

使用`chinese_clipboard.py`成功执行：
1. 激活微信窗口
2. Ctrl+F打开搜索
3. 剪贴板粘贴"黄老师"
4. 回车选择结果
5. 剪贴板粘贴中文测试消息
6. 回车发送

用户尚需视觉确认最终发送目标和内容。