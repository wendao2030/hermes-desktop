# 步骤完整性验证 - 用户直接纠正记录

## 事件详情
- **日期**：2026年6月11日
- **用户纠正**："你没有执行ctrl+F激活搜索"
- **上下文**：微信消息发送测试
- **模型**：deepseek-v3-2-251201

## 问题分析

### 发生了什么
1. **代理操作**：尝试使用cua-driver发送`Ctrl+F`快捷键
2. **工具响应**：`computer_use(action='key', keys='ctrl+f')` 返回 `ok: true`
3. **实际效果**：快捷键未实际发送到微信窗口
4. **用户观察**：用户发现搜索功能未激活

### 根本原因
1. **cua-driver缺陷**：在Windows上发送快捷键到错误进程(`explorer.exe`)
2. **状态验证缺失**：依赖工具状态(`ok: true`)而非实际效果验证
3. **步骤完整性检查缺失**：未验证每个关键步骤的实际执行

### 技术细节
```json
// cua-driver返回（错误但显示成功）
{
  "ok": true,
  "action": "hotkey",
  "message": "✅ Pressed ctrl+f on pid 8788 via PostMessage (Win32 target)."
}
// 实际：发送到explorer.exe而非微信
```

## 解决方案实施

### 1. Python脚本绕过方案
创建了三个专用脚本：
- `send_hotkey.py` - 发送`Ctrl+Alt+W`激活微信
- `send_ctrl_f.py` - 发送`Ctrl+F`激活搜索  
- `send_enter.py` - 发送回车键选择/发送

### 2. 验证机制强化
**必须验证**：
1. 脚本执行成功（输出包含成功消息）
2. 用户视觉确认（窗口弹出/搜索框出现）
3. 步骤完整性检查清单

### 3. 操作流程修正
**旧流程**：
```
cua-driver发送快捷键 → 依赖工具状态 → 可能失败
```

**新流程**：
```
Python脚本发送快捷键 → 验证脚本输出 → 用户视觉确认 → 继续下一步
```

## 对技能设计的影响

### 1. 原则更新
- **Python脚本优先**：所有快捷键操作必须使用Python脚本
- **主动验证**：每个步骤后必须主动验证执行效果
- **用户纠正响应**：立即重新执行，不等待指令

### 2. 验证清单要求
必须维护和执行以下验证点：
- [ ] 微信窗口激活（用户确认）
- [ ] 搜索功能激活（`Ctrl+F`执行确认）
- [ ] 搜索词输入完成
- [ ] 搜索结果选择完成
- [ ] 消息输入完成
- [ ] 消息发送完成

### 3. 错误响应协议
当用户指出操作遗漏时：
1. **立即承认错误**："你说得对，我确实没有执行X步骤"
2. **立即重新执行**：从该步骤开始完整流程
3. **切换正确工具**：使用Python脚本而非cua-driver
4. **主动请求验证**：执行后主动询问用户确认

## 技术实现参考

### Python脚本位置
```
C:\Users\dtyao\AppData\Local\hermes\scripts\
├── send_hotkey.py    # Ctrl+Alt+W
├── send_ctrl_f.py    # Ctrl+F
└── send_enter.py     # Enter
```

### 执行命令
```bash
# 激活微信窗口
cd /c/Users/dtyao/AppData/Local/hermes/scripts && python send_hotkey.py

# 激活搜索功能
cd /c/Users/dtyao/AppData/Local/hermes/scripts && python send_ctrl_f.py

# 发送回车键
cd /c/Users/dtyao/AppData/Local/hermes/scripts && python send_enter.py
```

### 验证脚本输出
成功输出应包含：
```
正在发送Ctrl+F快捷键...
Ctrl+F快捷键发送完成！
请检查微信搜索框是否出现...
```

## 经验教训

### 1. 工具状态 ≠ 操作成功
即使所有工具调用返回`ok: true`，操作也可能失败。

### 2. 用户是最终验证者
用户观察比工具状态更可靠。

### 3. 步骤完整性必须主动验证
不能假设步骤执行成功，必须主动验证每个关键步骤。

### 4. 环境特定的解决方案
Windows上的cua-driver缺陷需要环境特定的解决方案。

## 后续改进建议

### 短期
1. 在技能中添加步骤完整性检查清单
2. 强化Python脚本优先原则
3. 添加操作日志模板

### 长期
1. 开发统一的快捷键发送工具
2. 添加自动化验证机制
3. 支持更多Windows应用场景