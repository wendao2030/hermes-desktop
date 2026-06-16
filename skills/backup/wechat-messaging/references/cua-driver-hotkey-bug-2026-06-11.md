# cua-driver快捷键发送机制缺陷分析

## 问题发现时间
2026年6月11日，在微信消息发送任务中

## 问题现象
- 用户手动按`Ctrl+Alt+W`可以弹出微信窗口
- cua-driver执行`computer_use(action='key', keys='ctrl+alt+w')`返回成功，但微信未弹出
- 用户质疑："微信没有弹出来，是不是Ctrl+Alt+W没有被执行？"

## 根本原因分析

### 1. cua-driver日志分析
```json
{
  "ok": true,
  "action": "hotkey",
  "message": "✅ Pressed ctrl+option+w on pid 8820 via PostMessage (Win32 target)."
}
```

**关键发现**：快捷键被发送到pid 8820

### 2. 进程验证
```bash
# 检查pid 8820对应的进程
tasklist | findstr "8820"
# 输出：explorer.exe 8820 Console 1 268,132 K
```

**结论**：cua-driver将快捷键发送到了`explorer.exe`（Windows资源管理器），而不是微信进程

### 3. 技术原理缺陷
cua-driver使用`PostMessage` API发送快捷键，但：
1. **目标窗口选择错误**：可能选择了前台窗口或默认窗口
2. **全局快捷键处理不当**：`Ctrl+Alt+W`是应用级全局快捷键，应该发送到系统级
3. **进程匹配失败**：无法正确识别微信窗口句柄

## 对比分析：cua-driver vs 手动操作

| 特性 | cua-driver实现 | 手动操作 |
|------|----------------|----------|
| **API调用** | `PostMessage`到特定pid | 系统级键盘输入 |
| **目标选择** | 可能选择错误的前台窗口 | 系统全局处理 |
| **进程匹配** | 依赖窗口查找，可能失败 | 不依赖进程匹配 |
| **全局快捷键** | 可能无法正确处理 | 系统直接处理 |

## 解决方案对比

### 方案A：Python脚本绕过法（推荐）
```python
# 直接调用Windows API发送系统级键盘事件
ctypes.windll.user32.SendInput(...)
```

**优点**：
- 绕过cua-driver缺陷
- 系统级处理，与手动操作一致
- 不依赖进程匹配

**缺点**：
- 需要额外脚本
- 平台依赖（Windows）

### 方案B：进程目标验证
```python
# 执行前验证目标进程
import subprocess
result = subprocess.run(['tasklist', '|', 'findstr', '-i', 'WeChatAppEx.exe'], ...)
```

### 方案C：备用激活方法
1. **开始菜单启动**：`Win` → "微信" → `Enter`
2. **任务栏激活**：`Win+T` → 方向键选择
3. **命令行启动**：`start wechat:`

## 对技能设计的影响

### 1. 验证步骤强化
**必须添加**：
- 执行前：进程状态检查
- 执行中：目标进程验证
- 执行后：用户视觉确认

### 2. 备用方案准备
**必须准备**：
- 主要方案：cua-driver快捷键
- 备用方案1：Python脚本绕过
- 备用方案2：开始菜单启动
- 备用方案3：命令行启动

### 3. 用户沟通改进
**必须明确**：
- 告知用户可能的技术限制
- 提供替代方案选择
- 请求操作结果验证

## 长期建议

### 1. cua-driver改进建议
- 添加全局快捷键的特殊处理
- 改进窗口/进程匹配算法
- 添加执行结果验证机制

### 2. 技能设计原则
- **冗余设计**：重要操作准备多个实现方案
- **验证机制**：每个关键步骤都需要验证
- **透明沟通**：向用户说明技术限制和替代方案

## 相关文件
- `scripts/send_hotkey.py` - Python绕过脚本
- `SKILL.md` - 更新后的技能文档