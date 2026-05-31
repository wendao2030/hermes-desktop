# Windows QQ Control Implementation - 2026-05-31

## 成功验证的 Windows 10 cua-driver 支持

### 核心成就
- ✅ 成功在 Windows 10 上启用 `computer_use` 工具
- ✅ 修改 Hermes 代码移除 macOS 平台限制
- ✅ 安装 cua-driver Rust 版本 0.4.0
- ✅ 验证所有基础功能正常工作

### 代码修改详情

#### 1. 修改 `tools/computer_use/tool.py`
**位置**: 第 741-742 行
**原始代码**:
```python
if sys.platform != "darwin":
    return False
```
**修改后**: 移除或注释掉这两行

#### 2. 修改 `tools/computer_use/cua_backend.py`
**位置**: 第 355-356 行
**原始代码**:
```python
if sys.platform != "darwin":
    return False
```
**修改后**: 移除或注释掉这两行

### cua-driver 安装流程 (Windows)

#### 下载二进制文件
```bash
# 方法1: 使用 curl (如果可用)
curl -L -o cua-driver.zip https://github.com/trycua/cua/releases/download/cua-driver-rs-v0.4.0/cua-driver-rs-0.4.0-windows-x86_64-binary.zip

# 方法2: 使用 Python 脚本 (当 curl 不可用时)
python download_cua_driver.py
```

#### 安装到本地目录
```bash
# 创建安装目录
mkdir -p ~/.local/bin

# 解压文件
unzip cua-driver.zip -d ~/.local/bin/

# 验证安装
~/.local/bin/cua-driver.exe --version
# 应该输出: cua-driver 0.4.0
```

#### 添加到 PATH
```bash
# 临时添加到 PATH
export PATH="$HOME/.local/bin:$PATH"

# 永久添加到 PATH (Windows Git Bash)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 验证步骤

#### 1. 验证 cua-driver 安装
```bash
cua-driver --version
# 预期输出: cua-driver 0.4.0
```

#### 2. 验证 Hermes 代码修改
```python
import sys
sys.path.insert(0, r"C:\Users\dtyao\AppData\Local\hermes\hermes-agent")
from tools.computer_use_tool import check_computer_use_requirements
print(f"computer_use available: {check_computer_use_requirements()}")
# 预期输出: computer_use available: True
```

#### 3. 测试基本功能
```bash
# 获取屏幕尺寸
cua-driver get_screen_size
# 预期输出: {"width": 1440, "height": 960, "scale_factor": 1.0}

# 获取光标位置
cua-driver get_cursor_position
# 预期输出: {"x": 681, "y": 598}

# 列出窗口
cua-driver list_windows
# 应该返回窗口列表
```

### QQ 控制测试脚本

创建测试脚本 `test_qq_control.py`:

```python
#!/usr/bin/env python3
"""
QQ 控制功能测试
"""

import subprocess
import json

def run_cua_command(command):
    """运行 cua-driver 命令"""
    cmd = ["cua-driver"] + command
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    if result.returncode == 0 and result.stdout:
        try:
            return json.loads(result.stdout)
        except:
            return result.stdout.strip()
    return None

# 1. 查找 QQ 窗口
windows = run_cua_command(["list_windows"])
qq_windows = []

if windows and "_legacy_windows" in windows:
    for window in windows["_legacy_windows"]:
        title = window.get("title", "").lower()
        if "qq" in title or "腾讯" in title:
            qq_windows.append(window)

if qq_windows:
    print(f"找到 {len(qq_windows)} 个 QQ 窗口")
    
    # 2. 获取第一个 QQ 窗口的截图
    first_window = qq_windows[0]
    screenshot = run_cua_command([
        "get_window_state",
        "--pid", str(first_window["pid"]),
        "--window-id", str(first_window["window_id"])
    ])
    
    if screenshot and "screenshot" in screenshot:
        print("✅ 成功获取 QQ 窗口截图")
        
        # 3. 控制演示
        # 移动光标到窗口中心
        x = first_window["x"] + first_window["width"] // 2
        y = first_window["y"] + first_window["height"] // 2
        
        run_cua_command(["move_cursor", "--x", str(x), "--y", str(y)])
        run_cua_command(["click", "--x", str(x), "--y", str(y), "--button", "left"])
        run_cua_command(["type_text", "--text", "Hello from automated QQ control!"])
        
        print("✅ QQ 控制演示完成")
else:
    print("❌ 没有找到 QQ 窗口")
    print("请确保 QQ 已经打开")
```

### 常见问题解决

#### 问题1: "cua-driver not found"
**解决方案**:
```bash
# 检查文件是否存在
ls -la ~/.local/bin/cua-driver.exe

# 如果不存在，重新安装
# 如果存在但不在 PATH，添加完整路径
~/.local/bin/cua-driver.exe --version
```

#### 问题2: 代码修改后仍然显示 "computer_use is macOS only"
**解决方案**:
1. 确保修改了正确的文件
2. 重启 Hermes 会话
3. 验证修改:
```python
# 在 Python 中检查修改
import sys
sys.path.insert(0, r"C:\Users\dtyao\AppData\Local\hermes\hermes-agent")
exec(open("tools/computer_use/tool.py").read())
# 检查 check_computer_use_requirements 函数
```

#### 问题3: QQ 窗口找不到
**解决方案**:
1. 确保 QQ 已经打开并可见
2. 检查窗口标题:
```bash
cua-driver list_windows | grep -i "qq\|腾讯"
```
3. QQ 可能以托盘图标运行，尝试:
   - 双击托盘图标打开主窗口
   - 使用快捷键 Ctrl+Alt+Z 打开 QQ

### 成功验证的功能

1. **基础控制**:
   - 移动光标 ✓
   - 点击操作 ✓
   - 键盘输入 ✓
   - 获取截图 ✓

2. **系统信息**:
   - 屏幕分辨率 ✓
   - 光标位置 ✓
   - 窗口列表 ✓
   - 应用程序列表 ✓

3. **QQ 特定功能**:
   - 查找 QQ 窗口 ✓
   - 获取 QQ 窗口截图 ✓
   - 控制 QQ 窗口 ✓ (需要 QQ 已打开)

### 结论

cua-driver 在 Windows 10 上完全可用，`computer_use` 工具集可以通过简单的代码修改启用。这为 Windows 上的桌面自动化提供了完整支持，包括 QQ 等应用程序的控制。

**关键要点**:
- 修改两个文件中的平台检查
- 安装 cua-driver Rust 版本
- 验证所有基础功能
- 针对特定应用程序编写控制脚本