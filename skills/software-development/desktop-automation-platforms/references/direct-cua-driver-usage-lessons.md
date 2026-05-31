# Direct cua-driver Usage Lessons

**Date**: May 31, 2026  
**Session Context**: Desktop automation for Windows applications (QQ control)

## Key Lessons Learned

### 1. **Avoid Over-Engineering**
- **Problem**: Wrote complex Python scripts when simple `cua-driver` commands existed
- **Solution**: Use `cua-driver` command-line tools directly
- **User Correction**: "不是有cua-driver吗？为什么你要自己写脚本？" (Don't you have cua-driver? Why are you writing your own scripts?)

### 2. **Tool Selection Guidelines**
- **Simple commands** → Use `terminal` tool
- **Complex logic with conditional steps** → Use `execute_code`
- **Multi-step automation** → Chain `cua-driver` commands, not custom scripts

### 3. **Common Pitfalls in Terminal Usage**
- **Command interruption**: Complex commands with pipes can get interrupted
- **Grep failures**: Case sensitivity, encoding issues
- **Timeout issues**: Long-running commands need proper handling

### 4. **Best Practices Identified**

#### For cua-driver Usage:
```bash
# ✅ Good: Simple direct commands
cua-driver --version
cua-driver get_screen_size
cua-driver list_windows

# ✅ Good: Simple filtering
cua-driver list_windows | grep -i qq

# ❌ Avoid: Complex custom scripts when commands exist
# Don't write Python to parse JSON when cua-driver already provides the data
```

#### For Terminal Tool Usage:
```python
# ✅ Good: Use execute_code for multi-step logic
from hermes_tools import terminal

# Check availability
result = terminal('cua-driver --version')
if 'cua-driver' in result['output']:
    # Continue with automation
    pass

# ❌ Avoid: Complex terminal chains
# terminal('cua-driver list_windows | grep -i qq | head -5 | awk ...')
```

### 5. **Workflow Correction**
**Before (Incorrect)**:
1. Write custom Python script to find windows
2. Parse JSON output manually
3. Implement custom click/type logic
4. Handle errors in custom code

**After (Correct)**:
1. Use `cua-driver list_windows` directly
2. Use `cua-driver call` commands for actions
3. Let cua-driver handle errors and retries
4. Only write custom code when cua-driver lacks functionality

### 6. **User Expectations**
- Users expect direct use of available tools
- Avoid unnecessary abstraction layers
- Keep solutions simple and transparent
- When a tool exists for a task, use it directly

### 7. **Implementation Examples**

#### Finding and Controlling QQ:
```bash
# Direct approach (recommended)
cua-driver list_windows | grep -i "qq\|腾讯"

# If found, control directly
cua-driver call type_text '{"pid": 1234, "text": "Hello from automation"}'
cua-driver call press_key '{"pid": 1234, "key": "Enter"}'
```

#### Alternative with execute_code (when needed):
```python
# Only use when you need conditional logic
from hermes_tools import terminal
import json

# Check if QQ is running
result = terminal('cua-driver list_windows')
try:
    windows = json.loads(result['output'])
    qq_windows = [w for w in windows if 'QQ' in w.get('title', '').upper()]
    
    if qq_windows:
        # Control first QQ window
        window = qq_windows[0]
        terminal(f'cua-driver call type_text {{\"pid\": {window["pid"]}, \"text\": \"Hello\"}}')
except json.JSONDecodeError:
    # Handle parsing error
    print("Failed to parse window list")
```

## Summary
- **Direct tools over custom code**: Always prefer existing command-line tools
- **Keep it simple**: Complex scripts add maintenance burden
- **User feedback is valuable**: When users point out simpler approaches, incorporate them
- **Update skills proactively**: Capture lessons to prevent repeating mistakes