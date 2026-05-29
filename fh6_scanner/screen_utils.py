import cv2
import mss
import numpy as np


def diff_score(region_bgr, template_bgr):
    """
    分数越小：越接近模板，说明 X 快速移动还在。
    分数越大：越不像模板，说明 X 快速移动可能消失了。
    """
    if region_bgr.shape != template_bgr.shape:
        region_bgr = cv2.resize(
            region_bgr,
            (template_bgr.shape[1], template_bgr.shape[0])
        )

    diff = cv2.absdiff(region_bgr, template_bgr)
    return float(np.mean(diff))


class ScreenGrabber:
    def __init__(self):
        self.sct = mss.mss()

    def grab_region(self, region):
        x, y, w, h = map(int, region)

        img = np.array(self.sct.grab({
            "left": x,
            "top": y,
            "width": w,
            "height": h
        }))

        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def grab_full(self):
        monitor = self.sct.monitors[0]
        img = np.array(self.sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)