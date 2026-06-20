# WeChat Monitoring Protocol

This protocol is intentionally conservative. It records stable principles, not fixed screen coordinates.

## What Must Be Verified

1. The real WeChat window is restored and belongs to `Weixin.exe`, `WeChat.exe`, or `WeChatAppEx.exe`.
2. Any click target is computed from the current WeChat window bounds or verified visually.
3. The user can see important mouse movement when they are supervising the test.
4. A claimed unread badge, selected contact, chat content, or sent message must be backed by a current screenshot or script output.
5. If the user says the visible result did not happen, the user's observation wins.

## Coordinate Rule

Never persist absolute desktop coordinates such as `(76, 200)` or `(114, 204)` as truth.

Window position, DPI, scaling, and layout can change. Use one of these instead:

- window-relative coordinates derived from the current WeChat bounds
- UI automation element bounds when available
- current screenshots plus visual verification

## Monitoring Loop

1. Restore WeChat.
2. Get current window bounds.
3. Move/click relative to the current window.
4. Verify the selected UI state.
5. Open the target contact only after verifying it is the intended contact.
6. Read visible chat content.
7. Compare against local JSON history.
8. If a reply is needed, click the input box, paste the reply, and send.
9. Verify the visible send result.
10. Update local history only after verification.
11. Clean temporary screenshots.
