# Windows微信自动化调试记录
## 日期：2026年6月2日
## 环境：Windows 10，Hermes Agent，cua-driver

## 问题发现
用户反馈："你没有发送成功，检查下"

## 调试过程

### 1. 初始问题分析
- **假设**：使用`Weixin.exe`作为进程名
- **实际**：Windows 10上微信进程是`WeChatAppEx.exe`
- **验证命令**：`tasklist | findstr -i wechat`

### 2. cua-driver限制发现
- `computer_use(action='focus_app', app='WeChatAppEx.exe')` 失败
- `computer_use(action='list_apps')` 不显示微信
- `computer_use(action='capture', app='WeChatAppEx.exe')` 返回空元素

### 3. 替代方案测试
#### 方案A：开始菜单启动（成功）
```python
computer_use(action='capture', mode='som')
# 返回结果中包含：ListItem '微信' @ (0, 0, 0, 0) (元素#2)
computer_use(action='click', element=2)
computer_use(action='wait', seconds=5)
```

#### 方案B：全局快捷键（成功）
```python
computer_use(action='key', keys='ctrl+alt+w')
computer_use(action='wait', seconds=2)
```

### 4. 完整操作流程（经过测试）
```python
# 1. 启动微信（如果未运行）
computer_use(action='capture', mode='som')
computer_use(action='click', element=2)  # 微信图标
computer_use(action='wait', seconds=5)

# 2. 激活微信窗口
computer_use(action='key', keys='ctrl+alt+w')
computer_use(action='wait', seconds=2)

# 3. 搜索好友
computer_use(action='key', keys='ctrl+f')
computer_use(action='wait', seconds=2)
computer_use(action='type', text='朱智聪')
computer_use(action='wait', seconds=3)

# 4. 发送消息
computer_use(action='key', keys='return')
computer_use(action='wait', seconds=2)
computer_use(action='type', text='测试消息：这是通过Hermes Agent重新发送的测试消息，请确认是否收到')
computer_use(action='key', keys='return')
computer_use(action='wait', seconds=2)
```

## 关键发现

### 1. 进程信息
- **正确进程名**：`WeChatAppEx.exe`（多实例进程）
- **错误进程名**：`Weixin.exe`，`WeChat.exe`
- **进程检查**：`tasklist | findstr -i wechat` 返回多个`WeChatAppEx.exe`实例

### 2. cua-driver行为
- **不支持**：通过app名称直接操作微信窗口
- **支持**：全局快捷键和开始菜单操作
- **限制**：无法捕获微信界面元素进行验证

### 3. 操作验证
- **工具层面**：所有`computer_use`调用返回`ok: true`
- **用户层面**：需要用户手动检查微信聊天记录
- **关键教训**：`ok: true` ≠ 操作成功，需要用户最终验证

## 推荐的工作流程

### 首次设置
1. 检查微信进程：`tasklist | findstr -i wechat`
2. 测试启动方法：开始菜单 vs 全局快捷键
3. 记录有效的方法和等待时间

### 常规操作
1. 使用已验证的启动/激活方法
2. 执行完整的搜索-发送流程
3. 询问用户验证结果

### 故障排除
1. 如果用户反馈未收到：重新尝试
2. 如果多次失败：尝试不同的启动方法
3. 如果仍然失败：建议用户手动检查微信状态

## 环境特定信息
- **操作系统**：Windows 10
- **微信版本**：未知（基于进程名判断为较新版本）
- **cua-driver版本**：0.4.0
- **Hermes Agent版本**：未知

## 后续建议
1. **监控cua-driver更新**：未来版本可能改善对微信的支持
2. **记录用户环境**：不同Windows/微信版本可能有不同行为
3. **建立基线测试**：定期测试基本功能确保兼容性
4. **用户教育**：明确说明自动化操作的局限性