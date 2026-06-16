"""Verify that the real WeChat window can be found and restored."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wechat_window import describe_window, find_wechat_window, get_window_info, restore_and_focus


def main() -> int:
    print("=" * 60)
    print("Hermes WeChat window verification")
    print("=" * 60)
    window = find_wechat_window(wake=True, retries=2)
    if not window:
        print("NOT_FOUND: real WeChat process window was not detected")
        return 1

    print("FOUND:", describe_window(window))
    ok = restore_and_focus(window["hwnd"])
    time.sleep(0.5)
    after = get_window_info(window["hwnd"])
    print("AFTER:", describe_window(after))
    print(f"RESTORE_OK={ok}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
