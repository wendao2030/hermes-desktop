---
name: photoshop
description: Adobe Photoshop 自动化——修图、调色、图层处理、批量导出（Win/Mac 双平台）
platforms: [win32, darwin]
---

# Photoshop 自动化

> **本技能用于在 Photoshop 中逐层绘制、编辑、排版。不要用 `image_generate` 替代**——那是 AI 生图接口，不经过 PS。用户说"用 PS 做图/设计/排版"时必须走 PS，不要绕路。

> Mac 优先用 `computer_use` 直接看屏幕操作。脚本方式作为后台批量处理的备选。

需要写脚本文件时，放到 `skills/photoshop/scripts/` 下以便复用，不要写到工作目录。

## 路由规则

- 用户说“用 PS / Photoshop 做图、修图、设计、排版”时，必须操作 Photoshop，不要改用 `image_generate`、即梦、豆包生图或其他图片生成 API。
- 用户说“演示 / 看过程 / 一步步 / 让我看到操作 / 操作界面 / 展示 PS 过程”时，必须使用**可见步骤模式**：
  - Photoshop 必须 `Visible = True`、`DisplayDialogs = 3`，并尽量置前。
  - 不要把整张图一次性后台生成完。应拆成多个步骤执行，每步之间暂停 0.8-2 秒，让用户能看到画布、图层或对象逐步出现。
  - 每一步要在 Photoshop 里产生可见变化，例如：新建画布 -> 填背景 -> 画主体形状 -> 加文字 -> 调整图层 -> 保存。
  - 最终回复只能在确认输出文件真实存在后再说“完成”。
  - 有现成预设时，必须优先运行 `skills/photoshop/scripts/run_photoshop_demo.bat`，不要临时重写整套 PS 连接代码。
  - 已有预设覆盖：停车标识 `parking`、红心 `heart`、卡通老鼠 `cartoon_mouse`、游戏手柄 `gamepad`。
  - 演示开始前必须无提示关闭旧的未保存文档，避免 Photoshop 弹出“是否保存更改”导致脚本卡死。
- Windows 上运行 Photoshop 自动化脚本必须使用 `hermes-agent\venv\Scripts\python.exe`，因为 `runtime\python311\python.exe` 只提供基础 Python，不包含 `pythoncom/win32com`。
- 推荐直接运行 `skills/photoshop/scripts/run_photoshop_demo.bat`，它会自动使用正确的 venv Python。
- 用户没有要求演示，只是要结果时，可以使用批量/后台模式提高稳定性和速度。

## 关键坑

- **干活用 `DoJavaScript`**：一次 COM 调用把整段 JS 扔给 PS，稳定快速。但后台静默跑，界面上看不到变化
- **演示用可见步骤模式**：可以仍然用 `DoJavaScript`，但必须拆成多个小步骤分别调用，并在每步后 `BringToFront` + 暂停，让 PS 窗口显示变化。不要一次性把整段 JS 跑完。
- **直接 COM 调用**：适合少量界面动作；复杂绘图仍建议用“多个小段 JSX + 暂停”的可见步骤模式。可能被消息过滤器卡，需要 `Visible = True` + `DisplayDialogs = 3`
- 方法名是 `DoJavaScript`，不是 `DoScript` 或 `ExecuteJS`
- PS COM 必须 `Visible = True`，否则调用超时。Mac 上无此问题
- PS COM 默认单位是**厘米**，必须设 `RulerUnits = 1`（像素）
- `SaveAs` 必须传格式对象，缺了就弹窗。保存前先删旧文件避免覆盖确认弹窗

## Windows 初始化

```python
import pythoncom, win32com.client, time
pythoncom.CoInitialize()

for i in range(30):
    try:
        ps = win32com.client.Dispatch("Photoshop.Application")
        break
    except:
        time.sleep(2)

ps.Visible = True
ps.DisplayDialogs = 3
ps.Preferences.RulerUnits = 1  # 像素
```

## Mac 初始化

```python
import subprocess, tempfile, os

def ps_jsx(code):
    tmp = os.path.join(tempfile.gettempdir(), "_ps_temp.jsx")
    with open(tmp, "w") as f:
        f.write(code)
    subprocess.run(["osascript", "-e",
        f'tell application "Adobe Photoshop" to do javascript file "{tmp}"'], check=True)
    os.remove(tmp)
```

## 操作方式

三种方式，按场景选用。都是 ExtendScript 语法，Win/Mac 通用。

```python
# 方式 1：DoJavaScript（Windows 首选）
ps.DoJavaScript(js_code, [])

# 方式 2：演示模式，拆成多个可见步骤
import importlib.util, os
from pathlib import Path

helper = Path(os.environ["HERMES_HOME"]) / "skills" / "photoshop" / "scripts" / "photoshop_visible_runner.py"
spec = importlib.util.spec_from_file_location("photoshop_visible_runner", helper)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

connect_photoshop = runner.connect_photoshop
run_visible_steps = runner.run_visible_steps

ps = connect_photoshop()
run_visible_steps(ps, [
    ("新建画布", "var doc = app.documents.add(900, 600, 72, 'demo');"),
    ("填背景", "/* 创建背景图层并填色 */"),
    ("绘制主体", "/* 创建主体形状 */"),
    ("添加文字", "/* 创建文字图层 */"),
], delay=1.2)

# 常用演示预设，优先使用固定入口，确保走带 pywin32 的 venv Python：
# "%HERMES_HOME%\skills\photoshop\scripts\run_photoshop_demo.bat" --preset parking --output "%USERPROFILE%\Desktop\停车标识.jpg" --delay 1.2
# "%HERMES_HOME%\skills\photoshop\scripts\run_photoshop_demo.bat" --preset heart --output "%USERPROFILE%\Desktop\红心图.jpg" --delay 1.2
# "%HERMES_HOME%\skills\photoshop\scripts\run_photoshop_demo.bat" --preset cartoon_mouse --output "%USERPROFILE%\Desktop\卡通老鼠.jpg" --delay 1.2
# "%HERMES_HOME%\skills\photoshop\scripts\run_photoshop_demo.bat" --preset gamepad --output "%USERPROFILE%\Desktop\游戏手柄.jpg" --delay 1.2

# 方式 3：Mac 用 ps_jsx()
ps_jsx(js_code)
```

## 保存

**用户没指定格式时一律存 PSD**（保留图层，方便后续编辑）。

```javascript
// PSD（默认首选，不传格式对象，确保路径以 .psd 结尾）
doc.saveAs(File(path + ".psd"));

// JPEG（用户明确要求时）quality: 1-12
var opt = new JPEGSaveOptions(); opt.quality = 12;
doc.saveAs(File(path), opt, true);

// PNG（用户明确要求时）compression: 0-9
var opt = new PNGSaveOptions(); opt.compression = 6;
doc.saveAs(File(path), opt, true);
```

## 关闭

```python
ps.DoJavaScript("doc.close(SaveOptions.DONOTSAVECHANGES);")  # 不保存关闭
ps.DoJavaScript("doc.close(SaveOptions.SAVECHANGES);")        # 保存后关闭
ps.DoJavaScript("app.quit();")                                # 退出
```
