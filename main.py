# main.py
from core.logging_setup import setup_logging
from gui.main_window import run_app


if __name__ == "__main__":
    # Flip to debug=True when you want extra noisy logs.
    setup_logging(debug=False)
    run_app()
