# WeChat Messaging Scripts

This folder contains the fixed local scripts used by the Hermes WeChat skill.
During normal task execution, Hermes must use these scripts as-is. Hermes must
not create new WeChat scripts or rewrite these files while handling a user task.

## Official entry scripts

- `verify_wechat_window.py`
  - Finds the real WeChat window by process name.
  - Wakes WeChat with `Ctrl+Alt+W` when needed.
  - Restores and foregrounds the window.
  - Prints `RESTORE_OK=True` only when foreground activation succeeds.

- `send_message.py`
  - The only approved entrypoint for actively sending a message to a named contact.
  - Reads `HERMES_WECHAT_CONTACT` and `HERMES_WECHAT_MESSAGE`.
  - Uses the existing `Ctrl+F` search flow in `wechat_utils.py`.
  - Supports `--search-only` to paste a contact into WeChat search without opening a chat or sending.

- `locate_message_button.py`
  - Locates the left-side WeChat message button.
  - Prefers red unread-badge detection, then green message-icon detection.
  - Returns window/client/screen coordinates and a screenshot path.

- `monitor_unread.py`
  - Official unread-monitor evidence entrypoint.
  - Opens/foregrounds WeChat, locates the message button, double-clicks unread cycles, and returns screenshot paths.
  - Does not OCR contact names or invent replies. The caller must inspect the screenshots.

## Support modules

- `wechat_window.py`: strict WeChat detection, foreground activation, client coordinates, cursor helpers, clicks.
- `wechat_utils.py`: Ctrl+F, Ctrl+V, Enter, clipboard, and active-send flow used by `send_message.py`.
- `message_sender.py`: sends a reply in the currently selected chat.
- `screenshot_utils.py`: captures WeChat screenshots and cleans `temp_screenshots`.
- `chat_history.py`: local per-contact chat history.
- `auto_reply_config.py`: auto-reply configuration.

## Demo/support only

- `example_auto_reply.py`: demo only; not the official monitor entrypoint.
- `requirements.txt`: Python dependencies.

## Active send flow

1. Run `verify_wechat_window.py`.
2. Run `send_message.py` with environment variables.
3. The script foregrounds WeChat, presses `Ctrl+F`, pastes the contact, copies the search field back, and continues only when `SEARCH_TEXT_MATCH=True` / `SEARCH_OK=True`. Then it opens the first result, clicks the input box, pastes the message, and presses Enter.
4. If `SEARCH_OK=False`, the caller must report that contact search failed and must not claim the message was sent.
5. If Chinese search text appears missing or truncated, run `send_message.py --search-only` first. It should leave the contact visible in WeChat search and send nothing.
6. The caller must capture/verify the visible result before saying the message was sent.

Example:

```powershell
$env:HERMES_WECHAT_CONTACT='<contact name from user>'
$env:HERMES_WECHAT_MESSAGE='<message text from user>'
C:\Users\dtyao\AppData\Local\hermes\venv\Scripts\python.exe C:\Users\dtyao\AppData\Local\hermes\skills\software-development\wechat-messaging\scripts\send_message.py
```


Search-only Chinese contact check, no send:

```powershell
$env:HERMES_WECHAT_CONTACT='姐姐'
C:\Users\dtyao\AppData\Local\hermes\venv\Scripts\python.exe C:\Users\dtyao\AppData\Local\hermes\skills\software-development\wechat-messaging\scripts\send_message.py --search-only
```

Avoid copying old examples that contain mojibake. If Chinese text appears truncated in WeChat search, first run `send_message.py --dry-run` and check whether `CONTACT=` is complete, then inspect `CONTACT_UNICODE_ESCAPE` and `CLIPBOARD_CONTACT_MATCH` from the real send run.

## Unread monitoring flow

Use `monitor_unread.py` as the official entrypoint:

1. Run `monitor_unread.py --clean-first --max-cycles 1` for a fresh single-cycle check.
2. If unread messages remain, run with a larger `--max-cycles` or run another pass.
3. Inspect the chat-person list immediately to the right of the message button in each returned screenshot.
4. Select unread contacts from that list, clear unread state, and process the target contact.
5. Use screenshots plus `chat_history.py` to decide which incoming messages are new.
6. Use `message_sender.py` only after the target chat is selected and the input box is clicked.

Do not inspect the right-side chat title before selecting a person from the chat-person list.

## Temporary screenshots

Screenshots belong in:

`C:\Users\dtyao\AppData\Local\hermes\skills\software-development\wechat-messaging\temp_screenshots`

Clean them with `screenshot_utils.cleanup_temp_screenshots()` after tests.
