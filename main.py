# main.py

import logging

from core.app_context import create_app_context
from gui.main_window import run


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    ctx = create_app_context()
    run(ctx)


if __name__ == "__main__":
    main()
