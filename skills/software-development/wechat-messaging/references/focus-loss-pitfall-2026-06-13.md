# 微信自动化焦点丢失问题深度分析（2026年6月13日）

## 问题发现（用户直接观察）

> **用户原话**："你没有进行搜索，你把 AI 数字人发送在 这个hermes Desktop的输入框"

这是一个极其重要的发现——用户观察到了工具返回"成功"但实际操作完全失败的本质。

## 根本原因分析

### 完整的错误流程

```
1. Hermes Agent 执行脚本，发送 Ctrl+Alt+W
2. 微信窗口弹出，短暂获得焦点
3. ❌ 关键：Hermes Desktop 立刻把焦点抢回去（因为脚本在 Hermes 上下文中执行）
4. 后续 Ctrl+F 发送到 Hermes 窗口（什么也不发生，或者触发 Hermes 的搜索）
5. 文本 "AI 数字人" 粘贴到 Hermes 的输入框
6. 回车发送也在 Hermes 中
7. cua-driver 返回 "ok: true"（按键发送成功）
8. ❌ 但微信自始至终没有收到任何键盘输入！
```

### 为什么这个问题如此隐蔽

1. **工具返回成功**：`keybd_event` API 不返回"目标窗口是否收到"，只返回"按键已发送到系统"
2. **微信窗口可见**：用户看到微信在前台，以为操作在微信内
3. **没有错误提示**：整个流程静默失败，没有任何报错
4. **只有用户能发现**：只有用户同时看得到微信和 Hermes 的输入框

## 验证方法

### 快速验证（执行后立即检查）

1. 操作完成后，立即看 Hermes Desktop 的输入框
2. 如果看到"AI 数字人"或搜索词，说明焦点丢失了
3. 检查微信搜索框是否为空——如果是，确认焦点丢失

### 日志验证（在脚本中添加）

```python
# 每次键盘操作前验证焦点
active_hwnd = user32.GetForegroundWindow()
active_title = get_window_title(active_hwnd)
print(f"当前前台窗口: {active_title}")

if "微信" not in active_title and "WeChat" not in active_title:
    print(f"⚠️  警告：焦点不在微信！当前在: {active_title}")
    # 强制重新激活
    force_activate_wechat()
```

## 解决方案：强制焦点锁定模式

### 核心原则

> **"宁可多做10次激活，也不要假设焦点正确"**

### 标准实现

```python
import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

def find_wechat_window():
    """枚举所有窗口，找到微信主窗口（按大小排序取最大）"""
    found_hwnds = []
    
    def enum_callback(hwnd, lParam):
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buffer = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buffer, length)
        title = buffer.value
        
        if title and ('微信' in title or 'WeChat' in title):
            if user32.IsWindowVisible(hwnd):
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                # 主窗口通常 > 300x400
                if width > 300 and height > 400:
                    found_hwnds.append((hwnd, title, width, height))
        return True
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    
    if found_hwnds:
        # 按窗口面积排序，最大的就是主窗口
        found_hwnds.sort(key=lambda x: x[2] * x[3], reverse=True)
        return found_hwnds[0][0]
    return None

def force_activate_window(hwnd):
    """强制激活，确保焦点在微信"""
    # 1. 最小化
    user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
    time.sleep(0.2)
    
    # 2. 恢复
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    time.sleep(0.3)
    
    # 3. 设为前台窗口
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    
    # 4. ✅ 必须验证！不验证就是耍流氓
    active_hwnd = user32.GetForegroundWindow()
    return active_hwnd == hwnd
```

### 必须执行强制激活的时机

| 操作前 | 是否必须激活 | 原因 |
|--------|-------------|------|
| `Ctrl+F` 搜索前 | ✅ 必须 | 最容易丢失焦点的地方 |
| 输入搜索词前 | ✅ 必须 | 用户已观察到文本跑到 Hermes |
| 回车选择前 | ✅ 必须 | 回车跑到 Hermes 就是换行 |
| Tab 移动焦点前 | ✅ 必须 | Tab 在 Hermes 中是切换控件 |
| 粘贴消息前 | ✅ 必须 | 绝对不能把消息粘贴到 Hermes |
| 回车发送前 | ✅ 必须 | 发送前最后一道防线 |

### 简化：每步前都激活

最简单最可靠的做法：**不要判断，每步前都强制激活一次**

```python
# 不要这样做（优化但容易出错）：
if focus_not_on_wechat():
    force_activate()

# 要这样做（简单可靠）：
force_activate_window(wechat_hwnd)  # 每步前必做
do_the_operation()
```

激活一次只需要 ~1 秒，相对于失败后重试的成本，完全值得。

## 经验教训

### 1. 工具成功 ≠ 操作成功

`keybd_event` 返回成功只意味着"按键已发送到系统消息队列"，不意味着"目标窗口收到并处理了这个按键"。

### 2. 隐式焦点是万恶之源

永远不要相信"上一步激活了，这一步焦点应该还在"。

- Windows 可能因为各种原因切换焦点
- Hermes 可能抢回焦点
- 其他应用弹窗可能抢焦点
- 用户可能不小心点了别的地方

### 3. 用户观察 > 所有日志

用户是最终验证者。如果用户说"没成功"，不管工具返回什么，都必须重新尝试。

### 4. 防御性编程

自动化脚本应该像防御性驾驶一样——假设其他人（其他窗口）都会犯错误，提前做好准备。

## 性能影响

| 操作 | 耗时 |
|------|------|
| 强制激活一次 | ~1.0 秒 |
| 6 步流程额外耗时 | ~6.0 秒 |

相对于失败后重新执行的时间（用户报告问题 → 重新理解 → 重新执行，至少 30 秒），这 6 秒完全值得。

## 相关脚本

- `scripts/wechat_focus_fixed.py` - 焦点修复的完整实现
- `scripts/wechat_final_test.py` - 经过用户环境验证的测试脚本
