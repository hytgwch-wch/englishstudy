"""
Study Manager Service

Manages study sessions, word scheduling, and learning progress.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from config import config
from src.models.user import User
from src.models.vocabulary import Vocabulary
from src.models.word_record import WordRecord, MemoryStatus
from src.models.session import StudySession
from src.core.srs import SRSEngine
from src.core.difficulty import DifficultyAdapter
from src.core.state_machine import WordStateMachine, get_state_machine
from src.infrastructure.database import DatabaseManager
from src.infrastructure.logger import get_logger, log_exception

logger = get_logger(__name__)


class StudyManager:
    """
    Service for managing study sessions and word learning.

    Handles:
    - Creating and managing study sessions
    - Scheduling words for study/review
    - Processing user feedback
    - Updating word records with SRS algorithm
    - Managing mistake/new word books
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        srs_engine: Optional[SRSEngine] = None,
        difficulty_adapter: Optional[DifficultyAdapter] = None
    ):
        """
        Initialize study manager.

        Args:
            db_manager: Database manager instance
            srs_engine: SRS algorithm engine
            difficulty_adapter: Difficulty adaptation engine
        """
        self.db = db_manager
        self.srs = srs_engine or SRSEngine()
        self.difficulty = difficulty_adapter or DifficultyAdapter()
        self.state_machine = get_state_machine()
        self.current_session: Optional[StudySession] = None

    @log_exception(logger)
    def start_session(
        self,
        user: User,
        session_type: str = "study"
    ) -> StudySession:
        """
        Start a new study session.

        Args:
            user: User starting the session
            session_type: Type of session (study/review)

        Returns:
            Created StudySession
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        # Create session in database
        session_id = self.db.create_study_session(user.id)

        self.current_session = StudySession(
            id=session_id,
            user_id=user.id,
            session_type=session_type,
            start_time=datetime.now()
        )

        logger.info(
            f"Started {session_type} session {session_id} "
            f"for user {user.name} (ID: {user.id})"
        )

        return self.current_session

    @log_exception(logger)
    def end_session(self) -> Optional[StudySession]:
        """
        End the current study session.

        Returns:
            The ended session or None if no active session
        """
        if self.current_session is None or self.db is None:
            return None

        self.current_session.end()

        # Update database
        self.db.end_study_session(
            self.current_session.id,
            self.current_session.words_studied,
            self.current_session.correct_rate
        )

        logger.info(
            f"Ended session {self.current_session.id}: "
            f"{self.current_session.words_studied} words, "
            f"{self.current_session.correct_rate:.1%} correct"
        )

        session = self.current_session
        self.current_session = None
        return session

    @log_exception(logger)
    def get_study_queue(
        self,
        user: User,
        max_new: int = None,
        max_review: int = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get words for today's study session.

        Args:
            user: User to get queue for
            max_new: Maximum new words (default: from config)
            max_review: Maximum review words (default: from config)

        Returns:
            Dictionary with 'new' and 'review' word lists
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        max_new = max_new or config.DEFAULT_NEW_WORDS_PER_SESSION
        max_review = max_review or config.DEFAULT_REVIEW_WORDS_PER_SESSION

        # Get due words for review
        due_words_data = self.db.get_due_words(user.id)
        due_words_data = due_words_data[:max_review]

        # Get new words to learn
        new_words_data = self.db.get_new_words(user.id, max_new)

        logger.info(
            f"Study queue for user {user.id}: "
            f"{len(new_words_data)} new, {len(due_words_data)} review"
        )

        return {
            "new": new_words_data,
            "review": due_words_data
        }

    @log_exception(logger)
    def submit_answer(
        self,
        user: User,
        vocabulary_id: int,
        feedback: MemoryStatus
    ) -> Dict[str, Any]:
        """
        Submit an answer for a word and update records.

        Args:
            user: User submitting answer
            vocabulary_id: ID of vocabulary word
            feedback: User's memory status feedback

        Returns:
            Dictionary with updated record info
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        # Get or create word record
        record_data = self.db.get_or_create_word_record(user.id, vocabulary_id)
        record = WordRecord.from_dict(record_data)

        # Get vocabulary for difficulty info
        vocab_data = self.db.get_vocabulary_by_id(vocabulary_id)
        vocab_difficulty = vocab_data["difficulty"] if vocab_data else 5

        # Calculate SRS update
        new_interval, new_easiness, new_repetitions, next_review = \
            self.srs.calculate_next_review(
                record.interval,
                record.easiness,
                record.repetitions,
                feedback
            )

        # Update state based on feedback
        new_state = self.state_machine.next_state(record.state, feedback)

        # Update record in database
        self.db.update_word_record(
            record.id,
            feedback.value,
            new_easiness,
            new_interval,
            new_repetitions,
            next_review.isoformat(),
            new_state.value
        )

        # Update user rating
        is_correct = feedback.is_correct()
        new_rating = self.difficulty.update_user_rating(
            user.rating,
            vocab_difficulty,
            is_correct
        )
        self.db.update_user_rating(user.id, new_rating)
        user.update_rating(new_rating)

        # Track in session
        if self.current_session is not None:
            self.current_session.record_attempt(is_correct)
            self.current_session.add_vocabulary(vocabulary_id)

        # Add to mistake/new word books if needed
        if feedback == MemoryStatus.HARD:
            self.db.add_to_mistake_book(user.id, record.id)
        elif feedback == MemoryStatus.MEDIUM:
            # Optional: add to new word book for review
            pass

        logger.debug(
            f"Answer recorded: vocab_id={vocabulary_id}, "
            f"feedback={feedback.value}, "
            f"next_review={next_review.strftime('%Y-%m-%d')}"
        )

        return {
            "record_id": record.id,
            "new_interval": new_interval,
            "new_easiness": new_easiness,
            "next_review": next_review.isoformat(),
            "new_state": new_state.value,
            "user_rating": new_rating,
        }

    @log_exception(logger)
    def get_mistake_book(self, user: User) -> List[Dict[str, Any]]:
        """
        Get user's mistake book.

        Args:
            user: User to get mistake book for

        Returns:
            List of mistake book entries
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        return self.db.get_mistake_book(user.id)

    @log_exception(logger)
    def get_new_word_book(self, user: User) -> List[Dict[str, Any]]:
        """
        Get user's new word book.

        Args:
            user: User to get new word book for

        Returns:
            List of new word book entries
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        return self.db.get_new_word_book(user.id)

    @log_exception(logger)
    def add_to_new_word_book(
        self,
        user: User,
        word_record_id: int,
        note: str = ""
    ) -> bool:
        """
        Add a word to user's new word book.

        Args:
            user: User
            word_record_id: Word record ID
            note: Optional note

        Returns:
            True if successful
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        return self.db.add_to_new_word_book(user.id, word_record_id, note)

    @log_exception(logger)
    def remove_from_mistake_book(
        self,
        user: User,
        entry_id: int
    ) -> bool:
        """
        Remove an entry from mistake book.

        Args:
            user: User
            entry_id: Entry ID to remove

        Returns:
            True if successful
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM mistake_book WHERE id = ? AND user_id = ?",
                (entry_id, user.id)
            )
            conn.commit()
            return cursor.rowcount > 0

    @log_exception(logger)
    def remove_from_new_word_book(
        self,
        user: User,
        entry_id: int
    ) -> bool:
        """
        Remove an entry from new word book.

        Args:
            user: User
            entry_id: Entry ID to remove

        Returns:
            True if successful
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM new_word_book WHERE id = ? AND user_id = ?",
                (entry_id, user.id)
            )
            conn.commit()
            return cursor.rowcount > 0

    @log_exception(logger)
    def get_user_stats(self, user: User) -> Dict[str, Any]:
        """
        Get comprehensive user statistics.

        Args:
            user: User to get stats for

        Returns:
            Dictionary with statistics
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        stats = self.db.get_user_stats(user.id)

        # Get recommended difficulty
        recommended_difficulty = self.difficulty.recommend_difficulty(user.rating)

        return {
            **stats,
            "user_rating": user.rating,
            "recommended_difficulty": recommended_difficulty,
            "performance_level": self.difficulty.assess_performance_level(user.rating),
        }

    @log_exception(logger)
    def get_session_summary(self, session: StudySession) -> Dict[str, Any]:
        """
        Get summary of a study session.

        Args:
            session: Study session to summarize

        Returns:
            Session summary dictionary
        """
        return {
            "session_id": session.id,
            "session_type": session.session_type.value,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "duration_minutes": session.duration_minutes,
            "words_studied": session.words_studied,
            "correct_rate": session.correct_rate,
            "vocabulary_ids": session.vocabulary_ids,
        }


# Global instance
_study_manager_instance: Optional[StudyManager] = None


def get_study_manager() -> StudyManager:
    """Get the global study manager instance"""
    global _study_manager_instance
    if _study_manager_instance is None:
        from src.infrastructure.database import get_db
        _study_manager_instance = StudyManager(db_manager=get_db())
    return _study_manager_instance
