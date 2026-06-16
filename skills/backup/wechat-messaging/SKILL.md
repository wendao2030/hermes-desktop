---
name: wechat-messaging
title: WeChat messaging automation
description: Use verified local Windows scripts to restore WeChat and send messages to a named contact.
tags: [wechat, windows, desktop-automation]
trigger: Use this skill when the user asks Hermes to operate WeChat, open WeChat, search a WeChat contact, or send a WeChat message.
---

# WeChat Messaging Automation

## Hard Rules

1. Use the scripts in this skill folder. If a WeChat helper or debug script is needed, create or edit it only under this skill's `scripts` directory. Do not create temporary scripts on the desktop, project root, global scripts folder, or tools folder.
2. Always run a real tool before claiming that WeChat was opened, searched, clicked, or messaged.
3. Never say a message was sent unless a script actually ran and the user can verify the visible result.
4. Do not treat an Explorer folder/window named `wechat-messaging` as WeChat.
5. A trusted WeChat window must be owned by `Weixin.exe`, `WeChat.exe`, or `WeChatAppEx.exe`.
6. If the user says the visible UI did not change, trust the user and debug the scripts instead of arguing from `success=True`.

## Scripts

Folder:

`C:\Users\dtyao\AppData\Local\hermes\skills\software-development\wechat-messaging\scripts`

Use Hermes Python:

`C:\Users\dtyao\AppData\Local\hermes\venv\Scripts\python.exe`

Current scripts:

- `verify_wechat_window.py`: verify and restore the real WeChat window.
- `wechat_window.py`: strict window detection, foreground activation, and input-area clicking.
- `wechat_utils.py`: contact search and message sending helpers.
- `send_message.py`: the only recommended command-line entrypoint for sending a message.

## Verified Flow

1. Run `verify_wechat_window.py`.
2. If it prints `RESTORE_OK=True`, use `send_message.py`.
3. The send flow is:
   - restore real WeChat window
   - send `Ctrl+F`
   - paste contact name
   - press Enter twice to open the first result
   - click the lower-right message input area directly
   - paste message
   - press Enter

Important: do not rely on `Tab` to reach the input box. WeChat focus order changes and causes lost-focus failures. Use `click_wechat_input_box()` from `wechat_window.py`.

## Critical Windows API Pitfall

`SetForegroundWindow` can silently fail without `AttachThreadInput`.

Windows has a security restriction: a process cannot reliably set another process's window to foreground unless it attaches its thread to the target window's thread first. The sequence must be:

```python
current_thread = kernel32.GetCurrentThreadId()
window_thread = user32.GetWindowThreadProcessId(hwnd, None)
if current_thread != window_thread:
    user32.AttachThreadInput(current_thread, window_thread, True)

user32.SetForegroundWindow(hwnd)

if current_thread != window_thread:
    user32.AttachThreadInput(current_thread, window_thread, False)
```

Always re-activate after the chat window opens.

When Enter opens a chat window, WeChat's UI transitions and often loses focus. Call the `AttachThreadInput + SetForegroundWindow` sequence again after the chat window opens and before sending messages.

API correction: `GetCurrentThreadId()` is in `kernel32.dll`, not `user32.dll`.

## Example Command

```powershell
$env:HERMES_WECHAT_CONTACT='AI 数字人'
$env:HERMES_WECHAT_MESSAGE='技能脚本测试消息'
C:\Users\dtyao\AppData\Local\hermes\venv\Scripts\python.exe C:\Users\dtyao\AppData\Local\hermes\skills\software-development\wechat-messaging\scripts\send_message.py
```

Avoid `python -c "...中文..."` for WeChat messages. Some Windows shells or model-generated commands can turn Chinese into question-mark mojibake. Prefer `send_message.py` with environment variables.

After running, ask the user whether the target chat received the message.

## Change Log

- 2026-06-16: Fixed critical foreground activation bug: added `AttachThreadInput` to both `restore_and_focus()` and `send_wechat_message()` because Windows `SetForegroundWindow` silently fails without thread attachment; re-activate WeChat after chat window opens; corrected API: `GetCurrentThreadId()` is `kernel32`, not `user32`.
- 2026-06-16: Cleaned corrupted content, removed temporary-script guidance, enforced strict process-based WeChat detection, replaced Tab-based input focusing with direct input-area click, and added `send_message.py` to avoid Chinese command-line encoding loss.
