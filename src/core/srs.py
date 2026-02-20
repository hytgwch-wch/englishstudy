"""
SM-2 Spaced Repetition System Algorithm

Implements the SuperMemo-2 algorithm for optimized vocabulary review scheduling.
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional, List

from config import config
from src.models.word_record import MemoryStatus, WordState
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)


class SRSEngine:
    """
    SuperMemo-2 Spaced Repetition System engine.

    Algorithm reference:
    - I(1) = 1 day
    - I(2) = 6 days
    - I(n) = I(n-1) * EF(n-1), for n > 2
    - EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))

    Where:
    - I(n): Interval for n-th review (in days)
    - EF: Easiness factor (clamped to 1.3 - 3.0)
    - q: Quality score (0-5) based on user feedback
    """

    # Quality score mapping from MemoryStatus
    QUALITY_MAP = {
        MemoryStatus.EASY: 5,      # Perfect response
        MemoryStatus.MEDIUM: 3,    # Hesitant but correct
        MemoryStatus.HARD: 1,      # Incorrect
        MemoryStatus.UNKNOWN: 0,   # No response
    }

    # Default intervals
    FIRST_INTERVAL = 1  # days
    SECOND_INTERVAL = 6  # days

    # Maximum interval to prevent timedelta overflow (10 years)
    MAX_INTERVAL_DAYS = 3650

    def __init__(
        self,
        min_easiness: Optional[float] = None,
        max_easiness: Optional[float] = None,
        initial_easiness: Optional[float] = None
    ):
        """
        Initialize SRS engine.

        Args:
            min_easiness: Minimum easiness factor (default: from config)
            max_easiness: Maximum easiness factor (default: from config)
            initial_easiness: Initial easiness factor (default: from config)
        """
        self.min_easiness = min_easiness or config.SRS_MIN_EASINESS
        self.max_easiness = max_easiness or config.SRS_MAX_EASINESS
        self.initial_easiness = initial_easiness or config.SRS_INITIAL_EASINESS

    def calculate_next_review(
        self,
        current_interval: int,
        current_easiness: float,
        repetitions: int,
        feedback: MemoryStatus
    ) -> Tuple[int, float, int, datetime]:
        """
        Calculate next review parameters based on user feedback.

        Args:
            current_interval: Current review interval (days)
            current_easiness: Current easiness factor
            repetitions: Current number of repetitions
            feedback: User's memory status feedback

        Returns:
            Tuple of (new_interval, new_easiness, new_repetitions, next_review_date)
        """
        quality = self._get_quality_score(feedback)

        # Calculate new easiness factor
        new_easiness = self._update_easiness(current_easiness, quality)
        logger.debug(f"Easiness updated: {current_easiness:.2f} -> {new_easiness:.2f}")

        # Calculate new interval
        new_interval = self._calculate_interval(
            current_interval,
            repetitions,
            new_easiness,
            quality
        )
        logger.debug(f"Interval updated: {current_interval} -> {new_interval} days")

        # Update repetitions
        new_repetitions = self._update_repetitions(repetitions, quality)

        # Calculate next review date (with safety clamp)
        safe_interval = min(new_interval, self.MAX_INTERVAL_DAYS)
        next_review = datetime.now() + timedelta(days=safe_interval)

        return new_interval, new_easiness, new_repetitions, next_review

    def _get_quality_score(self, feedback: MemoryStatus) -> int:
        """Convert MemoryStatus to quality score (0-5)"""
        return self.QUALITY_MAP.get(feedback, 0)

    def _update_easiness(self, current_ef: float, quality: int) -> float:
        """
        Update easiness factor based on quality score.

        Formula: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))

        Args:
            current_ef: Current easiness factor
            quality: Quality score (0-5)

        Returns:
            New easiness factor (clamped to min/max bounds)
        """
        ef_prime = current_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

        # Clamp to bounds
        return max(self.min_easiness, min(ef_prime, self.max_easiness))

    def _calculate_interval(
        self,
        current_interval: int,
        repetitions: int,
        easiness: float,
        quality: int
    ) -> int:
        """
        Calculate next review interval.

        Rules:
        - First review: 1 day
        - Second review: 6 days
        - Subsequent: interval * easiness
        - If quality < 3: reset to 1 day

        Args:
            current_interval: Current interval
            repetitions: Number of successful repetitions
            easiness: Current easiness factor
            quality: Quality score

        Returns:
            New interval in days
        """
        # Reset on poor performance
        if quality < 3:
            return self.FIRST_INTERVAL

        if repetitions == 0:
            return self.FIRST_INTERVAL
        elif repetitions == 1:
            return self.SECOND_INTERVAL
        else:
            new_interval = int(current_interval * easiness)
            # Clamp to maximum to prevent timedelta overflow
            return min(new_interval, self.MAX_INTERVAL_DAYS)

    def _update_repetitions(self, current_repetitions: int, quality: int) -> int:
        """
        Update repetition count.

        Args:
            current_repetitions: Current repetition count
            quality: Quality score

        Returns:
            New repetition count
        """
        if quality < 3:
            return 0  # Reset on poor performance
        return current_repetitions + 1

    def get_due_records(
        self,
        records: List["WordRecord"],  # type: ignore
        limit: Optional[int] = None
    ) -> List["WordRecord"]:  # type: ignore
        """
        Get records that are due for review.

        Args:
            records: List of word records
            limit: Maximum number of records to return (None for unlimited)

        Returns:
            List of due word records, sorted by next_review date
        """
        now = datetime.now()

        # Filter for due records
        due = [
            r for r in records
            if r.next_review is not None
            and r.next_review <= now
            and r.state != WordState.MASTERED
        ]

        # Sort by next_review date (oldest first)
        due.sort(key=lambda r: r.next_review or datetime.min)

        if limit is not None:
            return due[:limit]

        return due

    def get_new_records(
        self,
        records: List["WordRecord"],  # type: ignore
        limit: int = 20
    ) -> List["WordRecord"]:  # type: ignore
        """
        Get records for new words to learn.

        Args:
            records: List of word records
            limit: Maximum number of records to return

        Returns:
            List of new word records (status == UNKNOWN)
        """
        new_records = [
            r for r in records
            if r.status == MemoryStatus.UNKNOWN
        ]

        return new_records[:limit]

    def calculate_study_queue(
        self,
        records: List["WordRecord"],  # type: ignore
        max_new: int = 20,
        max_review: int = 50
    ) -> Tuple[List["WordRecord"], List["WordRecord"]]:  # type: ignore
        """
        Calculate today's study queue.

        Args:
            records: All word records
            max_new: Maximum new words to study
            max_review: Maximum review words to study

        Returns:
            Tuple of (new_words, review_words)
        """
        # Get due words for review
        due_words = self.get_due_records(records, limit=max_review)

        # Get new words to learn
        new_words = self.get_new_records(records, limit=max_new)

        logger.info(f"Study queue: {len(new_words)} new, {len(due_words)} for review")
        return new_words, due_words

    def estimate_review_load(
        self,
        records: List["WordRecord"],  # type: ignore
        days_ahead: int = 7
    ) -> dict[int, int]:
        """
        Estimate review load for the next N days.

        Args:
            records: All word records
            days_ahead: Number of days to forecast

        Returns:
            Dictionary mapping days from now -> count of due reviews
        """
        now = datetime.now()
        load = {}

        for day in range(days_ahead + 1):
            target_date = now + timedelta(days=day)
            day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            # Count records due on this day
            count = sum(
                1 for r in records
                if r.next_review is not None
                and day_start <= r.next_review < day_end
            )

            load[day] = count

        return load


# Global SRS engine instance
_srs_instance: Optional[SRSEngine] = None


def get_srs_engine() -> SRSEngine:
    """Get the global SRS engine instance"""
    global _srs_instance
    if _srs_instance is None:
        _srs_instance = SRSEngine()
    return _srs_instance
