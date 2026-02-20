"""
ELO-based Difficulty Adaptation Algorithm

Adapts word difficulty recommendations based on user performance.
"""

import logging
import math
from typing import List, Tuple, Dict, Optional

from config import config
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)


class DifficultyAdapter:
    """
    ELO-based difficulty adaptation system.

    Uses ELO rating mechanics to:
    1. Track user ability (rating)
    2. Predict probability of correct answers
    3. Recommend appropriate word difficulty
    4. Adjust user rating based on performance

    Reference formula:
    - Expected score: P(A) = 1 / (1 + 10^((Rb - Ra) / 400))
    - Rating update: Ra' = Ra + K * (Sa - P(A))
    """

    # Difficulty to ELO mapping (1-10 difficulty levels)
    DIFFICULTY_TO_ELO = {
        1: 600,    # Very easy
        2: 800,
        3: 1000,   # Average baseline
        4: 1200,
        5: 1400,
        6: 1600,
        7: 1800,
        8: 2000,
        9: 2200,
        10: 2400,  # Very difficult
    }

    # Reverse mapping for lookups
    ELO_TO_DIFFICULTY = {v: k for k, v in DIFFICULTY_TO_ELO.items()}

    def __init__(
        self,
        initial_rating: float = None,
        k_factor: float = None,
        target_success_rate: float = None
    ):
        """
        Initialize difficulty adapter.

        Args:
            initial_rating: Initial user rating (default: from config)
            k_factor: Learning rate parameter (default: from config)
            target_success_rate: Target success rate for recommendations (default: from config)
        """
        self.initial_rating = initial_rating or config.ELO_INITIAL_RATING
        self.k_factor = k_factor or config.ELO_K_FACTOR
        self.target_success_rate = target_success_rate or config.ELO_TARGET_SUCCESS_RATE

    def difficulty_to_elo(self, difficulty: int) -> float:
        """
        Convert difficulty level to ELO rating.

        Args:
            difficulty: Difficulty level (1-10)

        Returns:
            ELO rating
        """
        difficulty = max(1, min(10, difficulty))
        return float(self.DIFFICULTY_TO_ELO.get(difficulty, 1000))

    def elo_to_difficulty(self, elo: float) -> int:
        """
        Convert ELO rating to difficulty level.

        Args:
            elo: ELO rating

        Returns:
            Difficulty level (1-10)
        """
        # Find closest difficulty
        closest_difficulty = 5
        min_diff = float('inf')

        for difficulty, difficulty_elo in self.DIFFICULTY_TO_ELO.items():
            diff = abs(difficulty_elo - elo)
            if diff < min_diff:
                min_diff = diff
                closest_difficulty = difficulty

        return closest_difficulty

    def expected_score(self, user_rating: float, word_difficulty: int) -> float:
        """
        Calculate expected probability of correct answer.

        Uses logistic function: P(A) = 1 / (1 + 10^((Rb - Ra) / 400))

        Args:
            user_rating: User's current ELO rating
            word_difficulty: Word difficulty level (1-10)

        Returns:
            Expected success probability [0, 1]
        """
        word_rating = self.difficulty_to_elo(word_difficulty)
        exponent = (word_rating - user_rating) / 400
        return 1.0 / (1.0 + pow(10, exponent))

    def update_user_rating(
        self,
        current_rating: float,
        word_difficulty: int,
        actual_result: bool
    ) -> float:
        """
        Update user rating after an attempt.

        Formula: Ra' = Ra + K * (Sa - P(A))

        Args:
            current_rating: User's current rating
            word_difficulty: Difficulty of attempted word
            actual_result: Actual result (True=correct, False=incorrect)

        Returns:
            New user rating
        """
        expected = self.expected_score(current_rating, word_difficulty)
        actual = 1.0 if actual_result else 0.0
        new_rating = current_rating + self.k_factor * (actual - expected)

        # Log significant rating changes
        rating_change = abs(new_rating - current_rating)
        if rating_change > 5:
            logger.debug(
                f"Rating change: {current_rating:.0f} -> {new_rating:.0f} "
                f"({'+'if new_rating > current_rating else ''}{new_rating - current_rating:.1f})"
            )

        return new_rating

    def recommend_difficulty(
        self,
        user_rating: float,
        target_success_rate: float = None
    ) -> int:
        """
        Recommend appropriate difficulty based on user rating.

        Inverts the expected score formula to find difficulty that yields
        the target success rate.

        Args:
            user_rating: User's current ELO rating
            target_success_rate: Desired success rate (default: from config)

        Returns:
            Recommended difficulty level (1-10)
        """
        target = target_success_rate or self.target_success_rate

        # Inverse formula: Rb = Ra + 400 * log10(1/P - 1)
        target_elo = user_rating + 400 * math.log10(1 / target - 1)

        return self.elo_to_difficulty(target_elo)

    def batch_update(
        self,
        current_rating: float,
        results: List[Tuple[int, bool]]
    ) -> float:
        """
        Batch update user rating from multiple results.

        Args:
            current_rating: User's current rating
            results: List of (difficulty, is_correct) tuples

        Returns:
            New user rating
        """
        new_rating = current_rating

        for difficulty, is_correct in results:
            new_rating = self.update_user_rating(new_rating, difficulty, is_correct)

        logger.info(
            f"Batch update: {len(results)} results, "
            f"rating: {current_rating:.0f} -> {new_rating:.0f}"
        )

        return new_rating

    def calculate_session_rating(
        self,
        current_rating: float,
        correct_count: int,
        total_count: int,
        average_difficulty: float
    ) -> float:
        """
        Calculate new rating after a study session.

        Simplified calculation using session averages.

        Args:
            current_rating: User's current rating
            correct_count: Number of correct answers
            total_count: Total number of attempts
            average_difficulty: Average difficulty of words studied

        Returns:
            New user rating
        """
        if total_count == 0:
            return current_rating

        success_rate = correct_count / total_count
        expected = self.expected_score(current_rating, int(round(average_difficulty)))

        # Apply K factor scaled by session size
        scaled_k = self.k_factor * min(1.0, total_count / 10)  # Cap at 10 questions worth
        new_rating = current_rating + scaled_k * (success_rate - expected)

        return new_rating

    def get_difficulty_range(
        self,
        user_rating: float,
        range_size: int = 2
    ) -> Tuple[int, int]:
        """
        Get a range of appropriate difficulties for a user.

        Args:
            user_rating: User's current ELO rating
            range_size: +/- range around recommended difficulty

        Returns:
            Tuple of (min_difficulty, max_difficulty)
        """
        recommended = self.recommend_difficulty(user_rating)
        min_diff = max(1, recommended - range_size)
        max_diff = min(10, recommended + range_size)

        return min_diff, max_diff

    def assess_performance_level(
        self,
        user_rating: float
    ) -> str:
        """
        Assess user's performance level based on rating.

        Args:
            user_rating: User's ELO rating

        Returns:
            Performance level description
        """
        if user_rating < 800:
            return "beginner"
        elif user_rating < 1200:
            return "elementary"
        elif user_rating < 1600:
            return "intermediate"
        elif user_rating < 2000:
            return "advanced"
        else:
            return "expert"

    def should_adjust_difficulty(
        self,
        recent_results: List[bool],
        min_samples: int = 5
    ) -> Tuple[bool, str]:
        """
        Analyze recent performance to suggest difficulty adjustment.

        Args:
            recent_results: List of recent results (True=correct, False=incorrect)
            min_samples: Minimum samples needed for analysis

        Returns:
            Tuple of (should_adjust, direction)
            direction is "easier", "harder", or "none"
        """
        if len(recent_results) < min_samples:
            return False, "none"

        correct_rate = sum(recent_results) / len(recent_results)

        # Adjust if success rate is too high or too low
        if correct_rate >= 0.9:
            return True, "harder"
        elif correct_rate <= 0.4:
            return True, "easier"
        else:
            return False, "none"


# Global difficulty adapter instance
_difficulty_adapter_instance: Optional[DifficultyAdapter] = None


def get_difficulty_adapter() -> DifficultyAdapter:
    """Get the global difficulty adapter instance"""
    global _difficulty_adapter_instance
    if _difficulty_adapter_instance is None:
        _difficulty_adapter_instance = DifficultyAdapter()
    return _difficulty_adapter_instance
