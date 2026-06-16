import time
import uiautomation as auto

def find_wechat_input():
    """查找微信搜索输入框"""
    print("查找微信窗口和输入框...")
    
    # 查找微信窗口
    wechat_window = auto.WindowControl(searchDepth=1, ClassName='WeChatMainWndForPC')
    if not wechat_window.Exists(3):
        print("未找到微信主窗口，尝试其他类名...")
        wechat_window = auto.WindowControl(searchDepth=1, Name='微信')
    
    if wechat_window.Exists(3):
        print("✅ 找到微信窗口")
        
        # 激活窗口
        wechat_window.SetFocus()
        wechat_window.SetActive()
        time.sleep(1)
        
        # 发送Ctrl+F
        print("发送Ctrl+F...")
        wechat_window.SendKeys('{Ctrl}f')
        time.sleep(2)
        
        # 查找搜索输入框
        print("查找搜索输入框...")
        
        # 微信搜索输入框可能是EditControl
        search_input = wechat_window.EditControl(searchDepth=3)
        
        if search_input.Exists(3):
            print("✅ 找到搜索输入框")
            
            # 点击输入框
            search_input.Click()
            time.sleep(0.5)
            
            # 清空并输入
            search_input.SendKeys('{Ctrl}a{DEL}')
            time.sleep(0.5)
            
            return search_input
        else:
            print("❌ 未找到搜索输入框")
            return None
    else:
        print("❌ 未找到微信窗口")
        return None

def main():
    print("=== 使用UI Automation操作微信 ===")
    
    # 查找并准备输入框
    search_input = find_wechat_input()
    
    if search_input:
        # 输入搜索词
        search_text = "AI 数字人"
        print(f"输入搜索词: {search_text}")
        
        # 方法1: 使用SendKeys
        search_input.SendKeys(search_text)
        time.sleep(2)
        
        print("✅ 搜索词已输入")
        
        # 按回车选择第一个结果
        print("按回车选择第一个结果...")
        search_input.SendKeys('{Enter}')
        time.sleep(2)
        
        # 查找聊天输入框
        print("查找聊天输入框...")
        
        # 聊天输入框可能是另一个EditControl
        chat_window = auto.WindowControl(searchDepth=1, Name='微信')
        chat_input = chat_window.EditControl(searchDepth=5)
        
        if chat_input.Exists(3):
            print("✅ 找到聊天输入框")
            
            # 输入测试消息
            test_message = "这是使用UI Automation发送的测试消息，请确认是否收到。"
            print(f"输入测试消息: {test_message}")
            
            chat_input.SendKeys(test_message)
            time.sleep(1)
            
            # 发送消息
            print("发送消息...")
            chat_input.SendKeys('{Enter}')
            time.sleep(1)
            
            print("🎉 消息已发送！请检查微信。")
        else:
            print("❌ 未找到聊天输入框")
    else:
        print("❌ 无法找到输入框")

if __name__ == "__main__":
    main()