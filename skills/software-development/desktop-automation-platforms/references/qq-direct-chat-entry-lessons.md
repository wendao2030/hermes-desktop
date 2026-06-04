# QQ Direct Chat Entry Lessons (May 31, 2026)

## User Correction and Key Insight

### Problem Identified
When automating QQ message sending, clicking on the contact name/button in search results often opens a friend profile card instead of directly entering the chat window. This requires additional steps to click the "发消息" button, complicating the automation workflow.

### User Correction (May 31, 2026)
The user explicitly provided the correct approach:
> "在搜索框搜到AI数字人后，点击搜索到的结果（而不是点击AI数字人按钮），直接进入聊天界面"

**Translation**: "After searching for AI数字人 in the search box, click on the search result (not the AI数字人 button) to directly enter the chat interface."

## Technical Implementation Details

### Element Analysis Findings
During testing on May 31, 2026, we discovered:

**Search Results Interface Elements**:
- **Button elements (incorrect)**: 
  - `index: 87`, `role: "Button"`, `label: "AI数字人"`
  - Clicking this opens the friend profile card
  - Requires additional click on "发消息" button
  
- **ListItem elements (correct)**:
  - `index: 45`, `role: "ListItem"`, `label: "AI数字人 联系人"`
  - `index: 46`, `role: "ListItem"`, `label: "AI数字人 联系人"` (duplicate)
  - Clicking this directly enters the chat window

### Why This Matters
1. **Workflow simplification**: Direct chat entry eliminates 1-2 extra steps
2. **Reliability**: Profile cards may have varying layouts, chat windows are consistent
3. **User expectation**: Users naturally click on search results to chat, not on buttons

## Best Practice Implementation

### 1. Element Detection Strategy
```python
# Use text-based analysis when model doesn't support images
computer_use(action='capture', app='QQ', mode='ax', max_elements=150)

# Look for ListItem elements with contact names
# Correct: {"index": 45, "role": "ListItem", "label": "AI数字人 联系人"}
# Incorrect: {"index": 87, "role": "Button", "label": "AI数字人"}
```

### 2. Click Sequence
```python
# Correct: Click on ListItem element
computer_use(action='click', element=45)

# Follow up with Enter key if needed
computer_use(action='key', keys='return')
```

### 3. Verification
```python
# Capture after clicking to verify chat window opened
computer_use(action='capture', app='QQ', mode='ax', capture_after=True)

# Look for chat window indicators:
# - "消息记录" (message history)
# - "发送" (send button)
# - Text input field
```

## Complete Workflow Example

### Successful Test (May 31, 2026)
1. **Search contact**: Click search box (element #41), type "AI数字人"
2. **Select result**: Click ListItem element #45 (NOT Button #87)
3. **Enter chat**: Press Enter key to ensure chat window opens
4. **Type message**: Use Tab to focus input field, type test message
5. **Send message**: Press Enter key

### Messages Successfully Sent
1. "测试消息：这是通过Hermes Agent和cua-driver发送的QQ自动化测试"
2. "QQ自动化测试完成！cua-driver在Windows 10上运行正常，Hermes Agent可以成功控制QQ发送消息"

## Lessons for Future Automation

### Key Principles
1. **Observe user behavior**: Users naturally click on search results, not on buttons
2. **Test both approaches**: Always verify what each element does
3. **Document element types**: Note the role (ListItem vs Button) for future reference
4. **Update skills immediately**: When users correct your approach, incorporate it immediately

### Common Pitfalls to Avoid
1. **Assuming all clickable elements are equal**: Different element types have different behaviors
2. **Not verifying after clicking**: Always re-capture to confirm the expected UI change
3. **Ignoring user corrections**: User-provided workflows are often more efficient

## Technical Notes

### Element Identification Tips
- **Use `mode='ax'`**: Better for text-based analysis when images aren't supported
- **Increase `max_elements`**: 100-150 for complex interfaces like QQ
- **Look for patterns**: "联系人" suffix in labels often indicates ListItem elements
- **Avoid duplicate elements**: QQ sometimes has duplicate elements; test both if unsure

### Focus Management
- **Tab navigation**: Use `keys='tab'` to cycle through focusable elements
- **Direct typing**: `action='type'` often works even without explicit focus
- **Enter key confirmation**: Some actions require Enter to confirm

## User Communication Guidelines

### When Explaining This Approach
**Use Chinese for technical terms**:
- "搜索到的结果" (search result) vs "AI数字人按钮" (AI数字人 button)
- "直接进入聊天界面" (directly enter chat interface)
- "好友简介卡片" (friend profile card)

**Provide clear comparisons**:
- **正确做法**: 点击搜索结果条目 (ListItem)
- **错误做法**: 点击联系人按钮 (Button)

### Confirmation Questions
When users ask about QQ automation, confirm:
1. "您希望我直接点击搜索结果进入聊天界面，对吗？"
2. "是否需要避免点击按钮弹出好友卡片？"

## Related References
- `desktop-automation-platforms` skill - Main skill containing this update
- `qq-automation-verification-2026-05-31.md` - Complete verification report
- `successful-qq-control-commands.md` - Verified command sequences
- `qq-finding-contacts.md` - Contact search implementation

---
**Last Updated**: May 31, 2026  
**Tested On**: Windows 10, QQ latest version  
**Hermes Agent**: computer_use toolset with cua-driver backend  
**User Language**: Chinese (technical communication preferred)  
**Key Lesson**: Direct chat entry via ListItem click > Button click with profile card