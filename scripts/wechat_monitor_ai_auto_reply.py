# -*- coding: utf-8 -*-
"""
微信“AI 数字人”会话监控并自动回复（图像差异保守版）

用途：
- 只监控“AI 数字人”这个会话
- 每 30 秒检查一次
- 启动时只搜索一次进入目标会话，后续每轮只截图当前会话，不再频繁搜索
- 首次只建立基线，不回复
- 后续如果聊天记录区域截图发生明显变化，则自动回复一次：我现在不方便看微信，稍后回复你。
- 发送后立即重新截图并更新基线，避免自己的回复触发下一轮循环回复

重要修正（2026-06-11）：
- 不要每 30 秒都 Ctrl+F 搜索并输入“AI 数字人”；这会干扰用户，也容易造成焦点错乱。
- 监控应启动时/恢复时搜索一次进入目标会话，后续只截图当前聊天区。
- 监控触发后，不能直接粘贴回复；焦点可能仍在搜索框，导致回复粘到搜索框。
- 发送前必须明确点击微信右侧底部聊天输入框。
- 发送后增加冷却时间并更新基线，避免每 30 秒重复回复。
- Ctrl+V 后不能额外留下字母 V；所有组合键必须先按 Ctrl 后按 V，再先松 V 后松 Ctrl。

为什么不用 OCR：
- 当前环境 pytesseract 导入会触发 pandas/numpy 二进制兼容错误
- 系统 PATH 中未找到 tesseract.exe
- 因此采用截图差异检测。微信 UIA 不完整，无法稳定读取未读消息文本。

安全限制：
- 只在启动/恢复时搜索并进入“AI 数字人”第一个结果。
- 不读取、不保存聊天文本；只保存截图指纹和少量调试截图。
- 默认不处理群聊、链接、文件、支付、红包等任何内容。
"""

import ctypes
import ctypes.wintypes
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

import pyperclip
from PIL import Image, ImageChops, ImageGrab, ImageStat

TARGET = "AI 数字人"
REPLY_TEXT = "我现在不方便看微信，稍后回复你。"
INTERVAL_SECONDS = 30
DIFF_THRESHOLD = 0.10
REPLY_COOLDOWN_SECONDS = 300

BASE_DIR = Path(r"C:\Users\dtyao\AppData\Local\hermes\scripts")
STATE_FILE = BASE_DIR / "wechat_monitor_ai_state.json"
LOG_FILE = BASE_DIR / "wechat_monitor_ai_auto_reply.log"
SCREENSHOT_DIR = BASE_DIR / "wechat_monitor_shots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

user32 = ctypes.windll.user32
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_F = 0x46
VK_RETURN = 0x0D
VK_V = 0x56
VK_A = 0x41
VK_W = 0x57
SW_RESTORE = 9


def log(msg: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def key_down(vk):
    user32.keybd_event(vk, 0, 0, 0)


def key_up(vk):
    user32.keybd_event(vk, 0, 2, 0)


def press_key(vk, delay=0.08):
    key_down(vk)
    time.sleep(delay)
    key_up(vk)
    time.sleep(delay)


def hotkey(*vks, delay=0.08):
    for vk in vks:
        key_down(vk)
        time.sleep(delay)
    for vk in reversed(vks):
        key_up(vk)
        time.sleep(delay)


def paste_text(text: str):
    pyperclip.copy(text)
    time.sleep(0.25)
    hotkey(VK_CONTROL, VK_V)
    time.sleep(0.6)


def get_window_title(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def find_wechat_hwnd():
    for title in ("微信", "WeChat"):
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            return hwnd
    return 0


def activate_wechat():
    hwnd = find_wechat_hwnd()
    if not hwnd:
        log("未找到标题为微信的窗口，尝试 Ctrl+Alt+W 激活")
        hotkey(VK_CONTROL, VK_MENU, VK_W)
        time.sleep(2)
        hwnd = find_wechat_hwnd()
    if not hwnd:
        return 0

    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.2)
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)
    fg = user32.GetForegroundWindow()
    fg_title = get_window_title(fg)
    log(f"激活微信窗口: hwnd=0x{hwnd:X}, foreground='{fg_title}'")
    if fg != hwnd and ("微信" not in fg_title and "WeChat" not in fg_title):
        log(f"WARN: 微信未成为前台窗口，本轮跳过；foreground='{fg_title}'")
        return 0
    return hwnd


