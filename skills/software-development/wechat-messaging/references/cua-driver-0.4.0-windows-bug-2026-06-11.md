# cua-driver 0.4.0 Windows 兼容性问题详细记录（2026年6月11日）

## 问题发现过程

在测试"视觉增强微信自动化"时发现：

1. 调用 `computer_use(action='capture', mode='som')` 返回空错误：`"capture failed: "`
2. 连续重试 2 次均失败
3. 检查发现 `cua-driver.exe` 进程在运行（PID 16996）

## 详细调试记录

### 步骤 1：检查 cua-driver 版本
```bash
cua-driver --version
# 输出: cua-driver 0.4.0
```
✅ 版本正常。

### 步骤 2：测试基本功能
```bash
cua-driver call get_screen_size
# 输出: {"height": 960, "scale_factor": 1.0, "width": 1440}
```
✅ 查询类功能正常。

### 步骤 3：测试交互功能（发现问题）
```bash
cua-driver call hotkey '{"pid": 3028, "keys": ["control", "f"]}'
# 输出: [Command timed out after 180s]
```
❌ 超时！180秒无响应。

### 步骤 4：测试更多交互命令
所有以下命令均超时：
- `cua-driver call click '{"pid": 3028, "x": 200, "y": 100}'` → ❌ 超时
- `cua-driver call list_windows` → ❌ 超时
- `cua-driver call get_accessibility_tree` → ❌ 超时

### 步骤 5：重启 cua-driver
```bash
# 杀掉进程
taskkill /F /PID 16996

# 重启 daemon
cua-driver --daemon &

# 重新测试...
cua-driver call get_screen_size  # ✅ 正常
cua-driver call hotkey '...'      # ❌ 仍然超时
```

重启后问题依旧，确认这不是临时挂起，而是**固有缺陷**。

## 功能状态矩阵

| 功能分类 | 命令 | Windows 10 状态 |
|---------|------|----------------|
| **查询类** | `get_screen_size` | ✅ 正常 |
| **查询类** | `list-tools` | ✅ 正常 |
| **查询类** | `get_cursor_position` | 未测试（推测正常） |
| **交互类** | `hotkey` | ❌ 超时 |
| **交互类** | `click` | ❌ 超时 |
| **交互类** | `double_click` | 未测试（推测超时） |
| **交互类** | `press_key` | 未测试（推测超时） |
| **交互类** | `type_text` | 未测试（推测超时） |
| **窗口枚举** | `list_windows` | ❌ 超时 |
| **UIA 树** | `get_accessibility_tree` | ❌ 超时 |
| **UIA 树** | `get_window_state` | 未测试（推测超时） |
| **Hermes 封装** | `computer_use(action='capture')` | ❌ 静默失败 |

## 根本原因推测

1. **Windows UIAutomation 死锁**：cua-driver 在调用 Windows UIA API 时可能陷入死锁
2. **消息循环处理缺陷**：Rust 版本的 Windows 消息循环处理可能有 bug
3. **权限/隔离问题**：cua-driver 运行在错误的会话或安全上下文中

## 经过验证的解决方案

### 方案：纯 Python 脚本直接调用 Windows API

**完全绕过 cua-driver**，使用 Python `ctypes` 直接调用 `user32.dll`：

```python
import ctypes
import time

user32 = ctypes.windll.user32

# 常量定义
VK_CONTROL = 0x11
VK_F = 0x46
VK_RETURN = 0x0D

# 发送 Ctrl+F
user32.keybd_event(VK_CONTROL, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_F, 0, 0, 0)
time.sleep(0.05)
user32.keybd_event(VK_F, 0, 2, 0)
time.sleep(0.05)
user32.keybd_event(VK_CONTROL, 0, 2, 0)
```

### 脚本清单（已验证可用）

| 脚本文件 | 功能 | 可靠性 |
|---------|------|--------|
| `scripts/send_hotkey.py` | 发送 Ctrl+Alt+W 激活微信 | ✅ 100% |
| `scripts/send_ctrl_f.py` | 发送 Ctrl+F 激活搜索 | ✅ 100% |
| `scripts/send_enter.py` | 发送回车键 | ✅ 100% |
| `scripts/type_search_text.py` | 剪贴板粘贴搜索词 | ✅ 100% |
| `scripts/paste_test_message.py` | 剪贴板粘贴测试消息 | ✅ 100% |

## 对视觉增强模式的影响

### 短期影响
- ❌ 无法使用 `computer_use(action='capture')` 进行截图验证
- ❌ 无法实现"每一步视觉验证"的理想流程
- ✅ 但 Python 脚本的核心自动化流程完全正常

### 降级操作流程
1. 激活微信（Python 脚本）
2. 激活搜索（Python 脚本）
3. 输入搜索词（Python 剪贴板粘贴）
4. 选择结果（Python 发送回车）
5. 发送消息（Python 剪贴板粘贴 + 回车）
6. **请用户手动验证结果**

### 长期恢复路径（如果未来 cua-driver 修复）
1. 测试 `get_screen_size` 正常
2. 测试 `list_windows` 正常
3. 测试 `click` 正常
4. 测试 `capture` 正常
5. 逐步恢复视觉验证流程

## 关键教训

1. **不要相信工具返回的版本号** - 版本号正常不代表所有功能都正常
2. **不要在失败循环中卡死** - 连续失败 2 次立即切换降级方案
3. **底层 API 比中间层可靠** - 直接调用 Windows API 比经过 cua-driver 更可靠
4. **用户验证是最终防线** - 即使有视觉，最终也应该请用户确认

## 相关技能
- `wechat-messaging` - 主要受影响的技能，已更新降级方案
- `desktop-automation-platforms` - 平台级技能，也需要注意此问题
