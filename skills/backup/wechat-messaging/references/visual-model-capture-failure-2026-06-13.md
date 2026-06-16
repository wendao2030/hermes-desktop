# 视觉模型 Capture 静默失败问题（2026年6月13日）

## 问题现象

使用支持视觉的模型（如 doubao-seed-2-0-pro-260215）时，调用 `computer_use(action='capture', mode='som')` 返回空错误：

```json
{"error": "capture failed: "}
```

## 关键特征

1. **没有具体错误信息**：只有空的 `capture failed`，没有原因说明
2. **连续调用重复失败**：重试会触发 `tool loop warning`
3. **与模型无关**：即使声明支持视觉的模型也会失败
4. **不是 Hermes 的问题**：这是 cua-driver 的 Windows 兼容性问题
5. **其他操作可能正常**：`key`、`wait` 等操作可能仍然可用

## 根本原因

这是 **cua-driver 0.4.0 Rust 版本在 Windows 平台的已知兼容性缺陷**，与 Windows UIAutomation 交互或消息循环处理有关。与模型是否支持视觉无关。

## 应对策略（必须严格执行）

### 1. 第一次失败立即降级
```python
# 尝试视觉模式
try:
    capture = computer_use(action='capture', mode='som')
    # 如果成功，继续视觉增强流程
except Exception:
    # ❌ Capture 失败，立即降级，不要重试！
    print("⚠️  视觉捕获暂时不可用，切换到纯脚本模式")
    
    # 继续用 Python 脚本完成所有操作
    # ...
```

### 2. 降级后的完整操作流程
所有操作使用纯 Python 脚本，不依赖 cua-driver 的任何视觉功能：

| 操作 | 降级方案 | 脚本 |
|------|----------|------|
| 激活微信 | Python 发送 Ctrl+Alt+W | `send_hotkey.py` |
| 激活搜索 | Python 发送 Ctrl+F | `send_ctrl_f.py` |
| 输入搜索词 | 剪贴板粘贴 | `keyboard_simulator.py paste` |
| 选择结果 | Python 发送两次回车 | `send_enter.py` |
| 聚焦输入框 | Python 发送 3 次 Tab | `keyboard_simulator.py tab` |
| 输入消息 | 剪贴板粘贴 | `paste_test_message.py` |
| 发送消息 | Python 发送回车 | `send_enter.py` |

### 3. 绝对不要做的
- ❌ 连续 2 次以上尝试 capture
- ❌ 反复截图验证（浪费 token 且无效）
- ❌ 使用 cua-driver 的 click 功能（会超时 180 秒）
- ❌ 告诉用户"你的模型不支持视觉"（这不是模型的问题）

### 4. 用户沟通
向用户透明说明：
> "当前 cua-driver 在 Windows 上暂时有视觉捕获的兼容性问题，我已切换到经过验证的纯脚本方案继续操作。这个问题修复后，我们就能使用视觉自验证功能了。"

## 临时解决方案

目前没有针对 cua-driver 本身的修复，但可以：
1. 降级使用纯 Python 脚本方案（已验证可靠）
2. 等待 cua-driver 未来版本修复 Windows 兼容性
3. 用户手动验证最终结果（当前替代方案）

## 相关参考文件
- `cua-driver-0.4.0-windows-bug-2026-06-11.md` - 底层功能缺陷分析
- `keyboard_simulator.py` - 统一的键盘输入模拟器脚本

## 历史追踪
- 2026-06-11：首次发现 cua-driver 在 Windows 上的快捷键发送缺陷
- 2026-06-13：首次发现视觉模型下 capture 仍然失败，确认是驱动层问题
