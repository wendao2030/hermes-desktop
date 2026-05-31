# Successful QQ Control Commands (May 31, 2026)

This document contains the exact commands that successfully controlled QQ on Windows 10 using cua-driver.

## Environment
- Windows 10
- cua-driver version 0.4.0 (Rust implementation)
- Hermes Agent with modified code (removed macOS platform restrictions)
- QQ application running (PID: 5160, Window ID: 264124)

## Successful Commands

### 1. Get Window State
```bash
cua-driver call get_window_state '{"pid": 5160, "window_id": 264124, "capture_mode": "som"}'
```

**Output**: Returns complete UI tree with 139 elements, screenshot (964x646), and element details.

### 2. Bring Window to Front
```bash
cua-driver call bring_to_front '{"pid": 5160, "window_id": 264124}'
```

**Output**: 
```json
{
  "landed_on_target": true,
  "now_fg_hwnd": "0x407bc",
  "previous_fg_hwnd": "0x407bc",
  "target_hwnd": "0x407bc"
}
```

### 3. Type Text in Input Field
```bash
cua-driver call type_text '{"pid": 5160, "text": "这是通过 cua-driver 自动发送的消息"}'
```

**Output**: `✅ Typed 23 char(s) on pid 5160 via PostMessage (30ms delay).`

### 4. Send Message (Press Enter)
```bash
cua-driver call press_key '{"pid": 5160, "key": "Enter"}'
```

**Output**: `✅ Pressed Enter on pid 5160.`

## Complete Workflow Example

This single command chain successfully performed the entire QQ automation workflow:

```bash
cua-driver call bring_to_front '{"pid": 5160, "window_id": 264124}' && sleep 1 && cua-driver call type_text '{"pid": 5160, "text": "这是通过 cua-driver 自动发送的消息"}' && sleep 1 && cua-driver call press_key '{"pid": 5160, "key": "Enter"}'
```

## Key Insights

1. **Use `cua-driver call` format** with JSON parameters for all operations
2. **Element indexing**: Input field was element 134, Send button was element 136 in UI tree
3. **Press Enter is more reliable** than clicking Send button (avoids element cache issues)
4. **Always call `get_window_state` first** to refresh element cache before clicking by index
5. **Use `bring_to_front`** to ensure window has focus before typing

## Common Issues and Solutions

### Issue: "Element 136 not in cache for hwnd=264124. Call get_window_state first."
**Solution**: Always call `get_window_state` before trying to click elements by index.

### Issue: Input not appearing in QQ
**Solution**: Use `bring_to_front` to ensure the window is active before typing.

### Issue: Can't find QQ window
**Solution**: Use `cua-driver call list_windows` and look for "QQ" or "腾讯" in titles.

## Verification Commands

To verify cua-driver is working:

```bash
# Check version
cua-driver --version
# Expected: cua-driver 0.4.0

# Get screen size
cua-driver get_screen_size
# Expected: {"width": 1440, "height": 960, "scale_factor": 1.0}

# Get cursor position
cua-driver get_cursor_position
# Expected: {"x": <x_coord>, "y": <y_coord>}
```

## Notes
- The `cua-driver call` command format is more reliable than individual command-line flags
- JSON parameters allow precise control of all options
- Sleep commands (&& sleep 1) help ensure operations complete before next command starts
- This approach works for any Windows application, not just QQ