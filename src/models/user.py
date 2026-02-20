"""
User model for EnglishStudy application

Represents a user with their proficiency level and learning statistics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from config import config


class UserLevel(Enum):
    """User proficiency levels"""
    ELEMENTARY = "elementary"  # 小学
    MIDDLE = "middle"          # 初中
    HIGH = "high"              # 高中
    CET4 = "cet4"              # 四级
    CET6 = "cet6"              # 六级

    @classmethod
    def all(cls) -> List[str]:
        """Get all available level values"""
        return [e.value for e in cls]

    @classmethod
    def from_string(cls, value: str) -> "UserLevel":
        """Create UserLevel from string value"""
        for level in cls:
            if level.value == value.lower():
                return level
        return cls.ELEMENTARY

    @classmethod
    def display_name(cls, level: str) -> str:
        """Get display name for a level"""
        names = {
            cls.ELEMENTARY.value: "小学",
            cls.MIDDLE.value: "初中",
            cls.HIGH.value: "高中",
            cls.CET4.value: "大学英语四级",
            cls.CET6.value: "大学英语六级",
        }
        return names.get(level, level)

    def difficulty_range(self) -> tuple[int, int]:
        """Get recommended difficulty range for this level"""
        ranges = {
            self.ELEMENTARY: (1, 3),
            self.MIDDLE: (2, 5),
            self.HIGH: (3, 7),
            self.CET4: (4, 8),
            self.CET6: (6, 10),
        }
        return ranges.get(self, (1, 10))


@dataclass
class User:
    """
    User entity representing a learner.

    Attributes:
        id: User's unique identifier (None for new users)
        name: User's display name
        level: Proficiency level
        rating: ELO-based ability rating
        created_at: Account creation timestamp
    """
    id: Optional[int]
    name: str
    level: UserLevel = UserLevel.ELEMENTARY
    rating: float = config.ELO_INITIAL_RATING
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level.value,
            "rating": self.rating,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create User from dictionary"""
        return cls(
            id=data.get("id"),
            name=data["name"],
            level=UserLevel.from_string(data.get("level", "elementary")),
            rating=data.get("rating", config.ELO_INITIAL_RATING),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )

    @property
    def level_display(self) -> str:
        """Get display name for user's level"""
        return UserLevel.display_name(self.level.value)

    def update_rating(self, new_rating: float) -> None:
        """
        Update user's ELO rating.

        Args:
            new_rating: New rating value
        """
        self.rating = max(100, min(3000, new_rating))  # Reasonable bounds

    def can_learn_difficulty(self, difficulty: int) -> bool:
        """
        Check if a word difficulty is appropriate for this user.

        Args:
            difficulty: Word difficulty level (1-10)

        Returns:
            True if the difficulty is within recommended range
        """
        min_diff, max_diff = self.level.difficulty_range()
        return min_diff <= difficulty <= max_diff


@dataclass
class UserStats:
    """
    User learning statistics.

    Attributes:
        user_id: User ID
        total_studied: Total number of words studied
        mastered: Number of mastered words
        due_for_review: Number of words due for review
        correct_rate: Overall correct rate
    """
    user_id: int
    total_studied: int = 0
    mastered: int = 0
    due_for_review: int = 0
    correct_rate: float = 0.0

    @property
    def progress_rate(self) -> float:
        """Calculate progress rate (mastered / total_studied)"""
        if self.total_studied == 0:
            return 0.0
        return self.mastered / self.total_studied

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "total_studied": self.total_studied,
            "mastered": self.mastered,
            "due_for_review": self.due_for_review,
            "correct_rate": self.correct_rate,
            "progress_rate": self.progress_rate,
        }