def get_wechat_rect():
    hwnd = find_wechat_hwnd()
    if not hwnd:
        return None
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    if rect.right <= rect.left or rect.bottom <= rect.top:
        return None
    return (rect.left, rect.top, rect.right, rect.bottom)


def click_abs(x: int, y: int):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.08)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.06)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.25)


def click_chat_input_box() -> bool:
    rect = get_wechat_rect()
    if not rect:
        log("ERROR: 无法获取微信窗口区域，不能点击输入框")
        return False
    left, top, right, bottom = rect
    w = right - left
    h = bottom - top
    x = left + int(w * 0.62)
    y = top + int(h * 0.88)
    log(f"点击聊天输入框坐标: ({x}, {y})")
    click_abs(x, y)
    return True


def search_and_enter_target_chat() -> bool:
    """只在启动/恢复时调用。不要每轮监控都搜索。"""
    hwnd = activate_wechat()
    if not hwnd:
        log("ERROR: 未找到/无法激活微信窗口")
        return False

    log(f"启动/恢复：搜索并进入目标会话: {TARGET}")
    hotkey(VK_CONTROL, VK_F)
    time.sleep(1.3)
    hotkey(VK_CONTROL, VK_A)
    time.sleep(0.15)
    paste_text(TARGET)
    time.sleep(2.2)
    press_key(VK_RETURN)
    time.sleep(2.8)
    click_chat_input_box()
    time.sleep(0.5)
    return True


def ensure_target_chat_ready(state: dict, loop: int) -> bool:
    """第一轮搜索进入目标会话；后续只激活微信，不再重复搜索。"""
    if not activate_wechat():
        return False

    if not state.get("target_chat_opened"):
        ok = search_and_enter_target_chat()
        if ok:
            state["target_chat_opened"] = True
            state["target_chat_opened_at"] = datetime.now().isoformat()
            save_state(state)
        return ok

    log("目标会话已在启动/恢复时打开；本轮不再搜索，只截图当前聊天区")
    return True


def crop_chat_area(full_img: Image.Image) -> Image.Image:
    w, h = full_img.size
    left = int(w * 0.28)
    top = int(h * 0.10)
    right = int(w * 0.98)
    bottom = int(h * 0.80)
    if right <= left or bottom <= top:
        return full_img
    return full_img.crop((left, top, right, bottom))


def image_signature(img: Image.Image) -> str:
    small = img.convert("L").resize((64, 64), Image.Resampling.LANCZOS)
    return hashlib.sha256(small.tobytes()).hexdigest()


def diff_score(img1_path: str, img2: Image.Image) -> float:
    try:
        img1 = Image.open(img1_path).convert("L").resize((64, 64), Image.Resampling.LANCZOS)
        img2s = img2.convert("L").resize((64, 64), Image.Resampling.LANCZOS)
        diff = ImageChops.difference(img1, img2s)
        return float(ImageStat.Stat(diff).mean[0])
    except Exception as e:
        log(f"计算差异失败，按有变化处理: {e}")
        return 999.0


def capture_chat_area():
    rect = get_wechat_rect()
    if not rect:
        return None, None
    full = ImageGrab.grab(bbox=rect)
    chat = crop_chat_area(full)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shot_path = SCREENSHOT_DIR / f"wechat_ai_chat_{ts}.png"
    chat.save(shot_path)
    return chat, str(shot_path)


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def iso_to_ts(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value).timestamp()
    except Exception:
        return 0.0


