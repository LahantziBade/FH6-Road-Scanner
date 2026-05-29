import ctypes

import pyautogui

try:
    import winsound
except ImportError:
    winsound = None


# Windows DPI 修正
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass


pyautogui.PAUSE = 0
pyautogui.MINIMUM_DURATION = 0
pyautogui.MINIMUM_SLEEP = 0


def get_screen_size():
    return pyautogui.size()


def is_key_down(vk_code):
    """
    检测全局按键状态。
    即使游戏窗口在前台，也能检测到。
    """
    try:
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)
    except Exception:
        return False


def move_mouse(x, y):
    """比 pyautogui.moveTo 更快的鼠标移动。"""
    ctypes.windll.user32.SetCursorPos(int(x), int(y))


def beep():
    if winsound:
        winsound.Beep(1200, 160)
        winsound.Beep(900, 160)
        winsound.Beep(1200, 160)
    else:
        print("\a")