---
name: wechat-messaging
title: WeChat messaging automation
description: 微信发消息/监控必须先加载本技能，并运行固定脚本验证结果。
tags: [wechat, windows, desktop-automation]
trigger: Use this skill when the user asks Hermes to operate 微信/WeChat, open WeChat, search a WeChat contact, monitor unread WeChat messages, or send a WeChat message.
---

# WeChat Messaging Automation

## Golden Rule

This skill is an execution skill, not a brainstorming skill. It is frozen and maintainer-only during normal use. When the user asks to operate WeChat, Hermes must run the existing scripts and report only what the scripts prove.

Hermes must not create new scripts, edit scripts, edit this skill file, rewrite workflows, or invent a new WeChat automation approach during normal use. If the existing scripts cannot complete the user's request, stop and tell the user that the WeChat skill needs a human upgrade.

## Execution Contract

1. WeChat tasks are real desktop-operation tasks. Reading this skill, reading memory, or describing a workflow is not execution.
2. The first observable step must be a real local tool call that runs one of the approved scripts from this skill's scripts directory.
3. Do not claim that WeChat was opened, searched, clicked, inspected, or messaged unless the immediately preceding tool result proves it.
4. If no real tool was called, say the action was not executed. Do not simulate step-by-step progress in text.
5. If the user says the visible UI did not change, trust the user and debug the script result. Do not insist that the action succeeded.
6. Do not use old chat history as proof of a current desktop action.

## Forbidden During Normal Use

Hermes must not:

- create temporary WeChat scripts;
- create replacement scripts such as search_friend.py, improved_monitor.py, or similar one-off files;
- edit SKILL.md;
- edit files in scripts;
- use ad-hoc python -c commands for Chinese WeChat text;
- press Down/Up or otherwise guess a search-result rank unless an official script returns a verified result list;
- claim a screenshot exists unless a screenshot script returned its path;
- claim the mouse is visible in a normal screenshot.

If a change is needed, ask the user to let the maintainer update the skill. Do not self-upgrade the skill while handling a WeChat task.

## Paths

Skill folder:

$env:HERMES_HOME\skills\software-development\wechat-messaging

Scripts folder:

$env:HERMES_HOME\skills\software-development\wechat-messaging\scripts

Use Hermes private Python:

$env:HERMES_HOME\hermes-agent\venv\Scripts\python.exe

Temporary screenshots:

$env:HERMES_HOME\skills\software-development\wechat-messaging\temp_screenshots

## Approved Script Roles

Official entry scripts:

- verify_wechat_window.py: check, wake, restore, and foreground the real WeChat window.
- send_message.py: send a message to a named contact. This is the only approved entrypoint for active send-message requests.
- locate_message_button.py: locate the left-side WeChat message button and unread red badge. Use this before clicking or monitoring unread messages.
- monitor_unread.py: official unread-monitor evidence entrypoint. It opens/foregrounds WeChat, locates the message button, double-clicks unread cycles, and returns screenshot evidence.

Support modules:

- wechat_window.py: strict WeChat process/window detection, Ctrl+Alt+W wake hotkey, foreground activation, DPI-aware client coordinates, cursor position, and click helpers.
- wechat_utils.py: Ctrl+F, Ctrl+V, Enter, clipboard, and the verified active-send flow used by send_message.py.
- message_sender.py: send a reply in the currently open chat after the chat window is already selected.
- screenshot_utils.py: capture the WeChat window, optionally draw cursor/grid overlays, and clean temporary screenshots.
- chat_history.py: store and read local per-contact chat history.
- auto_reply_config.py: configuration values for auto-reply behavior.

Demo/support files:

- example_auto_reply.py: demonstration only. Do not use it as the official monitoring entrypoint.
- README.md and requirements.txt: documentation and dependencies.

## Step 1: Open And Foreground WeChat

All WeChat operations must start here.

1. Run verify_wechat_window.py.
2. If no real WeChat process window is found, tell the user: WeChat is not running or not logged in.
3. If WeChat is running, the script may use Ctrl+Alt+W through wechat_window.send_wechat_hotkey() to wake it.
4. The script must then restore and foreground the window through restore_and_focus() / force_foreground().
5. Continue only when the script reports RESTORE_OK=True.

Important implementation detail: opening/foregrounding is not just the hotkey. The reliable sequence is:

- detect real WeChat by process name: Weixin.exe, WeChat.exe, or WeChatAppEx.exe;
- send Ctrl+Alt+W only when wake-up is needed;
- restore the window;
- use AttachThreadInput and SetForegroundWindow;
- verify the foreground result.

## Flow A: Send A Message To A Named Contact

Use this for: send a message to AI数字人, 给某个好友发消息, or any active one-off send request.

Approved entrypoint: send_message.py.

Required flow:

1. Run verify_wechat_window.py.
2. Run send_message.py with HERMES_WECHAT_CONTACT and HERMES_WECHAT_MESSAGE.
3. send_message.py must use the existing wechat_utils.send_wechat_message() flow:
   - foreground real WeChat;
   - press Ctrl+F;
   - paste the contact name through the clipboard;
   - verify the search field by copying it back; continue only if SEARCH_OK=True / SEARCH_TEXT_MATCH=True;
   - press Enter to open the first search result;
   - re-foreground WeChat after the chat opens;
   - click the lower-right chat input box directly;
   - paste the message through the clipboard;
   - press Enter to send.
