# Windows Computer Use Investigation

**Date**: May 31, 2026  
**Session context**: User inquiry about controlling desktop applications (QQ, WeChat) via Hermes Agent

## Investigation Summary

### User Request
User wanted to know if Hermes Agent could:
1. Control desktop software like QQ on Windows
2. Use mouse and keyboard automation
3. Take screenshots and analyze them with AI models
4. Automate message sending in desktop applications

### Initial Assumption
User correctly identified that Hermes has `computer_use` capabilities that should support:
- Mouse and keyboard control
- Screenshot capture
- UI element interaction

### Discovery Process

#### 1. Toolset Availability Check
```bash
hermes tools list
```
Found `computer_use` toolset listed but disabled.

#### 2. Enabling the Toolset
```bash
hermes tools enable computer_use
```
Successfully enabled, but tool description showed "Universal macOS desktop control via cua-driver".

#### 3. Code Inspection
Examined the implementation structure:

**Key files found**:
- `tools/computer_use_tool.py` - Shim for tool registration
- `tools/computer_use/cua_backend.py` - macOS-only backend
- `tools/computer_use/backend.py` - Abstract interface

**Critical findings in code**:
```python
# cua_backend.py line 1
"""Cua-driver backend (macOS only)."

# cua_backend.py line 80-81
def _is_macos() -> bool:
    return sys.platform == "darwin"
```

#### 4. Architecture Analysis
The system is well-architected for multi-platform support:
- Abstract `ComputerUseBackend` class defines interface
- Platform-specific backends can be implemented
- Current implementation only has `cua_backend.py` for macOS

### Platform Limitation Confirmation

**Current state**:
- `computer_use` toolset exists and can be enabled
- Backend implementation is **macOS-only** (`cua-driver`)
- Windows support requires a new backend implementation
- No Windows backend exists in current Hermes Agent codebase

### Alternative Approaches Identified

For Windows users needing desktop automation:

#### 1. Browser Automation
- Use existing `browser` toolset for web applications
- Supports similar capabilities for web-based interfaces

#### 2. Script-Based Automation
- Use `terminal` toolset to run Python scripts
- Libraries like `pyautogui` or `uiautomation` for Windows

#### 3. External Tool Integration
- Could implement Windows backend using:
  - `uiautomation` (Windows UI Automation API)
  - `pywinauto` (advanced Windows GUI automation)
  - `pyautogui` (cross-platform but limited)

### User Communication

**Key points conveyed to user**:
1. Acknowledged their correct understanding of Hermes capabilities
2. Explained the current macOS-only limitation
3. Provided alternative approaches for Windows
4. Explained the architecture for potential future Windows support

### Technical Details

**File structure examined**:
```
tools/computer_use/
├── backend.py              # Abstract interface
├── cua_backend.py          # macOS implementation (cua-driver)
├── schema.py              # Tool schema definitions
├── tool.py                # Main tool handler
└── vision_routing.py      # Vision model routing
```

**Backend interface methods** (from `backend.py`):
- `capture()` - Screenshot capture with element detection
- `click()` - Mouse click operations
- `type_text()` - Keyboard input
- `scroll()` - Mouse wheel scrolling
- `drag()` - Mouse drag operations
- `key()` - Individual key presses

### Recommendations for Future Windows Support

To implement Windows support:

1. **Create `windows_backend.py`** implementing `ComputerUseBackend`
2. **Use `uiautomation` library** for Windows UI Automation API access
3. **Add platform detection** in tool initialization
4. **Update requirements check** to verify Windows capabilities
5. **Consider installation requirements** (Python packages, system permissions)

### Session Outcome

User received:
1. Clear explanation of current limitations
2. Understanding of why the limitation exists
3. Practical alternatives for Windows automation
4. Insight into Hermes architecture for potential future enhancements

---

**Investigation conducted by**: Hermes Agent  
**Hermes Agent version**: v2026.5.29  
**User platform**: Windows 10  
**Key takeaway**: Desktop automation capabilities are platform-dependent; current Hermes implementation favors macOS with `cua-driver` backend.