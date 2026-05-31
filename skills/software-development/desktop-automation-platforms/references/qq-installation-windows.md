# QQ Installation Guide for Windows Automation Testing
## 2026-05-31

## Overview
This guide documents the process of installing QQ on Windows for desktop automation testing with cua-driver and Hermes Agent.

## Why Install QQ for Testing?
QQ is an ideal test application for Windows desktop automation because:
1. **Complex UI**: Multiple windows, input fields, buttons, menus
2. **Real-world use case**: Messaging application with common UI patterns
3. **Chinese interface**: Good test for Chinese language UI automation
4. **Widely available**: Free download with no registration required for basic testing

## Installation Methods

### Method 1: Official Website (Recommended)
1. **Visit**: https://im.qq.com/pcqq/
2. **Download**: Click the green "立即下载" button
3. **File**: `QQSetup.exe` (approximately 100MB)
4. **Run installer**: Accept all default settings
5. **Launch**: After installation, QQ will start automatically

### Method 2: Direct Download Links
- **Latest version**: https://dldir1.qq.com/qqfile/qq/QQNT/QQ_9.9.13.22312.exe
- **Alternative mirror**: Search "QQ下载" on Baidu for alternative sources
- **Version archive**: Older versions available at https://dldir1.qq.com/qqfile/qq/

### Method 3: Chocolatey (Package Manager)
```powershell
# Install Chocolatey first (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install QQ
choco install qq -y
```

## Installation Verification

### Command Line Verification
```bash
# Check if QQ process is running
tasklist | findstr /i "qq.exe"

# Expected output if running:
# QQ.exe                     12345 Console                    1     45,432 K

# Check installation directory
dir "C:\Program Files (x86)\Tencent\QQ\bin\QQ.exe" /s

# Check registry installation
reg query "HKLM\SOFTWARE\Tencent\QQ" /v Install
```

### File System Verification
Typical installation locations:
```
C:\Program Files (x86)\Tencent\QQ\bin\QQ.exe
C:\Users\<username>\AppData\Local\Tencent\QQ\
```

### Automation Readiness Check
```bash
# List windows to find QQ
cua-driver list_windows | grep -i "qq\|腾讯"

# Expected output example:
# {"pid": 5160, "window_id": 264124, "title": "QQ", "x": 100, "y": 100, "width": 800, "height": 600}
```

## Post-Installation Configuration

### Disable Automatic Updates (for stable testing)
1. Open QQ settings (右下角菜单 → 设置)
2. Go to "基本设置" → "软件更新"
3. Select "不检查更新"

### Configure for Automation Testing
1. **Keep window visible**: Don't minimize to system tray
2. **Disable notifications**: Reduce popup interference
3. **Login with test account**: Or use without login for basic UI testing

## Troubleshooting Installation Issues

### Issue: Installer won't run
**Solutions**:
1. Right-click → "Run as administrator"
2. Disable antivirus temporarily (false positives common)
3. Download fresh copy from official site

### Issue: QQ starts but no main window
**Solutions**:
1. Check system tray (右下角) for QQ icon
2. Double-click tray icon to show main window
3. Use shortcut: Ctrl+Alt+Z to toggle window

### Issue: cua-driver can't find QQ window
**Solutions**:
1. Ensure QQ main window is visible (not minimized)
2. Check window title with: `cua-driver list_windows`
3. Restart QQ if window title is missing

## Automation Test Script

```python
#!/usr/bin/env python3
"""
Basic QQ automation test after installation
"""

import subprocess
import json
import time

def check_qq_installation():
    """Verify QQ is installed and running"""
    # Method 1: Check process
    result = subprocess.run(
        ["tasklist", "/fi", "imagename eq QQ.exe"],
        capture_output=True,
        text=True
    )
    
    if "QQ.exe" in result.stdout:
        print("✅ QQ is running")
        return True
    
    # Method 2: Check installation directory
    import os
    common_paths = [
        r"C:\Program Files (x86)\Tencent\QQ\bin\QQ.exe",
        r"C:\Program Files\Tencent\QQ\bin\QQ.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            print(f"✅ QQ installed at: {path}")
            return True
    
    print("❌ QQ not found")
    return False

def launch_qq():
    """Launch QQ if not running"""
    subprocess.Popen([
        r"C:\Program Files (x86)\Tencent\QQ\bin\QQ.exe"
    ], shell=True)
    time.sleep(5)  # Wait for startup
    
def test_qq_automation():
    """Test basic QQ control with cua-driver"""
    # Find QQ window
    result = subprocess.run(
        ["cua-driver", "list_windows"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        windows = json.loads(result.stdout)
        for window in windows.get("_legacy_windows", []):
            if "qq" in window.get("title", "").lower():
                print(f"✅ Found QQ window: {window['title']}")
                print(f"   PID: {window['pid']}, Window ID: {window['window_id']}")
                return window
    
    print("❌ No QQ window found")
    return None

if __name__ == "__main__":
    print("QQ Installation Verification Script")
    print("=" * 40)
    
    if check_qq_installation():
        qq_window = test_qq_automation()
        if qq_window:
            print("\n✅ QQ is ready for automation testing!")
            print(f"Use PID: {qq_window['pid']}, Window ID: {qq_window['window_id']}")
        else:
            print("\n⚠️  QQ is installed but not visible")
            print("Try launching QQ and ensuring main window is visible")
    else:
        print("\n❌ QQ not installed or not running")
        print("Please install QQ from: https://im.qq.com/pcqq/")
```

## Best Practices for Automation Testing

1. **Use a test account** or skip login for UI testing only
2. **Disable popups** in QQ settings
3. **Keep window maximized** for consistent element positions
4. **Document element coordinates** for reliable automation
5. **Create UI map** of important elements (input field, send button, etc.)

## Resources
- Official QQ download: https://im.qq.com/pcqq/
- QQ support forum: https://kf.qq.com/
- cua-driver documentation: https://github.com/trycua/cua

## Notes
- QQ interface may change with updates
- Element IDs and coordinates may vary
- Always test automation scripts after QQ updates
- Consider using relative coordinates or element trees instead of absolute positions