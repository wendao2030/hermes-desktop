# User Verification Requirements for Desktop Automation
**Date**: June 2, 2026  
**Context**: WeChat automation testing and user feedback analysis  
**Key Insight**: Users require actual interface verification, not assumptions or inferences

## Critical User Feedback

### Direct Quotes from User

1. **关于界面验证的重要性**：
   > "你没打开界面你怎么截图的？你怎么知道有搜索按钮的？难道是推断的？"
   > Translation: "If you didn't open the interface, how did you take screenshots? How do you know there's a search button? Are you inferring?"

2. **关于工具行为一致性**：
   > "我是5.31号让你操作qq的，你是可以识别qq界面的按钮，应该是截图的吧，我的模型一直是deepseek"
   > Translation: "On May 31, I asked you to operate QQ, you could recognize QQ interface buttons, you should have taken screenshots, my model has always been deepseek"

3. **关于实时测试偏好**：
   > "要不你现在再测试一次qq发消息。你给AI数字人发一条测试消息"
   > Translation: "How about you test QQ messaging again now. Send a test message to AI数字人"

## User Expectations Analysis

### 1. **Operation Must Be Based on Actual Interface**
- **Expectation**: All actions must be verifiable through actual interface state
- **Rejection**: Inferred or assumed interface elements
- **Requirement**: Direct visual or text-based confirmation before action

### 2. **Consistency Across Sessions**
- **Expectation**: Tools should behave consistently over time
- **Observation**: User noted successful QQ operation on May 31
- **Requirement**: Similar capabilities should work for WeChat

### 3. **Real Testing Over Theoretical Explanations**
- **Preference**: Actual, verifiable tests
- **Rejection**: Abstract explanations or promises
- **Requirement**: Demonstrate capability through concrete actions

### 4. **Active Verification by Agent**
- **Expectation**: Agent should proactively verify operation results
- **Observation**: When user questioned "没有发送成功", agent should re-attempt
- **Requirement**: Tool call success (`ok: true`) ≠ operation success

## Impact on Desktop Automation Workflow

### Before (Problematic Approach)
1. Assume interface state based on previous sessions
2. Perform actions without current verification
3. Rely on tool call status as success indicator
4. Wait for user feedback when operations fail

### After (User-Preferred Approach)
1. **Always capture current interface state** before action
2. **Verify elements exist** in current capture
3. **Perform action** based on verified elements
4. **Re-capture to verify** action result (if vision supported)
5. **Ask user for confirmation** of successful operation
6. **Immediately re-attempt** if user reports failure

## Specific Implementation Requirements

### For Applications with Limited cua-driver Support (e.g., WeChat)
1. **Acknowledge limitation** upfront to user
2. **Use alternative verification methods**:
   - Keyboard shortcuts (user-confirmed `Ctrl+Alt+W`)
   - Process status checks (`tasklist | findstr -i wechat`)
   - User manual verification requests
3. **Document what works** for future reference

### For Model Vision Support Limitations
1. **Test vision capability** at session start
2. **Adapt workflow** based on actual capability:
   - Vision supported: Use `mode='som'` for visual verification
   - Vision not supported: Use `mode='ax'` + user verification
3. **Communicate limitations** clearly to user

## User's Technical Understanding Level

### Demonstrated Knowledge
1. **Tool operation mechanisms**: Understands how `computer_use` works
2. **Model capabilities**: Knows about vision support requirements
3. **Consistency tracking**: Monitors tool behavior across sessions
4. **Verification importance**: Values actual testing over promises

### Communication Style Preference
1. **Direct and specific**: Prefers concrete examples over abstract explanations
2. **Chinese technical terms**: Expects Chinese for interface descriptions
3. **Immediate correction**: Wants errors addressed immediately, not in future sessions
4. **Practical focus**: Values working solutions over theoretical perfection

## Best Practices Derived from User Feedback

### 1. **Never Assume Interface State**
- Always capture before action
- Never infer elements from memory or previous sessions
- Document current state for transparency

### 2. **Prioritize User Verification**
- Tool status ≠ operation success
- Always ask user to confirm critical operations
- Implement immediate re-attempt on failure reports

### 3. **Maintain Session Consistency**
- Document what worked in previous sessions
- Investigate inconsistencies immediately
- Update skills with verified patterns

### 4. **Prefer Real Testing**
- Demonstrate capability through actual tests
- Avoid theoretical "could work" explanations
- Use concrete examples from current session

### 5. **Communicate Limitations Proactively**
- Acknowledge when tools have limited support
- Explain verification alternatives
- Set realistic expectations based on testing

## Skill Development Implications

### Required Updates to Existing Skills
1. **`wechat-messaging`**: Add user verification requirements
2. **`desktop-automation-platforms`**: Document vision support limitations
3. **`qq-messaging`**: Reference successful patterns from May 31

### New Skill Considerations
1. **Model capability testing**: Skills for testing vision/function support
2. **User verification workflows**: Standardized verification request patterns
3. **Failure recovery patterns**: Immediate re-attempt procedures

## Verification Workflow Template

### For Each Operation
```python
# 1. Capture current state
result = computer_use(action='capture', mode='ax')

# 2. Verify target element exists
if not find_element(result['elements'], '搜索'):
    print("找不到搜索框，请确认微信界面已打开")
    return

# 3. Perform action
computer_use(action='click', element=search_box_idx)

# 4. Request user verification
print("已点击搜索框，请确认搜索框已获得焦点并可以输入")
```

### For Critical Operations (e.g., message sending)
```python
# 1. Complete all steps
# 2. Explicitly ask for verification
print("已完成消息发送操作，所有工具调用返回成功。")
print("请检查与[好友姓名]的微信聊天记录，确认是否收到了测试消息。")

# 3. Handle user response
# If user says "没有收到": re-attempt immediately
# If user says "收到了": record successful pattern
```

## Conclusion

The user has established clear expectations for desktop automation:
1. **Operations must be based on verifiable interface states**
2. **Consistency is expected across sessions and applications**
3. **Real testing is preferred over theoretical explanations**
4. **Active verification by the agent is required**

These preferences should be incorporated into all desktop automation skills and workflows to meet user expectations and ensure successful automation outcomes.