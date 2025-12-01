from __future__ import annotations

import logging
import tkinter as tk

from core.app_context import create_app_context
from gui.main_window import PriceCheckerGUI


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    ctx = create_app_context()

    root = tk.Tk()
    _app = PriceCheckerGUI(root, ctx)  # noqa: F841 - app runs via mainloop
    root.mainloop()


if __name__ == "__main__":
    main()
