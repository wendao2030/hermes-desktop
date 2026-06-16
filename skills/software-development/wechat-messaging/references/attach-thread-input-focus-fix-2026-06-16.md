# AttachThreadInput Focus Fix - 2026-06-16

## Root Cause

The `wechat_utils.py` and `wechat_window.py` scripts were calling `SetForegroundWindow()` without first attaching to the target window's thread. On Windows, this is a security restriction that causes silent failure.

## Symptoms

1. Script reports `Result: True` but nothing visibly happens
2. WeChat window opens but focus flashes and then disappears
3. `Ctrl+F` search never appears
4. `Ctrl+V` paste never works even though clipboard has content

## Two Key Fixes Applied

### Fix 1: `restore_and_focus()` in `wechat_window.py`

Before:
```python
user32.SetForegroundWindow(hwnd)
```

After:
```python
current_thread = kernel32.GetCurrentThreadId()
window_thread = user32.GetWindowThreadProcessId(hwnd, None)
if current_thread != window_thread:
    user32.AttachThreadInput(current_thread, window_thread, True)

user32.SetForegroundWindow(hwnd)

if current_thread != window_thread:
    user32.AttachThreadInput(current_thread, window_thread, False)
```

### Fix 2: Re-activate after chat window opens in `wechat_utils.py`

Added after opening chat window (after pressing Enter twice):
```python
# Re-activate after chat window opens - UI changes can lose focus
hwnd = window["hwnd"]
current_thread = kernel32.GetCurrentThreadId()
window_thread = user32.GetWindowThreadProcessId(hwnd, None)
if current_thread != window_thread:
    user32.AttachThreadInput(current_thread, window_thread, True)
user32.SetForegroundWindow(hwnd)
if current_thread != window_thread:
    user32.AttachThreadInput(current_thread, window_thread, False)
time.sleep(0.5)
```

## API Correction

- Wrong: `user32.GetCurrentThreadId()`
- Correct: `kernel32.GetCurrentThreadId()`

## Files Modified

- `scripts/wechat_window.py`: Added `kernel32` import, fixed `restore_and_focus()`
- `scripts/wechat_utils.py`: Added `kernel32` import, added re-activation after chat window opens

## Verification

After fixes, running:
```
python.exe -c "from wechat_utils import send_wechat_message; send_wechat_message('AI 数字人', 'test')"
```

Successfully:
1. Restores WeChat from tray
2. Opens search with `Ctrl+F`
3. Pastes contact name
4. Opens chat window
5. Retains focus through UI transition
6. Pastes and sends the message
