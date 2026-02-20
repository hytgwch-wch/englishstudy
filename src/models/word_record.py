"""
Word Record model for EnglishStudy application

Tracks a user's learning progress for individual words.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from config import config


class MemoryStatus(Enum):
    """Memory status after studying a word"""
    UNKNOWN = "unknown"      # 未学习
    EASY = "easy"            # 认识
    MEDIUM = "medium"        # 模糊
    HARD = "hard"            # 不认识

    @classmethod
    def all(cls) -> list[str]:
        """Get all status values"""
        return [e.value for e in cls]

    @classmethod
    def from_string(cls, value: str) -> "MemoryStatus":
        """Create MemoryStatus from string value"""
        for status in cls:
            if status.value == value.lower():
                return status
        return cls.UNKNOWN

    @classmethod
    def display_name(cls, status: str) -> str:
        """Get display name for a status"""
        names = {
            cls.UNKNOWN.value: "未学习",
            cls.EASY.value: "认识",
            cls.MEDIUM.value: "模糊",
            cls.HARD.value: "不认识",
        }
        return names.get(status, status)

    def is_correct(self) -> bool:
        """Check if this status indicates correct recall"""
        return self in [self.EASY, self.MEDIUM]

    def to_quality_score(self) -> int:
        """
        Convert to SM-2 quality score (0-5).

        Mapping:
        - EASY (认识) -> 5 (perfect response)
        - MEDIUM (模糊) -> 3 (hesitant but correct)
        - HARD (不认识) -> 1 (incorrect)
        """
        scores = {
            self.EASY: 5,
            self.MEDIUM: 3,
            self.HARD: 1,
            self.UNKNOWN: 0,
        }
        return scores.get(self, 0)


class WordState(Enum):
    """Learning state of a word"""
    NEW = "new"                    # 新词，未学习
    LEARNING = "learning"          # 学习中
    REVIEW = "review"              # 复习中
    MASTERED = "mastered"          # 已掌握

    @classmethod
    def from_string(cls, value: str) -> "WordState":
        """Create WordState from string value"""
        for state in cls:
            if state.value == value.lower():
                return state
        return cls.NEW

    @classmethod
    def display_name(cls, state: str) -> str:
        """Get display name for a state"""
        names = {
            cls.NEW.value: "新词",
            cls.LEARNING.value: "学习中",
            cls.REVIEW.value: "复习中",
            cls.MASTERED.value: "已掌握",
        }
        return names.get(state, state)


class StateMachine:
    """
    State machine for word learning progression.

    Transitions:
        NEW --[any feedback]--> LEARNING
        LEARNING --[EASY]--> REVIEW
        LEARNING --[MEDIUM/HARD]--> LEARNING
        REVIEW --[EASY]--> MASTERED
        REVIEW --[MEDIUM]--> REVIEW
        REVIEW --[HARD]--> LEARNING
        MASTERED --[MEDIUM]--> REVIEW
        MASTERED --[HARD]--> LEARNING
        MASTERED --[EASY]--> MASTERED
    """

    TRANSITIONS = {
        WordState.NEW: {
            MemoryStatus.EASY: WordState.LEARNING,
            MemoryStatus.MEDIUM: WordState.LEARNING,
            MemoryStatus.HARD: WordState.LEARNING,
        },
        WordState.LEARNING: {
            MemoryStatus.EASY: WordState.REVIEW,
            MemoryStatus.MEDIUM: WordState.LEARNING,
            MemoryStatus.HARD: WordState.LEARNING,
        },
        WordState.REVIEW: {
            MemoryStatus.EASY: WordState.MASTERED,
            MemoryStatus.MEDIUM: WordState.REVIEW,
            MemoryStatus.HARD: WordState.LEARNING,
        },
        WordState.MASTERED: {
            MemoryStatus.EASY: WordState.MASTERED,
            MemoryStatus.MEDIUM: WordState.REVIEW,
            MemoryStatus.HARD: WordState.LEARNING,
        },
    }

    @classmethod
    def next_state(
        cls,
        current: WordState,
        feedback: MemoryStatus
    ) -> WordState:
        """
        Calculate next state based on current state and feedback.

        Args:
            current: Current word state
            feedback: User's memory status feedback

        Returns:
            Next word state
        """
        return cls.TRANSITIONS[current][feedback]


@dataclass
class WordRecord:
    """
    Record tracking a user's progress with a specific word.

    Attributes:
        id: Record's unique identifier
        user_id: User ID who owns this record
        vocabulary_id: ID of the vocabulary word
        status: Current memory status
        easiness: SM-2 easiness factor
        interval: Current review interval (days)
        repetitions: Number of successful repetitions
        next_review: Next review timestamp
        last_review: Last review timestamp
        state: Learning state
        created_at: Record creation timestamp
    """
    id: Optional[int]
    user_id: int
    vocabulary_id: int
    status: MemoryStatus = MemoryStatus.UNKNOWN
    easiness: float = config.SRS_INITIAL_EASINESS
    interval: int = 0
    repetitions: int = 0
    next_review: Optional[datetime] = None
    last_review: Optional[datetime] = None
    state: WordState = WordState.NEW
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "vocabulary_id": self.vocabulary_id,
            "status": self.status.value,
            "easiness": self.easiness,
            "interval": self.interval,
            "repetitions": self.repetitions,
            "next_review": self.next_review.isoformat() if self.next_review else None,
            "last_review": self.last_review.isoformat() if self.last_review else None,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WordRecord":
        """Create WordRecord from dictionary"""
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            vocabulary_id=data["vocabulary_id"],
            status=MemoryStatus.from_string(data.get("status", "unknown")),
            easiness=data.get("easiness", config.SRS_INITIAL_EASINESS),
            interval=data.get("interval", 0),
            repetitions=data.get("repetitions", 0),
            next_review=datetime.fromisoformat(data["next_review"]) if data.get("next_review") else None,
            last_review=datetime.fromisoformat(data["last_review"]) if data.get("last_review") else None,
            state=WordState.from_string(data.get("state", "new")),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )

    def update_from_study(
        self,
        feedback: MemoryStatus,
        new_interval: int,
        new_easiness: float,
        new_repetitions: int,
        next_review: datetime
    ) -> None:
        """
        Update record after a study session.

        Args:
            feedback: User's memory status
            new_interval: New review interval
            new_easiness: New easiness factor
            new_repetitions: New repetition count
            next_review: Next review time
        """
        self.status = feedback
        self.interval = new_interval
        self.easiness = new_easiness
        self.repetitions = new_repetitions
        self.next_review = next_review
        self.last_review = datetime.now()

        # Update state based on feedback
        self.state = StateMachine.next_state(self.state, feedback)

    @property
    def is_due(self) -> bool:
        """Check if this word is due for review"""
        if self.next_review is None:
            return False
        return datetime.now() >= self.next_review

    @property
    def days_until_review(self) -> Optional[int]:
        """Get days until next review (None if not scheduled)"""
        if self.next_review is None:
            return None
        delta = self.next_review - datetime.now()
        return max(0, delta.days)

    @property
    def status_display(self) -> str:
        """Get display name for current status"""
        return MemoryStatus.display_name(self.status.value)

    @property
    def state_display(self) -> str:
        """Get display name for current state"""
        return WordState.display_name(self.state.value)
