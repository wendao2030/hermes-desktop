# QQ Automation Workflow Corrections (May 31, 2026)

## Session Overview
This document captures critical workflow corrections provided by the user during QQ automation testing on Windows 10 using Hermes Agent's `computer_use` toolset.

## Key User Corrections

### 1. Search Results Auto-Enter Chat Interface

**User's Exact Words**: 
"你搜索得到刘海建后，就自动进入跟他的聊天界面了，这个之前跟你说过的，还有不要按esc，那会退出qq界面的"

**Previous Incorrect Approach**:
1. Search for contact (e.g., "刘海建")
2. Click on the search result button
3. This often opened friend profile card instead of chat window
4. Additional steps needed to click "发消息" (Send Message) button

**Corrected Approach**:
1. Search for contact (type name, press Enter)
2. **QQ automatically enters chat interface** - no clicking needed
3. **Do NOT press ESC** - this exits QQ interface entirely
4. Immediately start typing message in the chat window

### 2. Direct Tool Usage Over Custom Scripts

**User's Exact Words**:
"不是有cua-driver吗？为什么你要自己写脚本？"

**Translation**: "Don't you have cua-driver? Why are you writing your own scripts?"

**Key Lesson**: Users prefer direct use of available command-line tools (like cua-driver through Hermes `computer_use` tool) rather than writing complex custom Python scripts. Avoid over-engineering when simple tools exist.

### 3. Chinese Technical Communication

**User Preference**: The user is a Chinese technical user who prefers Chinese communication for desktop automation topics, especially when discussing interface elements, installation steps, and technical explanations.

## Complete QQ Automation Workflow (Corrected)

### Step-by-Step Process for Sending Messages

**Prerequisites**:
- QQ application running on Windows 10
- cua-driver 0.4.0 installed and configured
- Hermes Agent with `computer_use` toolset enabled
- macOS platform restrictions removed from Hermes code

**Workflow**:

```python
# 1. Capture current QQ interface
computer_use(action='capture', app='QQ', mode='ax', max_elements=150)

# 2. Click search box (consistently element #41 in our tests)
computer_use(action='click', element=41)

# 3. Clear any existing search text (if needed)
computer_use(action='key', keys='a')  # Select all
computer_use(action='key', keys='delete')  # Delete

# 4. Type contact name
computer_use(action='type', text='刘海建')

# 5. Press Enter to search
computer_use(action='key', keys='return')

# 6. Wait for search to complete and auto-enter chat (3 seconds recommended)
computer_use(action='wait', seconds=3)

# 7. Type message directly (no need to click input field - focus is already there)
computer_use(action='type', text='晚上好，这是agent测试消息')

# 8. Press Enter to send
computer_use(action='key', keys='return')

# 9. Verify message sent (optional - capture chat interface)
computer_use(action='capture', app='QQ', mode='ax', max_elements=150)
```

## Critical Do's and Don'ts

### ✅ DO:
- **Use direct `computer_use` commands**: Through Hermes Agent interface
- **Search and auto-enter**: Let QQ handle the transition from search to chat
- **Wait after search**: 2-3 seconds for interface to stabilize
- **Type messages directly**: After search completes, focus is already in chat input
- **Use Chinese for technical terms**: Especially for QQ interface elements

### ❌ DON'T:
- **Don't click search result buttons**: This opens profile cards, not chat windows
- **Don't press ESC**: This exits QQ interface entirely
- **Don't write custom Python scripts**: When `computer_use` tools exist
- **Don't over-engineer**: Use simplest possible approach

## Technical Insights from This Session

### Element Consistency
- **Search box**: Consistently element #41 across sessions
- **Search results**: ListItem elements (not Buttons) for direct chat entry
- **Chat input field**: Automatically focused after search completes

### Timing Considerations
- **Search delay**: 2-3 seconds needed for results to appear
- **Auto-transition**: Additional 1-2 seconds for chat interface to load
- **Typing speed**: 30ms delay between characters works reliably

### Error Handling
- **If search fails**: Check if contact is in friend list
- **If no auto-transition**: May need to press Enter again after search
- **If element not found**: Re-capture with different mode or increased max_elements

## User Communication Preferences

### Language Preference
- **Primary**: Chinese for technical communication
- **Secondary**: English for code examples and commands
- **Interface terms**: Use Chinese terms for QQ elements (e.g., "搜索框", "聊天界面")

### Communication Style
- **Direct and practical**: Focus on working solutions, not theoretical explanations
- **Immediate demonstrations**: Show working examples first
- **Proactive correction**: When users correct approach, incorporate immediately

## Successfully Tested Contacts

During this session, we successfully tested QQ automation with:

1. **刘海建** - Test contact for workflow correction verification
   - Message sent: "晚上好，这是agent测试消息"
   - Status: ✅ Successfully sent and verified

2. **Previous session contacts** (May 31, 2026):
   - **AI数字人** - Initial test contact
   - **朱智聪** - Real-world contact with company affiliation

## Updated Best Practices

1. **Simplicity over complexity**: Direct tool usage > custom scripts
2. **User workflow respect**: Follow QQ's natural flow (search → auto-enter chat)
3. **Minimal interaction**: Fewer clicks = fewer failure points
4. **Timing awareness**: Appropriate waits for UI transitions
5. **Language alignment**: Match user's preferred technical language

## Implementation Status

**Windows QQ Automation**: ✅ **Fully Functional**
- cua-driver 0.4.0 working on Windows 10
- Hermes `computer_use` toolset enabled
- Complete message sending workflow verified
- User workflow corrections incorporated

**Key Achievement**: Successfully incorporated user corrections into automation workflow, making it simpler, more reliable, and aligned with user preferences.