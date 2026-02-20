"""
EnglishStudy - Main Application Entry Point

个性化英语单词学习软件
基于 SM-2 间隔重复算法和 ELO 难度自适应系统
"""

import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from config import config
from src.ui.main_window import MainWindow
from src.infrastructure.logger import Logger, get_logger


def setup_logging():
    """Setup application logging"""
    log_file = config.user_data_path / config.LOG_FILE
    Logger.setup(
        log_file=str(log_file),
        log_level=config.LOG_LEVEL
    )


def main():
    """Main application entry point"""
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info(f"Starting {config.APP_NAME} v{config.VERSION}")
    logger.info("=" * 60)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.VERSION)
    app.setOrganizationName("EnglishStudy")

    # Enable high DPI scaling
    app.setStyle("Fusion")

    # Create and show main window
    main_window = MainWindow()
    main_window.show()

    logger.info("Main window displayed")

    # Run application
    exit_code = app.exec()

    logger.info(f"Application exiting with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
