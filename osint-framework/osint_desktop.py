#!/usr/bin/env python3
"""
OSINT Framework — Desktop Application Entry Point

Launch the premium investigation dashboard.
All recon modules use free, public data sources — no API keys required.
"""

import sys
import os
import logging
from datetime import datetime

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def setup_logging():
    """Configure logging for the desktop application."""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"osint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("OSINT Framework starting...")
    return logger


def main():
    logger = setup_logging()

    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont
    except ImportError:
        print("ERROR: PyQt6 is required. Install with: pip install PyQt6")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("OSINT Framework")
    app.setOrganizationName("OSINT")
    app.setApplicationVersion("2.0.0")

    # Set default font
    font = QFont("Inter", 11)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    # Import and launch main window
    from src.ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    logger.info("Desktop application launched successfully")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
