# cua-driver Technical Details: How Desktop Automation Works
**Date**: June 2, 2026  
**Context**: User questions about how computer_use gets UI information without opening interfaces

## Core Question from User
> "哪里来的文本描述？你又是怎么定位到输入框的位置？按钮的位置？computer_use到底如何获取这个qq窗体的信息？他自己通过截图解析出来的？"

## Detailed Technical Explanation

### 1. How cua-driver Gets UI Information (NOT Through Screenshot Parsing)

**Common Misconception**: People think desktop automation works by:
1. Taking a screenshot
2. Using OCR to read text
3. Using computer vision to find buttons

**Actual Implementation (cua-driver on Windows)**:
1. **Uses Windows UIAutomation API** - built-in Windows accessibility framework
2. **Direct programmatic access** to UI element properties
3. **No OCR or computer vision needed** for basic operations

### 2. Source of Text Descriptions

**Where text comes from**:
```
UIA Element Properties:
└── Name: "搜索"                    ← Text label (from application)
└── Role: "Edit"                   ← Control type
└── AutomationId: "SearchBox"      ← Programmatic ID
└── Bounds: {x:100, y:200, w:200, h:30} ← Screen coordinates
└── ClassName: "Edit"              ← Windows control class
```

**Key Insight**: The text "搜索" comes directly from the application's UI element properties, not from analyzing a screenshot.

### 3. How Input Box and Button Positions are Located

**Not through image analysis**:
```
// BAD (what people think happens):
1. Take screenshot
2. Analyze image for "搜索" text
3. Calculate coordinates of that text
4. Click at those coordinates

// GOOD (what actually happens):
1. Call UIA API: GetElementByName("搜索")
2. API returns: element with Bounds={x:100, y:200, w:200, h:30}
3. Click at coordinates: (x + w/2, y + h/2) = (200, 215)
```

**Advantages of UIA approach**:
- **More accurate**: No OCR errors
- **Faster**: Direct API call vs image processing
- **More reliable**: Works with any visual theme/font
- **Accessibility**: Same API used by screen readers

### 4. Complete Information Flow

```
User requests QQ automation
    ↓
cua-driver calls Windows UIAutomation API
    ↓
Windows returns UI tree for QQ window
    ↓
cua-driver processes tree:
    • Element #41: Role=Edit, Name="搜索", Bounds=(100,200,200,30)
    • Element #42: Role=Button, Name="发送", Bounds=(320,200,80,30)
    • Element #43: Role=List, Name="联系人列表", Bounds=(0,0,100,600)
    ↓
Hermes Agent receives structured data
    ↓
Agent can click element #41 (search box) using exact coordinates
```

### 5. Screenshot Analysis (When Used)

**Two separate data sources**:
1. **UIA tree** (always available): Text labels, coordinates, control types
2. **Screenshot** (optional): Visual verification, numbered overlays

**With vision-capable model** (`mode='som'`):
- Gets UIA tree + screenshot
- Shows numbered overlays on screenshot for visual reference
- Agent can see both text data and visual representation

**Without vision support** (`mode='ax'`):
- Gets only UIA tree (text data)
- Still has all coordinates and labels
- Can perform actions but can't see visual results

### 6. Verification of Current Interface State

**User concern**: "你没打开界面你怎么截图的？"

**Answer**: When we say "capture the interface", we mean:
1. **UIA capture** (`mode='ax'`): Gets current UI tree from Windows API
2. **Visual capture** (`mode='som'`/`mode='vision'`): Takes actual screenshot

**Important**: Even if model can't see screenshots, UIA capture still works and provides:
- Current window state
- Available elements
- Their positions and properties
- Whether interface is actually open

### 7. Practical Example: Finding QQ Search Box

**Step-by-step process**:
```python
# 1. Get current UI state (text-based, works without vision)
result = computer_use(action='capture', mode='ax', max_elements=200)

# 2. Search for "搜索" in element labels
search_box_idx = None
for elem in result['elements']:
    if '搜索' in elem.get('label', ''):
        search_box_idx = elem['index']
        break

# 3. Element properties from UIA (not from screenshot):
# {
#   "index": 41,
#   "role": "Edit",
#   "label": "搜索",
#   "bounds": {"x": 100, "y": 200, "width": 200, "height": 30},
#   "automation_id": "SearchBox_Edit",
#   "class_name": "Edit"
# }

# 4. Click using UIA coordinates
if search_box_idx is not None:
    computer_use(action='click', element=search_box_idx)
    # This clicks at (200, 215) - center of bounds from UIA
```

### 8. Why This Matters for User Trust

**User's valid concern**: They want to know operations are based on actual interface state, not assumptions.

**How we address this**:
1. **Always capture current state** before action
2. **Verify elements exist** in current capture
3. **Use actual coordinates** from UIA, not guessed positions
4. **Document the source** of all information (UIA vs screenshot)

### 9. Limitations and Workarounds

**When UIA doesn't work well**:
- Some applications have poor UIA implementation
- Custom controls may not expose proper properties
- Workaround: Use `mode='vision'` + computer vision (if model supports it)

**When model doesn't support images**:
- Use `mode='ax'` for text-based analysis
- Rely on UIA coordinates for clicking
- Ask user for manual verification of visual results

### 10. Key Takeaways for Users

1. **Text descriptions come from** Windows UIA API, not screenshot OCR
2. **Coordinates come from** UIA element bounds, not image analysis
3. **Operations are based on** current interface state via UIA
4. **Screenshots are for** visual verification, not primary data source
5. **Even without screenshots**, UIA provides all needed information for automation

## Commands to Verify UIA Information

```bash
# Check what cua-driver tools are available
cua-driver list-tools

# See detailed description of get_window_state
cua-driver describe get_window_state

# Test UIA capture on a running application
cua-driver call get_window_state '{"pid": 1234, "window_id": 5678, "capture_mode": "ax"}'

# The response will show UIA tree with all element properties
```

## Conclusion

cua-driver's desktop automation works by:
1. **Using Windows UIAutomation API** to get direct programmatic access to UI elements
2. **Extracting text labels and coordinates** from application's own UI properties
3. **Providing structured data** (not image analysis) for reliable automation
4. **Supporting both visual and text-based** operation modes

This approach is more reliable than screenshot-based methods because it uses the same accessibility APIs that screen readers use, ensuring accurate and consistent access to UI elements.