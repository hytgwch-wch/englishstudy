"""
Session model for EnglishStudy application

Tracks study sessions and test sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class SessionType(Enum):
    """Type of session"""
    STUDY = "study"      # Learning mode
    TEST = "test"        # Testing mode
    REVIEW = "review"    # Review mode

    @classmethod
    def from_string(cls, value: str) -> "SessionType":
        """Create SessionType from string value"""
        for session_type in cls:
            if session_type.value == value.lower():
                return session_type
        return cls.STUDY

    @classmethod
    def display_name(cls, session_type: str) -> str:
        """Get display name for a session type"""
        names = {
            cls.STUDY.value: "学习",
            cls.TEST.value: "测试",
            cls.REVIEW.value: "复习",
        }
        return names.get(session_type, session_type)


@dataclass
class StudySession:
    """
    Record of a study session.

    Attributes:
        id: Session's unique identifier
        user_id: User ID
        session_type: Type of session
        start_time: Session start timestamp
        end_time: Session end timestamp (None if ongoing)
        words_studied: Number of words studied
        words_correct: Number of correct answers
        total_attempts: Total answer attempts
        vocabulary_ids: List of vocabulary IDs studied
    """
    id: Optional[int]
    user_id: int
    session_type: SessionType = SessionType.STUDY
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    words_studied: int = 0
    words_correct: int = 0
    total_attempts: int = 0
    vocabulary_ids: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_type": self.session_type.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "words_studied": self.words_studied,
            "words_correct": self.words_correct,
            "total_attempts": self.total_attempts,
            "vocabulary_ids": self.vocabulary_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudySession":
        """Create StudySession from dictionary"""
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            session_type=SessionType.from_string(data.get("session_type", "study")),
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else datetime.now(),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            words_studied=data.get("words_studied", 0),
            words_correct=data.get("words_correct", 0),
            total_attempts=data.get("total_attempts", 0),
            vocabulary_ids=data.get("vocabulary_ids", []),
        )

    @property
    def is_ongoing(self) -> bool:
        """Check if session is still ongoing"""
        return self.end_time is None

    @property
    def correct_rate(self) -> float:
        """Calculate correct rate"""
        if self.total_attempts == 0:
            return 0.0
        return self.words_correct / self.total_attempts

    @property
    def duration_minutes(self) -> Optional[int]:
        """Get session duration in minutes (None if ongoing)"""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)

    def start(self) -> None:
        """Start or resume the session"""
        if self.end_time is not None:
            # Resume previously ended session
            self.end_time = None

    def end(self) -> None:
        """End the session"""
        if self.end_time is None:
            self.end_time = datetime.now()

    def record_attempt(self, is_correct: bool) -> None:
        """
        Record an answer attempt.

        Args:
            is_correct: Whether the answer was correct
        """
        self.total_attempts += 1
        if is_correct:
            self.words_correct += 1

    def add_vocabulary(self, vocab_id: int) -> None:
        """Add a vocabulary ID to the session"""
        if vocab_id not in self.vocabulary_ids:
            self.vocabulary_ids.append(vocab_id)
            self.words_studied = len(self.vocabulary_ids)


@dataclass
class TestQuestion:
    """
    A test question for a vocabulary word.

    Attributes:
        vocabulary_id: ID of the vocabulary word
        question_type: Type of question
        question: Question text
        correct_answer: Correct answer
        user_answer: User's answer (None if not answered)
        is_correct: Whether the answer was correct (None if not answered)
        time_taken: Time taken to answer (seconds, None if not answered)
    """
    vocabulary_id: int
    question_type: str
    question: str
    correct_answer: str
    user_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    time_taken: Optional[int] = None

    def answer(self, user_answer: str, time_taken: Optional[int] = None) -> bool:
        """
        Submit an answer to the question.

        Args:
            user_answer: User's answer
            time_taken: Time taken in seconds

        Returns:
            Whether the answer was correct
        """
        self.user_answer = user_answer
        self.time_taken = time_taken
        self.is_correct = self._check_answer(user_answer)
        return self.is_correct

    def _check_answer(self, answer: str) -> bool:
        """Check if the answer is correct"""
        # Case-insensitive comparison
        return answer.strip().lower() == self.correct_answer.strip().lower()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "vocabulary_id": self.vocabulary_id,
            "question_type": self.question_type,
            "question": self.question,
            "correct_answer": self.correct_answer,
            "user_answer": self.user_answer,
            "is_correct": self.is_correct,
            "time_taken": self.time_taken,
        }


@dataclass
class TestResult:
    """
    Result summary for a test session.

    Attributes:
        session_id: Associated study session ID
        total_questions: Total number of questions
        correct_answers: Number of correct answers
        total_time: Total time taken (seconds)
        questions: List of test questions
    """
    session_id: int
    total_questions: int
    correct_answers: int
    total_time: int = 0
    questions: List[TestQuestion] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Calculate test score (0-100)"""
        if self.total_questions == 0:
            return 0.0
        return (self.correct_answers / self.total_questions) * 100

    @property
    def passed(self) -> bool:
        """Check if test was passed (score >= 60%)"""
        return self.score >= 60.0

    @property
    def average_time_per_question(self) -> float:
        """Calculate average time per question (seconds)"""
        if self.total_questions == 0:
            return 0.0
        return self.total_time / self.total_questions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "total_questions": self.total_questions,
            "correct_answers": self.correct_answers,
            "score": self.score,
            "passed": self.passed,
            "total_time": self.total_time,
            "average_time": self.average_time_per_question,
            "questions": [q.to_dict() for q in self.questions],
        }
