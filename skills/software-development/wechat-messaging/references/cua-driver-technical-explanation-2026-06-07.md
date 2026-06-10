# cua-driver 技术原理详解（基于2026年6月7日对话）

## 用户疑问澄清

### 用户的核心问题
1. **computer_use 是什么？** - Hermes Agent 内置工具，不是独立软件
2. **cua-driver 是什么？** - 需要安装的后端驱动，实现桌面控制
3. **两者关系？** - computer_use 调用 cua-driver 控制桌面
4. **别的智能体有没有？** - 只有 Hermes 有这个功能

## 技术架构详解

### 三层架构
```
1. Hermes Agent (computer_use 工具接口)
   ↓ 参数验证 + 结果转发
2. cua-driver (Rust 守护进程)
   ↓ 调用系统API
3. Windows 系统API层
   ↓ 硬件交互
4. 用户桌面
```

### cua-driver 核心代码原理（Windows实现）

#### 1. UI元素获取（不是截图OCR！）
```rust
// 使用 Windows UIAutomation API
let automation = CoCreateInstance::<IUIAutomation>()?;
let root_element = automation.GetRootElement()?;

// 遍历所有UI元素
let walker = automation.CreateTreeWalker(&condition)?;
let mut element = walker.GetFirstChildElement(&root_element)?;

while element.is_some() {
    // 直接获取系统属性（不是OCR识别）
    let name = element.GetCurrentPropertyValue(UIA_NamePropertyId)?; // 文本内容
    let bounds = element.GetCurrentPropertyValue(UIA_BoundingRectanglePropertyId)?; // 坐标
    let control_type = element.GetCurrentPropertyValue(UIA_ControlTypePropertyId)?; // 类型
    
    element = walker.GetNextSiblingElement(&element)?;
}
```

#### 2. 截图实现
```rust
// 模式A：vision/som（带图像）
let capture_item = GraphicsCaptureItem::CreateFromWindowId(window_id)?;
let session = capture_item.CreateCaptureSession()?;

// 模式B：ax（纯文本）
// 只调用 UIAutomation，返回 JSON 格式的 elements 数组
```

#### 3. 鼠标点击实现
```rust
// 使用 SendInput API
let inputs = [
    INPUT { /* 鼠标移动 */ },
    INPUT { /* 左键按下 */ },
    INPUT { /* 左键抬起 */ },
];
SendInput(3, &inputs, ...);
```

#### 4. 键盘输入实现
```rust
// 发送文本
for c in text.chars() {
    let vk = MapVirtualKeyW(c as u32, MAPVK_VK_TO_VSC);
    let key_down = INPUT { /* KEYDOWN */ };
    let key_up = INPUT { /* KEYUP */ };
    SendInput(2, &[key_down, key_up], ...);
}
```

## 关键区别：UIA vs OCR

### ❌ OCR方式（慢、不准）
1. 截图整个屏幕
2. 图片传给OCR
3. 识别文字
4. 猜测位置

### ✅ UIA方式（快、准）
1. 调用 `GetCurrentPropertyValue(UIA_NamePropertyId)`
2. **直接得到**系统提供的文本字符串
3. 获取精确的坐标位置

## 模型兼容性

### `mode='ax'` 模式（纯文本）
```json
{
  "elements": [
    {
      "index": 1,
      "role": "button",
      "name": "搜索",
      "bounds": [100, 200, 150, 230],
      "enabled": true
    }
  ]
}
```

**优势**：
- 不需要 vision 能力
- LLM 直接看 JSON 理解界面结构
- 适合 deepseek-v3-2-251201 等无视觉模型

## 微信的特殊限制

### 关键发现：微信没有完整 UIA 树
```json
# get_window_state 返回
{
  "element_count": 0,  // 没有子元素！
  "tree_markdown": "- Window \"微信\"",  // 只有窗口标题
}
```

### 影响
1. **无法使用**：`computer_use(action='click', element=14)`
2. **无法使用**：`computer_use(action='type', element=15, text='...')`
3. **只能依赖**：快捷键操作（Ctrl+Alt+W, Ctrl+F等）

## 验证机制

### 工具状态 vs 操作成功
- `ok: true` = 按键已发送到系统
- **不等于** = 微信已处理消息
- **需要用户最终验证** = 检查微信聊天记录

### 用户期望
1. **主动验证**：代理应该检查操作是否成功
2. **立即重新尝试**：用户质疑结果时立即重新执行
3. **完整流程**：确保每个步骤都执行到位

## 最佳实践总结

### 必须做的
1. **先 capture 建立活动窗口**
2. **使用用户确认的快捷键**（Ctrl+Alt+W）
3. **等待足够时间**（2-5秒每个步骤）
4. **询问用户验证结果**
5. **立即重新尝试失败的操作**

### 不要做的
1. **不要跳过**搜索步骤
2. **不要假设** `ok: true` = 操作成功
3. **不要等待**用户指令才重新尝试
4. **不要混淆**身份认知（我是Hermes Agent，不是小美）