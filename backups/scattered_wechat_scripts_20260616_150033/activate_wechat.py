import ctypes
import time

def activate_wechat_window():
    """激活微信窗口"""
    print("正在尝试激活微信窗口...")
    
    # 尝试通过窗口标题查找微信窗口
    user32 = ctypes.windll.user32
    
    # 微信窗口可能的标题
    wechat_titles = ["微信", "WeChat"]
    
    for title in wechat_titles:
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            print(f"找到微信窗口: {title}")
            
            # 激活窗口
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE = 9
            user32.SetForegroundWindow(hwnd)
            
            # 等待窗口激活
            time.sleep(1)
            
            print("微信窗口已激活！")
            return True
    
    print("未找到微信窗口，尝试通过进程激活...")
    
    # 如果没找到，尝试通过进程激活
    import subprocess
    try:
        # 使用PowerShell激活窗口
        ps_command = """
        Add-Type @'
        using System;
        using System.Runtime.InteropServices;
        public class Win32 {
            [DllImport("user32.dll")]
            public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
            [DllImport("user32.dll")]
            public static extern bool SetForegroundWindow(IntPtr hWnd);
            [DllImport("user32.dll")]
            public static extern IntPtr FindWindow(string className, string windowName);
        }
        '@
        
        $hwnd = [Win32]::FindWindow($null, "微信")
        if ($hwnd -ne [IntPtr]::Zero) {
            [Win32]::ShowWindow($hwnd, 9)
            [Win32]::SetForegroundWindow($hwnd)
            "微信窗口已激活"
        } else {
            "未找到微信窗口"
        }
        """
        
        result = subprocess.run(["powershell", "-Command", ps_command], 
                              capture_output=True, text=True, timeout=5)
        if "微信窗口已激活" in result.stdout:
            print("通过PowerShell激活微信窗口成功！")
            time.sleep(2)
            return True
        else:
            print(f"PowerShell激活失败: {result.stdout}")
            return False
            
    except Exception as e:
        print(f"激活窗口时出错: {e}")
        return False

def main():
    print("=== 激活微信窗口 ===")
    if activate_wechat_window():
        print("\n✅ 微信窗口激活成功！")
        print("请现在发送Ctrl+F快捷键进行搜索...")
    else:
        print("\n❌ 微信窗口激活失败")
        print("请手动检查微信是否已打开")

if __name__ == "__main__":
    main()