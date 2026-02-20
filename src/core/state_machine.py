"""
Word Learning State Machine

Manages word learning progression through different states.
"""

import logging
from typing import Dict, List, Optional, Callable
from enum import Enum

from src.models.word_record import WordState, MemoryStatus
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)


class StateTransition:
    """
    Represents a state transition with conditions and actions.
    """

    def __init__(
        self,
        from_state: WordState,
        to_state: WordState,
        feedback: MemoryStatus,
        condition: Optional[Callable] = None,
        action: Optional[Callable] = None
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.feedback = feedback
        self.condition = condition
        self.action = action

    def can_transition(self) -> bool:
        """Check if transition conditions are met"""
        if self.condition is None:
            return True
        return self.condition()

    def execute_action(self) -> None:
        """Execute the transition action"""
        if self.action is not None:
            self.action()


class WordStateMachine:
    """
    State machine for managing word learning progression.

    State Transitions:
        NEW --[any feedback]--> LEARNING
        LEARNING --[EASY x2]--> REVIEW
        LEARNING --[MEDIUM]--> LEARNING
        LEARNING --[HARD]--> LEARNING
        REVIEW --[EASY x3]--> MASTERED
        REVIEW --[MEDIUM]--> REVIEW
        REVIEW --[HARD]--> LEARNING
        MASTERED --[MEDIUM/HARD]--> REVIEW
        MASTERED --[EASY]--> MASTERED
    """

    # State transition rules
    # Format: {from_state: {feedback: (to_state, consecutive_required)}}
    TRANSITIONS = {
        WordState.NEW: {
            MemoryStatus.EASY: (WordState.LEARNING, 1),
            MemoryStatus.MEDIUM: (WordState.LEARNING, 1),
            MemoryStatus.HARD: (WordState.LEARNING, 1),
        },
        WordState.LEARNING: {
            MemoryStatus.EASY: (WordState.REVIEW, 2),  # Need 2 consecutive EASY
            MemoryStatus.MEDIUM: (WordState.LEARNING, None),
            MemoryStatus.HARD: (WordState.LEARNING, None),
        },
        WordState.REVIEW: {
            MemoryStatus.EASY: (WordState.MASTERED, 3),  # Need 3 consecutive EASY
            MemoryStatus.MEDIUM: (WordState.REVIEW, None),
            MemoryStatus.HARD: (WordState.LEARNING, None),
        },
        WordState.MASTERED: {
            MemoryStatus.EASY: (WordState.MASTERED, None),
            MemoryStatus.MEDIUM: (WordState.REVIEW, None),
            MemoryStatus.HARD: (WordState.LEARNING, None),
        },
    }

    def __init__(self):
        """Initialize state machine"""
        self.consecutive_counts: Dict[WordState, int] = {
            WordState.LEARNING: 0,
            WordState.REVIEW: 0,
        }
        self.state_history: List[tuple[WordState, MemoryStatus]] = []

    def next_state(
        self,
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
        # Get transition rule
        transitions = self.TRANSITIONS.get(current, {})
        if feedback not in transitions:
            logger.warning(f"No transition defined for {current} + {feedback}")
            return current

        next_state, required = transitions[feedback]

        # Check if consecutive requirement is met
        if required is not None:
            if feedback == MemoryStatus.EASY:
                self.consecutive_counts[current] = self.consecutive_counts.get(current, 0) + 1
                if self.consecutive_counts[current] < required:
                    logger.debug(
                        f"Need {required} EASY for {current} -> {next_state}, "
                        f"have {self.consecutive_counts[current]}"
                    )
                    return current
            else:
                # Reset consecutive count on non-EASY
                self.consecutive_counts[current] = 0

        # Reset consecutive count when leaving state
        if next_state != current:
            self.consecutive_counts[current] = 0

        # Record history
        self.state_history.append((current, feedback))

        # Limit history size
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-50:]

        logger.debug(f"State transition: {current.value} --[{feedback.value}]--> {next_state.value}")
        return next_state

    def get_state_history(self, limit: int = 10) -> List[tuple[WordState, MemoryStatus]]:
        """
        Get recent state transition history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of (state, feedback) tuples
        """
        return self.state_history[-limit:]

    def reset(self) -> None:
        """Reset state machine to initial state"""
        self.consecutive_counts = {
            WordState.LEARNING: 0,
            WordState.REVIEW: 0,
        }
        self.state_history = []
        logger.debug("State machine reset")

    def can_transition_to(
        self,
        current: WordState,
        target: WordState
    ) -> bool:
        """
        Check if a transition to target state is possible from current state.

        Args:
            current: Current state
            target: Target state

        Returns:
            True if transition is possible
        """
        if current == target:
            return True

        # Check if target is reachable from current via any feedback
        for feedback, (next_state, _) in self.TRANSITIONS.get(current, {}).items():
            if next_state == target:
                return True

        return False

    def get_required_feedback_for(
        self,
        current: WordState,
        target: WordState
    ) -> List[MemoryStatus]:
        """
        Get feedback options that would cause transition to target state.

        Args:
            current: Current state
            target: Target state

        Returns:
            List of MemoryStatus values that lead to target
        """
        feedback_options = []

        for feedback, (next_state, _) in self.TRANSITIONS.get(current, {}).items():
            if next_state == target:
                feedback_options.append(feedback)

        return feedback_options

    def get_state_progress(self, state: WordState) -> Dict[str, any]:
        """
        Get progress information for a state.

        Args:
            state: State to query

        Returns:
            Dictionary with progress information
        """
        progress = {
            "state": state.value,
            "consecutive_count": self.consecutive_counts.get(state, 0),
        }

        # Add requirement info if applicable
        for feedback, (next_state, required) in self.TRANSITIONS.get(state, {}).items():
            if next_state != state and required is not None:
                progress["next_state"] = next_state.value
                progress["required_consecutive"] = required
                progress["required_feedback"] = feedback.value
                break

        return progress


class ProgressTracker:
    """
    Tracks overall learning progress across multiple words.
    """

    def __init__(self):
        """Initialize progress tracker"""
        self.state_counts: Dict[WordState, int] = {
            WordState.NEW: 0,
            WordState.LEARNING: 0,
            WordState.REVIEW: 0,
            WordState.MASTERED: 0,
        }

    def update_state_count(self, old_state: Optional[WordState], new_state: WordState) -> None:
        """
        Update state counts when a word changes state.

        Args:
            old_state: Previous state (None for new words)
            new_state: New state
        """
        if old_state is not None and old_state in self.state_counts:
            self.state_counts[old_state] -= 1

        if new_state in self.state_counts:
            self.state_counts[new_state] += 1

        logger.debug(f"State counts updated: {self.get_summary()}")

    def get_summary(self) -> Dict[str, int]:
        """
        Get summary of word distribution across states.

        Returns:
            Dictionary mapping state names to counts
        """
        return {
            state.value: count
            for state, count in self.state_counts.items()
        }

    def get_total_words(self) -> int:
        """Get total number of tracked words"""
        return sum(self.state_counts.values())

    def get_mastered_rate(self) -> float:
        """
        Calculate mastery rate.

        Returns:
            Fraction of words in MASTERED state
        """
        total = self.get_total_words()
        if total == 0:
            return 0.0
        mastered = self.state_counts.get(WordState.MASTERED, 0)
        return mastered / total

    def get_learning_progress(self) -> float:
        """
        Calculate overall learning progress.

        Weights: NEW=0, LEARNING=0.3, REVIEW=0.6, MASTERED=1.0

        Returns:
            Overall progress fraction [0, 1]
        """
        weights = {
            WordState.NEW: 0.0,
            WordState.LEARNING: 0.3,
            WordState.REVIEW: 0.6,
            WordState.MASTERED: 1.0,
        }

        total = self.get_total_words()
        if total == 0:
            return 0.0

        weighted_sum = sum(
            count * weights[state]
            for state, count in self.state_counts.items()
        )

        return weighted_sum / total


# Global instances
_state_machine_instance: Optional[WordStateMachine] = None
_progress_tracker_instance: Optional[ProgressTracker] = None


def get_state_machine() -> WordStateMachine:
    """Get the global state machine instance"""
    global _state_machine_instance
    if _state_machine_instance is None:
        _state_machine_instance = WordStateMachine()
    return _state_machine_instance


def get_progress_tracker() -> ProgressTracker:
    """Get the global progress tracker instance"""
    global _progress_tracker_instance
    if _progress_tracker_instance is None:
        _progress_tracker_instance = ProgressTracker()
    return _progress_tracker_instance
