import tkinter as tk
from tkinter import ttk

from fh6_scanner.app import ForzaScannerGUI


def main():
    root = tk.Tk()

    try:
        style = ttk.Style()
        style.theme_use("clam")
    except Exception:
        pass

    ForzaScannerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()