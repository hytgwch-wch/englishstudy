"""
Logger configuration for EnglishStudy application

Provides structured logging with file and console handlers.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from config import config


class Logger:
    """
    Centralized logger for the application.

    Usage:
        from src.infrastructure.logger import get_logger

        logger = get_logger(__name__)
        logger.info("Application started")
    """

    _loggers: dict = {}
    _initialized: bool = False

    @classmethod
    def setup(cls, log_file: Optional[str] = None, log_level: Optional[str] = None) -> None:
        """
        Setup the logging configuration.

        Args:
            log_file: Path to log file (default: from config)
            log_level: Logging level (default: from config)
        """
        if cls._initialized:
            return

        log_file = log_file or config.LOG_FILE
        log_level = log_level or config.LOG_LEVEL

        # Create logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Remove existing handlers
        root_logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt=config.LOG_FORMAT,
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        simple_formatter = logging.Formatter(
            fmt="%(levelname)s: %(message)s"
        )

        # Console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)

        # File handler
        log_path = config.user_data_path / log_file
        file_handler = logging.FileHandler(
            log_path,
            mode="a",
            encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        cls._initialized = True

        # Log initialization
        root_logger.info("=" * 50)
        root_logger.info(f"{config.APP_NAME} v{config.VERSION} - Logger initialized")
        root_logger.info("=" * 50)

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with the given name.

        Args:
            name: Logger name (typically __name__ of the module)

        Returns:
            Logger instance
        """
        if not cls._initialized:
            cls.setup()

        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)

        return cls._loggers[name]


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance
    """
    return Logger.get_logger(name)


def log_function_call(func):
    """
    Decorator to log function calls with arguments and return values.

    Usage:
        @log_function_call
        def my_function(arg1, arg2):
            return arg1 + arg2
    """
    logger = get_logger("function_calls")

    def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")

        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func_name} returned {result}")
            return result
        except Exception as e:
            logger.error(f"{func_name} raised {type(e).__name__}: {e}")
            raise

    return wrapper


def log_exception(logger: Optional[logging.Logger] = None):
    """
    Decorator to log exceptions raised by functions.

    Usage:
        @log_exception()
        def my_function():
            raise ValueError("Something went wrong")
    """
    def decorator(func):
        nonlocal_logger = logger or get_logger(func.__module__)

        def wrapper(*args, **kwargs):
            func_name = func.__name__
            try:
                return func(*args, **kwargs)
            except Exception as e:
                nonlocal_logger.error(
                    f"Exception in {func_name}: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise

        return wrapper
    return decorator
