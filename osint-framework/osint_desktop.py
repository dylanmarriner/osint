#!/usr/bin/env python3
"""
OSINT Framework Desktop Application

Standalone PyQt6 desktop application.
Can be packaged with PyInstaller into single executable.

Usage:
    python osint_desktop.py                    # Run desktop app
    pyinstaller osint_desktop.py --onefile    # Package into single exe
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from src.ui import MainWindow


def setup_logging():
    """Configure logging."""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "osint.log"),
            logging.StreamHandler()
        ]
    )


def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting OSINT Framework Desktop Application")
    
    app = QApplication(sys.argv)
    app.setApplicationName("OSINT Framework")
    app.setApplicationVersion("1.0.0")
    
    window = MainWindow()
    window.show()
    
    logger.info("Application window displayed")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
