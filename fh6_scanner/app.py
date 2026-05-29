import os
import json
import queue
import threading
import webbrowser
from datetime import datetime

import cv2
import tkinter as tk
from tkinter import ttk, messagebox

from .constants import (
    AUTHOR_HOME_URL,
    AUTHOR_NAME,
    AUTHOR_UID,
    CONFIG_PATH,
    OUT_DIR,
    STOP_HOTKEY_VK,
    TEMPLATE_PATH,
)
from .platform_utils import get_screen_size, is_key_down
from .screen_utils import ScreenGrabber, diff_score
from .scanner import ScanParams, run_scan

class ForzaScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("地平线道路扫描器")
        self.root.geometry("780x780")
        self.root.minsize(760, 620)

        self.stop_event = threading.Event()
        self.worker_thread = None
        self.msg_queue = queue.Queue()

        self.screen_w, self.screen_h = get_screen_size()

        self.vars = {}
        self.create_widgets()

        self.log("本软件完全免费，请勿用于售卖或倒卖。")
        self.load_config()

        self.root.after(100, self.process_queue)

    # =========================
    # UI
    # =========================

    def create_widgets(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        # 顶部标题 + 作者信息
        header_frame = ttk.Frame(main)
        header_frame.pack(fill="x", pady=(0, 12))

        left_header = ttk.Frame(header_frame)
        left_header.pack(side="left", anchor="nw")

        title = ttk.Label(
            left_header,
            text="地平线道路扫描器",
            font=("Microsoft YaHei UI", 18, "bold")
        )
        title.pack(anchor="w")

        subtitle = ttk.Label(
            left_header,
            text="利用左下角“X 快速移动”是否消失，逐行扫描未探索道路。扫描中按 F8 可停止。",
            foreground="#666666"
        )
        subtitle.pack(anchor="w", pady=(2, 0))

        author_frame = ttk.Frame(header_frame)
        author_frame.pack(side="right", anchor="ne", padx=(12, 0))

        ttk.Label(
            author_frame,
            text="作者B站：",
            justify="right",
            foreground="#444444",
            font=("Microsoft YaHei UI", 9)
        ).pack(anchor="e")

        author_link = tk.Label(
            author_frame,
            text=AUTHOR_NAME,
            justify="right",
            fg="#1E6BD6",
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "underline")
        )
        author_link.pack(anchor="e")
        author_link.bind("<Button-1>", self.open_author_home)
        author_link.bind("<Button-3>", self.copy_author_name)

        uid_link = tk.Label(
            author_frame,
            text=f"uid: {AUTHOR_UID}",
            justify="right",
            fg="#1E6BD6",
            cursor="hand2",
            font=("Microsoft YaHei UI", 9)
        )
        uid_link.pack(anchor="e")
        uid_link.bind("<Button-1>", self.open_author_home)
        uid_link.bind("<Button-3>", self.copy_author_name)

        # 屏幕信息
        info_frame = ttk.Frame(main)
        info_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(
            info_frame,
            text=f"当前屏幕：{self.screen_w} × {self.screen_h}"
        ).pack(side="left")

        ttk.Button(
            info_frame,
            text="恢复默认区域",
            command=self.set_default_values
        ).pack(side="right")

        # 扫描区域
        scan_group = ttk.LabelFrame(main, text="扫描区域")
        scan_group.pack(fill="x", pady=6)

        self.add_region_inputs(
            scan_group,
            prefix="scan",
            labels=("X 起点", "Y 起点", "宽度", "高度")
        )

        # 检测区域
        detect_group = ttk.LabelFrame(main, text="左下角【X 快速移动】检测区域")
        detect_group.pack(fill="x", pady=6)

        self.add_region_inputs(
            detect_group,
            prefix="detect",
            labels=("X 起点", "Y 起点", "宽度", "高度")
        )

        detect_btn_frame = ttk.Frame(detect_group)
        detect_btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(
            detect_btn_frame,
            text="截取/更新模板",
            command=self.capture_template
        ).pack(side="left")

        ttk.Button(
            detect_btn_frame,
            text="测试当前差异分数",
            command=self.test_diff_score
        ).pack(side="left", padx=8)

        ttk.Label(
            detect_btn_frame,
            text=f"模板文件：{TEMPLATE_PATH}",
            foreground="#666666"
        ).pack(side="left", padx=8)

        # 参数区域
        param_group = ttk.LabelFrame(main, text="扫描参数")
        param_group.pack(fill="x", pady=6)

        param_grid = ttk.Frame(param_group)
        param_grid.pack(fill="x", padx=10, pady=10)

        self.add_param_input(param_grid, "step_x", "横向步长", 0, 0, default="20")
        self.add_param_input(param_grid, "step_y", "纵向步长", 0, 1, default="20")
        self.add_param_input(param_grid, "move_delay", "移动延迟", 0, 2, default="0.006")

        self.add_param_input(param_grid, "diff_threshold", "差异阈值", 1, 0, default="14")
        self.add_param_input(param_grid, "start_delay", "开始延迟", 1, 1, default="5")

        self.stop_on_hit_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            param_grid,
            text="命中后停止",
            variable=self.stop_on_hit_var
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.auto_save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            param_grid,
            text="开始扫描前自动保存配置",
            variable=self.auto_save_var
        ).grid(row=2, column=2, columnspan=4, sticky="w", pady=(8, 0))

        # 操作按钮
        action_frame = ttk.Frame(main)
        action_frame.pack(fill="x", pady=10)

        self.start_btn = ttk.Button(
            action_frame,
            text="开始扫描",
            command=self.start_scan
        )
        self.start_btn.pack(side="left", ipadx=16, ipady=4)

        self.stop_btn = ttk.Button(
            action_frame,
            text="停止扫描（F8）",
            command=self.stop_scan,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=8, ipadx=16, ipady=4)

        ttk.Button(
            action_frame,
            text="保存配置",
            command=self.save_config
        ).pack(side="left", padx=8)

        ttk.Button(
            action_frame,
            text="打开截图文件夹",
            command=self.open_hit_folder
        ).pack(side="right")

        # 进度条
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(
            main,
            variable=self.progress_var,
            maximum=100
        )
        self.progress.pack(fill="x", pady=(4, 8))

        # 状态
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(
            main,
            textvariable=self.status_var,
            foreground="#333333"
        )
        status_label.pack(anchor="w", pady=(0, 6))

        # 日志
        log_group = ttk.LabelFrame(main, text="运行日志")
        log_group.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_group,
            height=10,
            wrap="word",
            font=("Consolas", 10)
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            log_group,
            orient="vertical",
            command=self.log_text.yview
        )
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def add_region_inputs(self, parent, prefix, labels):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", padx=10, pady=10)

        keys = ["x", "y", "w", "h"]

        for i, label in enumerate(labels):
            ttk.Label(frame, text=label).grid(
                row=0,
                column=i * 2,
                sticky="e",
                padx=(0, 4)
            )

            var_name = f"{prefix}_{keys[i]}"
            self.vars[var_name] = tk.StringVar()

            entry = ttk.Entry(frame, textvariable=self.vars[var_name], width=10)
            entry.grid(
                row=0,
                column=i * 2 + 1,
                sticky="w",
                padx=(0, 14)
            )

    def add_param_input(self, parent, key, label, row, col, default):
        ttk.Label(parent, text=label).grid(
            row=row,
            column=col * 2,
            sticky="e",
            padx=(0, 4),
            pady=4
        )

        self.vars[key] = tk.StringVar(value=default)

        entry = ttk.Entry(parent, textvariable=self.vars[key], width=10)
        entry.grid(
            row=row,
            column=col * 2 + 1,
            sticky="w",
            padx=(0, 24),
            pady=4
        )

    # =========================
    # 配置
    # =========================

    def set_default_values(self):
        self.vars["scan_x"].set(str(int(self.screen_w * 0.01)))
        self.vars["scan_y"].set(str(int(self.screen_h * 0.01)))
        self.vars["scan_w"].set(str(int(self.screen_w * 0.98)))
        self.vars["scan_h"].set(str(int(self.screen_h * 0.84)))

        self.vars["detect_x"].set(str(int(self.screen_w * 0.215)))
        self.vars["detect_y"].set(str(int(self.screen_h * 0.895)))
        self.vars["detect_w"].set(str(int(self.screen_w * 0.125)))
        self.vars["detect_h"].set(str(int(self.screen_h * 0.065)))

        self.vars["step_x"].set("20")
        self.vars["step_y"].set("20")
        self.vars["move_delay"].set("0.006")
        self.vars["diff_threshold"].set("14")
        self.vars["start_delay"].set("5")

        self.log("已恢复默认区域。")

    def load_config(self):
        if not os.path.exists(CONFIG_PATH):
            self.set_default_values()
            self.log("未找到配置文件，已使用默认配置。")
            return

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            saved_w = int(data.get("screen_w", 0))
            saved_h = int(data.get("screen_h", 0))

            if saved_w and saved_h and (saved_w != self.screen_w or saved_h != self.screen_h):
                self.set_default_values()
                self.log(
                    f"检测到屏幕分辨率变化：配置为 {saved_w}×{saved_h}，当前为 {self.screen_w}×{self.screen_h}，已自动恢复默认区域。"
                )

                # 保留扫描参数，不保留坐标区域
                for key in ["step_x", "step_y", "move_delay", "diff_threshold", "start_delay"]:
                    if key in data:
                        self.vars[key].set(str(data[key]))

            else:
                for key, var in self.vars.items():
                    if key in data:
                        var.set(str(data[key]))

            self.stop_on_hit_var.set(bool(data.get("stop_on_hit", True)))
            self.auto_save_var.set(bool(data.get("auto_save", True)))

            self.log(f"已读取配置：{CONFIG_PATH}")

        except Exception as e:
            self.set_default_values()
            self.log(f"读取配置失败，已使用默认配置：{e}")

    def save_config(self):
        data = {}

        data["screen_w"] = self.screen_w
        data["screen_h"] = self.screen_h

        for key, var in self.vars.items():
            data[key] = var.get()

        data["stop_on_hit"] = self.stop_on_hit_var.get()
        data["auto_save"] = self.auto_save_var.get()

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.log(f"配置已保存：{CONFIG_PATH}")

        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    # =========================
    # 参数读取
    # =========================

    def get_int(self, key):
        return int(float(self.vars[key].get().strip()))

    def get_float(self, key):
        return float(self.vars[key].get().strip())

    def get_region(self, prefix):
        return (
            self.get_int(f"{prefix}_x"),
            self.get_int(f"{prefix}_y"),
            self.get_int(f"{prefix}_w"),
            self.get_int(f"{prefix}_h"),
        )

    def get_params(self):
        return {
            "scan_region": self.get_region("scan"),
            "detect_region": self.get_region("detect"),
            "step_x": self.get_int("step_x"),
            "step_y": self.get_int("step_y"),
            "move_delay": self.get_float("move_delay"),
            "diff_threshold": self.get_float("diff_threshold"),
            "start_delay": self.get_float("start_delay"),
            "stop_on_hit": self.stop_on_hit_var.get(),
        }

    # =========================
    # 模板相关
    # =========================

    def capture_template(self):
        try:
            detect_region = self.get_region("detect")
            grabber = ScreenGrabber()
            img = grabber.grab_region(detect_region)
            cv2.imwrite(TEMPLATE_PATH, img)

            self.log(f"已截取模板：{TEMPLATE_PATH}")
            messagebox.showinfo(
                "模板已保存",
                f"已保存 {TEMPLATE_PATH}\n\n建议打开看看是否准确截到了【X 快速移动】。"
            )

        except Exception as e:
            messagebox.showerror("截取失败", str(e))

    def test_diff_score(self):
        try:
            if not os.path.exists(TEMPLATE_PATH):
                messagebox.showwarning("缺少模板", "请先点击【截取/更新模板】。")
                return

            detect_region = self.get_region("detect")
            grabber = ScreenGrabber()

            template = cv2.imread(TEMPLATE_PATH)
            current = grabber.grab_region(detect_region)

            score = diff_score(current, template)
            self.log(f"当前差异分数：{score:.2f}")

            messagebox.showinfo(
                "测试结果",
                f"当前差异分数：{score:.2f}\n\n"
                f"如果鼠标在已探索道路上，这个分数应该比较低。"
            )

        except Exception as e:
            messagebox.showerror("测试失败", str(e))

    # =========================
    # 扫描控制
    # =========================

    def start_scan(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        try:
            params = self.get_params()
        except Exception as e:
            messagebox.showerror("参数错误", f"请检查输入框参数：\n{e}")
            return

        if not os.path.exists(TEMPLATE_PATH):
            messagebox.showwarning(
                "缺少模板",
                "请先把鼠标放到已探索道路上，确保左下角出现【X 快速移动】，然后点击【截取/更新模板】。"
            )
            return

        if self.auto_save_var.get():
            self.save_config()

        self.stop_event.clear()
        self.progress_var.set(0)

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        self.worker_thread = threading.Thread(
            target=self.scan_worker,
            args=(params,),
            daemon=True
        )
        self.worker_thread.start()

    def stop_scan(self):
        self.stop_event.set()
        self.log("正在请求停止扫描……")

    def should_stop_scan(self):
        """
        统一判断是否需要停止：
        1. 点击了 GUI 的停止按钮
        2. 按下了全局快捷键 F8
        """
        if self.stop_event.is_set():
            return True

        if is_key_down(STOP_HOTKEY_VK):
            self.stop_event.set()
            self.queue_log("检测到 F8 快捷键，正在停止扫描……")
            self.queue_status("正在停止扫描……")
            return True

        return False

    def scan_worker(self, params):
        scan_params = ScanParams(
            scan_region=params["scan_region"],
            detect_region=params["detect_region"],
            step_x=params["step_x"],
            step_y=params["step_y"],
            move_delay=params["move_delay"],
            diff_threshold=params["diff_threshold"],
            start_delay=params["start_delay"],
            stop_on_hit=params["stop_on_hit"],
        )

        try:
            run_scan(
                params=scan_params,
                stop_checker=self.should_stop_scan,
                log=self.queue_log,
                status=self.queue_status,
                progress=self.queue_progress,
            )
        finally:
            self.queue_done()

    # =========================
    # 队列更新 UI
    # =========================

    def queue_log(self, text):
        self.msg_queue.put(("log", text))

    def queue_status(self, text):
        self.msg_queue.put(("status", text))

    def queue_progress(self, value):
        self.msg_queue.put(("progress", value))

    def queue_done(self):
        self.msg_queue.put(("done", None))

    def process_queue(self):
        try:
            while True:
                msg_type, value = self.msg_queue.get_nowait()

                if msg_type == "log":
                    self.log(value)

                elif msg_type == "status":
                    self.status_var.set(value)

                elif msg_type == "progress":
                    self.progress_var.set(value)

                elif msg_type == "done":
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")

        except queue.Empty:
            pass

        self.root.after(100, self.process_queue)

    # =========================
    # 作者链接
    # =========================

    def open_author_home(self, event=None):
        webbrowser.open(AUTHOR_HOME_URL)

    def copy_author_name(self, event=None):
        self.root.clipboard_clear()
        self.root.clipboard_append(AUTHOR_NAME)
        self.log(f"已复制作者昵称：{AUTHOR_NAME}")

    # =========================
    # 其他
    # =========================

    def log(self, text):
        now = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{now}] {text}\n")
        self.log_text.see("end")

    def open_hit_folder(self):
        os.makedirs(OUT_DIR, exist_ok=True)
        os.startfile(os.path.abspath(OUT_DIR))


def main():
    root = tk.Tk()

    try:
        style = ttk.Style()
        style.theme_use("clam")
    except Exception:
        pass

    app = ForzaScannerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()