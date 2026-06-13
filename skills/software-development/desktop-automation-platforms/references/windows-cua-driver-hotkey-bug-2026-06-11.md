# Windows cua-driver Hotkey Bug Analysis - June 11, 2026

## Executive Summary

**Critical Issue Discovered**: cua-driver on Windows sends global hotkeys to the wrong process (`explorer.exe`) instead of the target application window.

**Impact**: Hotkey-based automation for applications like WeChat fails silently, returning `ok: true` but not activating the intended application.

## Technical Analysis

### Problem Manifestation

**Tool Call**:
```python
computer_use(action='key', keys='ctrl+alt+w')
```

**Expected Result**: WeChat window activated
**Actual Result**: Returns success but nothing happens

**Tool Response**:
```json
{
  "ok": true,
  "action": "hotkey",
  "message": "✅ Pressed ctrl+option+w on pid 8788 via PostMessage (Win32 target)."
}
```

### Root Cause Investigation

**Process Verification**:
```bash
tasklist | findstr "8788"
# Output: explorer.exe 8788 Console 1 268,132 K
```

**Key Finding**: cua-driver sent the hotkey to `explorer.exe` (PID 8788) instead of WeChat.

### Technical Root Cause

1. **PostMessage API Misuse**: cua-driver uses `PostMessage` with the wrong window handle
2. **Global Hotkey Handling**: System-level hotkeys require different handling than application-level keys
3. **Process Matching Failure**: Unable to correctly identify target application window handle
4. **Silent Failure**: Returns success even when hotkey doesn't reach intended target

## User's Direct Correction

**User's Exact Words**: "你没有执行ctrl+F激活搜索"

**Context**: During WeChat message sending test, user observed that search functionality wasn't activated despite tool returning success.

**Implications**:
1. **Tool status ≠ operation success**: Even with `ok: true`, operations can fail
2. **User is final validator**: User observation is more reliable than tool status
3. **Step integrity matters**: Must verify each critical step actually executed

## Solution Implementation

### Python Script Workaround

Created three specialized Python scripts that bypass cua-driver's hotkey handling:

**Script 1**: `send_hotkey.py` - Sends `Ctrl+Alt+W` to activate WeChat
**Script 2**: `send_ctrl_f.py` - Sends `Ctrl+F` to activate search
**Script 3**: `send_enter.py` - Sends `Enter` key for selection/sending

**Location**: `C:\Users\dtyao\AppData\Local\hermes\scripts\`

**Technical Approach**:
- Direct Windows API calls using `ctypes.windll.user32.SendInput`
- Bypasses cua-driver's process matching issues
- System-level keyboard events identical to manual typing

**Usage**:
```bash
# Activate WeChat window
cd /c/Users/dtyao/AppData/Local/hermes/scripts && python send_hotkey.py

# Activate search
cd /c/Users/dtyao/AppData/Local/hermes/scripts && python send_ctrl_f.py

# Send Enter key
cd /c/Users/dtyao/AppData/Local/hermes/scripts && python send_enter.py
```

## Improved Operation Protocol

### Step 1: Process Target Verification
Before executing hotkeys, verify target process state:
```python
import subprocess
result = subprocess.run(['tasklist', '|', 'findstr', '-i', 'wechat'], 
                       capture_output=True, text=True, shell=True)
print(f"WeChat process status: {result.stdout}")
```

### Step 2: Alternative Activation Methods (Priority Order)
1. **Python Script Method** (Recommended): Direct Windows API, bypass cua-driver
2. **Start Menu Method**: `Win` → type "微信" → `Enter`
3. **Taskbar Method**: `Win+T` → arrow keys → `Enter`
4. **Command Line Method**: `start wechat:`

### Step 3: Enhanced Verification Mechanism
- **Pre-execution**: Check target process state
- **During execution**: Verify hotkey sent to correct process
- **Post-execution**: **Must** obtain user visual confirmation (window popup/interface change)

## Impact on Skill Design Principles

### 1. Redundancy Design Principle
Critical operations must have multiple implementation options:
- Primary method: Python script workaround
- Secondary method: Alternative activation paths
- Fallback: User manual intervention

### 2. Verification Mechanism Strengthening
Each critical step requires verification:
- Tool call success (`ok: true`)
- Process state verification
- User visual confirmation

### 3. Transparent Communication Requirement
When tool limitations are discovered:
- Immediately inform user of the limitation
- Explain technical root cause
- Present alternative solutions
- Document in skills for future reference

### 4. Active Update Mechanism
Upon discovering tool defects:
- Immediately update relevant skills
- Document workarounds and limitations
- Create reference files for detailed analysis

## Long-term Recommendations

### For cua-driver Improvement
1. **Add global hotkey special handling**: System-level vs application-level distinction
2. **Improve window/process matching algorithm**: Better target identification
3. **Add execution result verification**: Confirm hotkey reached intended target
4. **Better error reporting**: Distinguish between "sent" and "actually activated"

### For Skill Design
1. **Redundancy design**: Prepare multiple implementation options for critical operations
2. **Verification mechanisms**: Build verification into every critical step
3. **Transparent communication**: Clearly explain limitations and alternatives to users
4. **Active maintenance**: Update skills immediately when issues are discovered

## Key Lessons Learned

### 1. Tool Status ≠ Operation Success
Even when all tool calls return `ok: true`, operations can still fail.

### 2. User is the Ultimate Validator
User observation is more reliable than tool status reports.

### 3. Step Integrity Must Be Actively Verified
Cannot assume steps execute successfully; must actively verify each critical step.

### 4. Environment-Specific Solutions Required
Windows-specific cua-driver defects require Windows-specific solutions.

### 5. Proactive Skill Updates Are Essential
When users correct your approach, immediately incorporate the lesson into skills.

## Implementation Examples

### Complete WeChat Automation with Python Scripts
```python
# 1. Activate WeChat window
terminal('cd /c/Users/dtyao/AppData/Local/hermes/scripts && python send_hotkey.py')

# 2. Wait for WeChat to activate
computer_use(action='wait', seconds=3)

# 3. Activate search
terminal('cd /c/Users/dtyao/AppData/Local/hermes/scripts && python send_ctrl_f.py')

# 4. Wait for search box
computer_use(action='wait', seconds=2)

# 5. Type contact name
computer_use(action='type', text='AI 数字人')

# 6. Select search result
terminal('cd /c/Users/dtyao/AppData/Local/hermes/scripts && python send_enter.py')

# 7. Type message
computer_use(action='type', text='测试消息内容')

# 8. Send message
terminal('cd /c/Users/dtyao/AppData/Local/hermes/scripts && python send_enter.py')

# 9. Request user verification
print("操作完成，请检查微信聊天记录确认消息是否发送成功。")
```

## Related Files

- `references/step-integrity-verification-2026-06-11.md` - Detailed step integrity verification requirements
- `references/cua-driver-technical-details-2026-06-02.md` - cua-driver technical implementation details
- `references/user-verification-requirements-2026-06-02.md` - User verification expectations

## Status
**Issue**: Confirmed and documented
**Workaround**: Implemented and tested
**Skills Updated**: ✅ `wechat-messaging`, ✅ `desktop-automation-platforms`
**User Awareness**: Informed of limitation and solution