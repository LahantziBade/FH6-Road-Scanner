import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Tuple

import cv2
import numpy as np

from .constants import OUT_DIR, TEMPLATE_PATH
from .platform_utils import beep, move_mouse
from .screen_utils import ScreenGrabber, diff_score


Region = Tuple[int, int, int, int]


@dataclass
class ScanParams:
    scan_region: Region
    detect_region: Region
    step_x: int
    step_y: int
    move_delay: float
    diff_threshold: float
    start_delay: float
    stop_on_hit: bool


def run_scan(
    params: ScanParams,
    stop_checker: Callable[[], bool],
    log: Callable[[str], None],
    status: Callable[[str], None],
    progress: Callable[[float], None],
):
    """
    执行地图扫描。
    这里不直接操作 Tkinter，只通过 callback 把日志、状态、进度传回 GUI。
    """
    try:
        os.makedirs(OUT_DIR, exist_ok=True)

        grabber = ScreenGrabber()
        template = cv2.imread(TEMPLATE_PATH)

        if template is None:
            log("模板读取失败，请重新截取模板。")
            return

        scan_x, scan_y, scan_w, scan_h = params.scan_region
        detect_region = params.detect_region

        x0 = scan_x
        y0 = scan_y
        x1 = scan_x + scan_w
        y1 = scan_y + scan_h

        total_rows = max(1, int((y1 - y0) / params.step_y) + 1)

        log("扫描即将开始。")
        log(f"请在 {params.start_delay:.1f} 秒内切回游戏地图，不要移动鼠标。")

        for i in range(int(params.start_delay), 0, -1):
            if stop_checker():
                log("扫描已停止。")
                return

            status(f"{i} 秒后开始扫描……")
            time.sleep(1)

        # 自动校准一次基础差异
        base_scores = []
        for _ in range(8):
            if stop_checker():
                log("扫描已停止。")
                return

            current = grabber.grab_region(detect_region)
            base_scores.append(diff_score(current, template))
            time.sleep(0.03)

        base_diff = float(np.mean(base_scores))
        diff_threshold = max(params.diff_threshold, base_diff + 8)

        log(f"当前稳定差异分数：{base_diff:.2f}")
        log(f"本次消失判定阈值：{diff_threshold:.2f}")
        log("开始逐行扫描……")

        row_index = 0
        y = y0

        while y <= y1:
            if stop_checker():
                log("扫描已停止。")
                return

            if row_index % 2 == 0:
                xs = range(x0, x1 + 1, params.step_x)
            else:
                xs = range(x1, x0 - 1, -params.step_x)

            for x in xs:
                if stop_checker():
                    log("扫描已停止。")
                    return

                move_mouse(x, y)
                time.sleep(params.move_delay)

                current = grabber.grab_region(detect_region)
                score = diff_score(current, template)

                status(f"扫描中：x={x}, y={y}, 差异={score:.2f}")

                if score > diff_threshold:
                    move_mouse(x, y)

                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    full_path = os.path.join(OUT_DIR, f"hit_{ts}_x{x}_y{y}.png")
                    crop_path = os.path.join(OUT_DIR, f"hit_crop_{ts}_x{x}_y{y}.png")

                    full_img = grabber.grab_full()
                    crop_img = grabber.grab_region(detect_region)

                    cv2.imwrite(full_path, full_img)
                    cv2.imwrite(crop_path, crop_img)

                    log("发现疑似未探索道路！")
                    log(f"鼠标位置：x={x}, y={y}")
                    log(f"差异分数：{score:.2f}")
                    log(f"完整截图：{full_path}")
                    log(f"检测区域截图：{crop_path}")
                    status(f"命中：x={x}, y={y}")

                    beep()

                    if params.stop_on_hit:
                        return

            row_index += 1
            progress(row_index / total_rows * 100)
            y += params.step_y

        progress(100)
        log("当前扫描区域已扫完，没有发现疑似点。")
        status("扫描完成")

    except Exception as e:
        log(f"扫描出错：{e}")
        status("扫描出错")