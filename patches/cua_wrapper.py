#!/usr/bin/env python3
"""
cua-driver Windows 连接包装器。

由于 Hermes 的 MCP 连接在 Windows 上有问题，
这个脚本通过 subprocess 直接调用 cua-driver call 命令。
"""

import json
import subprocess
import sys
import os

def call_cua_driver(tool_name: str, args: dict) -> dict:
    """调用 cua-driver call 命令"""
    cmd = ["cua-driver", "call", tool_name]
    
    # 添加参数
    if args:
        cmd.extend(["--args", json.dumps(args)])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": result.stderr or f"Command failed with exit code {result.returncode}"}
    
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON output: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}

def main():
    """测试函数"""
    if len(sys.argv) > 1:
        tool = sys.argv[1]
        args_str = sys.argv[2] if len(sys.argv) > 2 else "{}"
        
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {}
        
        result = call_cua_driver(tool, args)
        print(json.dumps(result, indent=2))
        return
    
    # 测试一些基本功能
    print("Testing cua-driver connection...")
    
    # 测试 1: 获取光标位置
    print("\n1. Testing get_cursor_position:")
    result = call_cua_driver("get_cursor_position", {})
    print(json.dumps(result, indent=2))
    
    # 测试 2: 获取屏幕大小
    print("\n2. Testing get_screen_size:")
    result = call_cua_driver("get_screen_size", {})
    print(json.dumps(result, indent=2))
    
    # 测试 3: 列出应用
    print("\n3. Testing list_apps:")
    result = call_cua_driver("list_apps", {})
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()