def in_reply_cooldown(state: dict) -> bool:
    last_replied_at = state.get("last_replied_at")
    if not last_replied_at:
        return False
    elapsed = time.time() - iso_to_ts(last_replied_at)
    if elapsed < REPLY_COOLDOWN_SECONDS:
        log(f"处于回复冷却期：距离上次回复 {elapsed:.0f}s < {REPLY_COOLDOWN_SECONDS}s，本轮只更新基线不回复")
        return True
    return False


def send_reply() -> bool:
    log(f"发送自动回复: {REPLY_TEXT}")
    if not click_chat_input_box():
        return False
    time.sleep(0.3)
    paste_text(REPLY_TEXT)
    time.sleep(0.8)
    press_key(VK_RETURN)
    time.sleep(2.0)
    return True


def update_baseline(state: dict, img: Image.Image, shot_path: str, reason: str):
    state.update({
        "target": TARGET,
        "last_signature": image_signature(img),
        "last_shot_path": shot_path,
        "last_seen_at": datetime.now().isoformat(),
        "mode": "image_diff_no_repeated_search",
        "baseline_reason": reason,
    })
    save_state(state)


def check_once(state: dict, loop: int):
    log(f"--- 第 {loop} 次检查开始 ---")
    if not ensure_target_chat_ready(state, loop):
        return state

    chat_img, shot_path = capture_chat_area()
    if chat_img is None:
        log("ERROR: 无法截图，跳过本轮")
        return state

    sig = image_signature(chat_img)
    last_shot = state.get("last_shot_path")
    last_sig = state.get("last_signature")
    log(f"聊天区域截图: {shot_path}")

    if not last_sig or not last_shot or not Path(last_shot).exists():
        update_baseline(state, chat_img, shot_path, "first_run")
        log("首次检查：仅建立基线，不自动回复")
        return state

    score = diff_score(last_shot, chat_img)
    changed = score >= DIFF_THRESHOLD and sig != last_sig
    log(f"聊天区域差异分数: {score:.2f}，阈值: {DIFF_THRESHOLD}，签名变化: {sig != last_sig}")

    if changed:
        log("检测到 AI 数字人会话聊天区域明显变化")
        if in_reply_cooldown(state):
            update_baseline(state, chat_img, shot_path, "changed_but_in_cooldown")
            return state

        log("准备回复")
        sent = send_reply()
        new_img, new_shot = capture_chat_area()
        if new_img is not None:
            update_baseline(state, new_img, new_shot, "after_reply" if sent else "after_failed_reply_attempt")
            if sent:
                state.update({
                    "last_replied_at": datetime.now().isoformat(),
                    "last_reply": REPLY_TEXT,
                })
                save_state(state)
                log(f"已回复并更新基线: {new_shot}")
            else:
                log(f"回复未确认发送，但已更新基线避免重复触发: {new_shot}")
        else:
            update_baseline(state, chat_img, shot_path, "fallback_after_reply_attempt")
            log("回复后二次截图失败；用回复前截图更新基线，避免重复触发")
    else:
        state["last_seen_at"] = datetime.now().isoformat()
        save_state(state)
        log("无明显变化，不回复")

    return state


def main():
    log("=== 微信 AI 数字人监控自动回复启动（图像差异版：启动搜索一次，后续不重复搜索）===")
    log(f"目标={TARGET}, 间隔={INTERVAL_SECONDS}s, 阈值={DIFF_THRESHOLD}, 冷却={REPLY_COOLDOWN_SECONDS}s, 回复='{REPLY_TEXT}'")
    state = load_state()
    # 每次脚本新启动时重新搜索一次目标会话；运行期间不再每轮搜索。
    state["target_chat_opened"] = False
    save_state(state)
    loop = 0
    while True:
        loop += 1
        try:
            state = check_once(state, loop)
        except KeyboardInterrupt:
            log("收到 KeyboardInterrupt，退出")
            break
        except Exception as e:
            log(f"ERROR: 本轮异常: {type(e).__name__}: {e}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
