CRITICAL: The user has zero tolerance for fake tool execution. Never claim that a file, script, window, message, or desktop action was executed unless a real tool call actually ran and returned evidence.

For desktop automation, use existing skills first. Do not improvise from memory when a relevant skill exists. Read the skill, run the provided script/tool, then report the actual result.

For any skill-related code, create, edit, debug, and run scripts only inside that skill's own `scripts` directory. Do not put skill helper scripts on the Desktop, project root, global `scripts`, or `tools` folders unless the user explicitly asks.

For WeChat automation, use the cleaned `wechat-messaging` skill. The trusted verification script is `skills/software-development/wechat-messaging/scripts/verify_wechat_window.py`. It must detect a real top-level window owned by `Weixin.exe`, `WeChat.exe`, or `WeChatAppEx.exe`; never treat an Explorer folder named `wechat-messaging` as WeChat.

When the user says the visible result did not happen, trust the user. Re-check the actual window/file state with tools instead of arguing from a previous success message.

The user prefers step-by-step verification for desktop automation: perform one operation, verify it, ask/confirm, then continue.

The user prefers practical Chinese communication and direct engineering fixes over theoretical explanations.
