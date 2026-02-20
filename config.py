"""
EnglishStudy Application Configuration

Centralized configuration management for the application.
"""

from pathlib import Path
from typing import Final
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Application configuration settings"""

    # Application metadata
    APP_NAME: str = "EnglishStudy"
    VERSION: str = "0.1.0"
    AUTHOR: str = "EnglishStudy Team"

    # Directory paths (relative to project root)
    DATA_DIR: str = "data"
    VOCAB_DIR: str = "data/vocab"
    USER_DATA_DIR: str = "data/user"

    # Database settings
    DB_NAME: str = "study.db"
    DB_TIMEOUT: int = 30  # seconds

    # SRS Algorithm settings
    SRS_MIN_EASINESS: float = 1.3
    SRS_MAX_EASINESS: float = 3.0
    SRS_INITIAL_EASINESS: float = 2.5

    # Difficulty Adapter settings
    ELO_INITIAL_RATING: float = 1000.0
    ELO_K_FACTOR: float = 32.0
    ELO_TARGET_SUCCESS_RATE: float = 0.7

    # UI settings
    WINDOW_WIDTH: int = 1000
    WINDOW_HEIGHT: int = 700
    WINDOW_MIN_WIDTH: int = 800
    WINDOW_MIN_HEIGHT: int = 600

    # Study settings
    DEFAULT_NEW_WORDS_PER_SESSION: int = 20
    DEFAULT_REVIEW_WORDS_PER_SESSION: int = 50

    # Test settings
    DEFAULT_TEST_QUESTIONS: int = 10

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "englishstudy.log"

    @property
    def project_root(self) -> Path:
        """Get the project root directory"""
        return Path(__file__).parent

    @property
    def vocab_path(self) -> Path:
        """Get the vocabulary directory path"""
        return self.project_root / self.VOCAB_DIR

    @property
    def user_data_path(self) -> Path:
        """Get the user data directory path"""
        path = self.project_root / self.USER_DATA_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def db_path(self) -> Path:
        """Get the database file path"""
        return self.user_data_path / self.DB_NAME


# Global configuration instance
config = AppConfig()


# UserLevel enum for convenience
class UserLevel:
    """User proficiency levels"""
    ELEMENTARY = "elementary"  # 小学
    MIDDLE = "middle"          # 初中
    HIGH = "high"              # 高中
    CET4 = "cet4"              # 四级
    CET6 = "cet6"              # 六级

    @classmethod
    def all(cls) -> list:
        """Get all available levels"""
        return [cls.ELEMENTARY, cls.MIDDLE, cls.HIGH, cls.CET4, cls.CET6]

    @classmethod
    def display_name(cls, level: str) -> str:
        """Get display name for a level"""
        names = {
            cls.ELEMENTARY: "小学",
            cls.MIDDLE: "初中",
            cls.HIGH: "高中",
            cls.CET4: "大学英语四级",
            cls.CET6: "大学英语六级",
        }
        return names.get(level, level)


# MemoryStatus enum for convenience
class MemoryStatus:
    """Word memory status"""
    UNKNOWN = "unknown"
    EASY = "easy"          # 认识
    MEDIUM = "medium"      # 模糊
    HARD = "hard"          # 不认识

    @classmethod
    def all(cls) -> list:
        """Get all available statuses"""
        return [cls.UNKNOWN, cls.EASY, cls.MEDIUM, cls.HARD]

    @classmethod
    def display_name(cls, status: str) -> str:
        """Get display name for a status"""
        names = {
            cls.UNKNOWN: "未学习",
            cls.EASY: "认识",
            cls.MEDIUM: "模糊",
            cls.HARD: "不认识",
        }
        return names.get(status, status)