4. If SEARCH_OK=False or SEARCH_TEXT_MATCH=False, stop immediately. Do not press Enter and do not send the message.
5. Do not press Down to choose a guessed second or third search result. If the first opened chat cannot be verified as the requested contact, stop and report verification failure.
6. If Chinese contact search appears to fail, first run send_message.py --search-only with the same HERMES_WECHAT_CONTACT. This must leave WeChat open with the contact text pasted into the search box and must not open a chat or send a message. Ask the user to visually confirm the search text before retrying a real send.
7. After sending, capture the window and verify:
   - the current chat is the intended contact;
   - the sent message is visible;
   - there is no visible failed-send marker.
8. Update local chat history only after the visible send result is verified.
9. If verification fails, run the same Ctrl+F search/send flow one more time. If it fails again, stop and ask the user to inspect the WeChat UI.

Do not use a separate search script. The Ctrl+F search is already part of send_message.py / wechat_utils.py.


Chinese search debug pattern, no message is sent:

```powershell
$env:HERMES_WECHAT_CONTACT='姐姐'
$env:HERMES_HOME\hermes-agent\venv\Scripts\python.exe $env:HERMES_HOME\skills\software-development\wechat-messaging\scripts\send_message.py --search-only
```

Example command pattern:

```powershell
$env:HERMES_WECHAT_CONTACT='AI数字人'
$env:HERMES_WECHAT_MESSAGE='测试消息'
$env:HERMES_HOME\hermes-agent\venv\Scripts\python.exe $env:HERMES_HOME\skills\software-development\wechat-messaging\scripts\send_message.py
```

## Flow B: Monitor Unread Messages For A Contact

Use this for: 看看 AI数字人 有没有发新消息, 监控某个微信好友, or 有新消息就回复.

Approved entrypoint: monitor_unread.py. Hermes must not create a new monitor script during the task.

Required flow:

1. Run monitor_unread.py with --max-cycles set to the number of unread contacts to cycle this pass. Use --clean-first for a fresh test run.
2. Inspect the JSON result and screenshot paths returned by monitor_unread.py.
3. Inspect the locator result:
   - if the method indicates no red unread badge and the screenshot confirms no red unread number on the message button, report that there are no unread WeChat messages;
   - if a red unread badge exists, continue.
4. monitor_unread.py must move/click only using the client_point returned by locate_message_button.py. Do not use old absolute coordinates such as (76, 200) or (114, 204).
5. monitor_unread.py double-clicks the left-side message button once per cycle.
6. After each double-click, inspect the screenshot of the chat-person list immediately to the right of the message button, in the middle-left column of WeChat.
7. Do not inspect the right-side chat title first. The right-side chat title is only proof after the desired contact has been selected from the chat-person list.
8. For every chat-person list item that has a red unread badge:
   - click that list item to clear the unread state;
   - if it is not the target contact, continue cycling;
   - if it is the target contact, open the chat and process it.
9. For the target contact:
   - capture the visible chat area;
   - compare visible messages with chat_history.py;
   - identify all new incoming messages, not only one line;
   - generate a reply only if the intent is clear;
   - if confidence is low, stop and ask the user to provide the reply.
10. To send the reply:
   - click the chat input box using click_wechat_input_box();
   - use message_sender.py or the existing support function to paste and send;
   - capture the window after sending;
   - update chat history only after visible verification.
11. Even after replying to the target contact, continue clearing other unread chats until the message button no longer shows a red unread number.
12. Only when the message button has no red unread number can Hermes conclude that the monitored contact currently has no more unread messages.

This flow supports one monitored contact now. For multiple monitored contacts, the maintainer should add configuration to monitor_unread.py instead of letting Hermes create another script.

## Screenshot And Cursor Rules

Normal Windows screenshots usually do not include the real mouse cursor. If cursor position matters, capture with cursor/grid overlays through screenshot_utils.capture_window(..., draw_cursor=True, draw_grid=True) and inspect the red crosshair overlay.

Always clean temporary screenshots after a test or monitor run by using screenshot_utils.cleanup_temp_screenshots().

## Known Pitfalls

1. SetForegroundWindow can silently fail unless AttachThreadInput is used. wechat_window.force_foreground() already handles this.
2. Chinese text in command-line arguments may become mojibake. Prefer environment variables and clipboard paste.
3. WeChat focus changes after opening a chat. Re-foreground and click the input box before sending.
4. If the search field did not contain the target contact after paste verification, the script must stop. Continuing would risk sending to the wrong chat.
5. Never guess search result rank with arrow keys. Guessing can send to the wrong chat.
6. Chat-person list verification must happen in the list immediately right of the left navigation rail, not in the right chat panel title.
7. Do not rely on Tab to reach the input box. WeChat focus order changes.

## Change Log

- 2026-06-20: Added send_message.py --search-only for Chinese contact-search verification without sending messages.
- 2026-06-20: Added monitor_unread.py as the official unread-monitor evidence entrypoint.
- 2026-06-20: Reorganized the skill into fixed approved entrypoints, removed duplicated/experimental script guidance, and clarified the unread-monitoring flow. Hermes is now explicitly forbidden from creating or editing WeChat scripts during normal execution.
- 2026-06-20: Added execution-contract wording so WeChat tasks must start with real local tool calls and cannot be simulated in text.
- 2026-06-19: Added DPI-aware client-area coordinate helpers and annotated screenshots with cursor/grid overlays, because normal screenshots do not show the mouse pointer.
- 2026-06-19: Removed polluted fixed-coordinate guidance. Require window-relative positioning and per-step visible verification.
- 2026-06-16: Fixed foreground activation: added AttachThreadInput, re-activated WeChat after opening a chat, and corrected GetCurrentThreadId() to kernel32.
- 2026-06-16: Enforced strict process-based WeChat detection, replaced Tab-based input focusing with direct input-area click, and added send_message.py to avoid Chinese command-line encoding loss.
