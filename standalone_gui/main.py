"""Entry point for DeDRM Standalone GUI application."""
import sys
import os
import warnings

warnings.filterwarnings('ignore')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from standalone_gui import compat  # noqa: F401 — bootstrap DeDRM imports
from standalone_gui.app_config import AppConfig
from standalone_gui.main_window import MainWindow


def main():
    args = sys.argv[1:]
    config_path = None
    headless = False

    # Parse CLI arguments
    i = 0
    while i < len(args):
        if args[i] == '--config' and i + 1 < len(args):
            i += 1
            config_path = args[i]
        elif args[i] == '--headless':
            headless = True
        i += 1

    # Load configuration
    cfg = AppConfig(config_path)
    cfg.ensure_configured()

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow(cfg, headless=headless)

    if headless:
        print('Headless mode: GUI initialized but not shown.')
        print('Use the decrypt_worker directly for CLI decryption.')
        return 0

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
