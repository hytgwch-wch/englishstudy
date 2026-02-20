"""
Test Manager Service

Manages test creation, execution, and scoring.
"""

import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from config import config
from src.models.user import User
from src.models.vocabulary import Vocabulary
from src.models.session import StudySession, TestQuestion, TestResult
from src.models.word_record import MemoryStatus
from src.infrastructure.database import DatabaseManager
from src.infrastructure.logger import get_logger, log_exception

logger = get_logger(__name__)


class TestType(Enum):
    """Types of tests"""
    MULTIPLE_CHOICE = "multiple_choice"  # 单选题
    SPELLING = "spelling"                # 拼写题
    DEFINITION = "definition"            # 释义匹配
    MIXED = "mixed"                      # 混合题型

    @classmethod
    def display_name(cls, test_type: str) -> str:
        """Get display name for test type"""
        names = {
            cls.MULTIPLE_CHOICE.value: "单选题",
            cls.SPELLING.value: "拼写题",
            cls.DEFINITION.value: "释义匹配",
            cls.MIXED.value: "混合题型",
        }
        return names.get(test_type, test_type)


class TestManager:
    """
    Service for creating and managing vocabulary tests.

    Handles:
    - Generating test questions
    - Administering tests
    - Scoring and results
    - Test history
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize test manager.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.current_test: Optional[TestResult] = None
        self.current_session: Optional[StudySession] = None

    @log_exception(logger)
    def generate_test(
        self,
        user: User,
        word_count: int = None,
        test_type: str = "mixed",
        difficulty: Optional[int] = None,
        difficulty_range: Optional[tuple[int, int]] = None
    ) -> List[TestQuestion]:
        """
        Generate a test with the specified parameters.

        Args:
            user: User taking the test
            word_count: Number of questions (default: from config)
            test_type: Type of test
            difficulty: Specific difficulty level (optional)
            difficulty_range: Difficulty range (min, max) (optional)

        Returns:
            List of TestQuestion objects
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        word_count = word_count or config.DEFAULT_TEST_QUESTIONS

        # Get vocabulary words for the test
        words = self._get_test_vocabulary(
            user,
            word_count,
            difficulty,
            difficulty_range
        )

        if not words:
            logger.warning(f"No vocabulary available for test (user {user.id})")
            return []

        # Generate questions based on type
        questions = []

        if test_type == TestType.MIXED.value:
            # Mix different question types
            for word in words:
                q_type = random.choice([
                    TestType.MULTIPLE_CHOICE.value,
                    TestType.SPELLING.value,
                    TestType.DEFINITION.value
                ])
                question = self._create_question(word, q_type)
                if question:
                    questions.append(question)
        else:
            for word in words:
                question = self._create_question(word, test_type)
                if question:
                    questions.append(question)

        random.shuffle(questions)

        logger.info(
            f"Generated test: {len(questions)} questions, "
            f"type={test_type}, user={user.id}"
        )

        return questions

    def _get_test_vocabulary(
        self,
        user: User,
        count: int,
        difficulty: Optional[int],
        difficulty_range: Optional[tuple[int, int]]
    ) -> List[Dict[str, Any]]:
        """Get vocabulary words for testing"""
        if self.db is None:
            return []

        # Determine difficulty parameters
        if difficulty is not None:
            min_diff, max_diff = difficulty, difficulty
        elif difficulty_range is not None:
            min_diff, max_diff = difficulty_range
        else:
            # Use user's recommended difficulty range
            from src.services.study_manager import get_study_manager
            from src.core.difficulty import get_difficulty_adapter

            study_mgr = get_study_manager()
            diff_adapter = get_difficulty_adapter()

            min_diff, max_diff = diff_adapter.get_difficulty_range(user.rating)

        # Get words - prefer words user has studied
        with self.db.get_connection() as conn:
            # Try to get studied words first
            cursor = conn.execute(
                """
                SELECT v.*, wr.state
                FROM vocabularies v
                JOIN word_records wr ON v.id = wr.vocabulary_id
                WHERE wr.user_id = ?
                  AND v.difficulty BETWEEN ? AND ?
                  AND wr.state != 'new'
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (user.id, min_diff, max_diff, count)
            )
            words = [dict(row) for row in cursor.fetchall()]

            # If not enough studied words, get new ones
            if len(words) < count:
                remaining = count - len(words)
                cursor = conn.execute(
                    """
                    SELECT * FROM vocabularies
                    WHERE difficulty BETWEEN ? AND ?
                      AND id NOT IN (
                          SELECT vocabulary_id FROM word_records
                          WHERE user_id = ?
                      )
                    ORDER BY RANDOM()
                    LIMIT ?
                    """,
                    (min_diff, max_diff, user.id, remaining)
                )
                words.extend([dict(row) for row in cursor.fetchall()])

        return words[:count]

    def _create_question(
        self,
        vocab: Dict[str, Any],
        question_type: str
    ) -> Optional[TestQuestion]:
        """Create a single test question"""
        word = vocab["word"]
        definition = vocab["definition"]
        vocab_id = vocab["id"]

        if question_type == TestType.MULTIPLE_CHOICE.value:
            return self._create_multiple_choice(vocab_id, word, definition, vocab["difficulty"])

        elif question_type == TestType.SPELLING.value:
            return TestQuestion(
                vocabulary_id=vocab_id,
                question_type=TestType.SPELLING.value,
                question=f"请拼写单词：{definition}",
                correct_answer=word
            )

        elif question_type == TestType.DEFINITION.value:
            return TestQuestion(
                vocabulary_id=vocab_id,
                question_type=TestType.DEFINITION.value,
                question=f"'{word}' 的中文释义是？",
                correct_answer=definition
            )

        return None

    def _create_multiple_choice(
        self,
        vocab_id: int,
        word: str,
        definition: str,
        difficulty: int
    ) -> TestQuestion:
        """Create a multiple choice question"""
        # Get distractors
        distractors = self._get_distractors(word, definition, difficulty, count=3)

        # Combine correct answer with distractors
        options = [definition] + distractors
        random.shuffle(options)

        # Format question with options
        options_text = "\n".join([
            f"{chr(65 + i)}. {opt}"  # A., B., C., D.
            for i, opt in enumerate(options)
        ])

        return TestQuestion(
            vocabulary_id=vocab_id,
            question_type=TestType.MULTIPLE_CHOICE.value,
            question=f"'{word}' 的中文释义是：\n\n{options_text}",
            correct_answer=definition
        )

    def _get_distractors(
        self,
        correct_word: str,
        correct_definition: str,
        difficulty: int,
        count: int = 3
    ) -> List[str]:
        """Get distractor definitions for multiple choice"""
        if self.db is None:
            return []

        with self.db.get_connection() as conn:
            # Get similar difficulty words
            cursor = conn.execute(
                """
                SELECT definition FROM vocabularies
                WHERE id != ?
                  AND difficulty BETWEEN ? AND ?
                  AND word != ?
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (correct_word, max(1, difficulty - 1), min(10, difficulty + 1), correct_word, count)
            )
            return [row["definition"] for row in cursor.fetchall()]

    @log_exception(logger)
    def start_test(self, user: User, questions: List[TestQuestion]) -> TestResult:
        """
        Start a new test session.

        Args:
            user: User taking the test
            questions: List of test questions

        Returns:
            TestResult object
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        # Create study session for tracking
        session_id = self.db.create_study_session(user.id)

        self.current_session = StudySession(
            id=session_id,
            user_id=user.id,
            session_type="test",
            start_time=datetime.now()
        )

        self.current_test = TestResult(
            session_id=session_id,
            total_questions=len(questions),
            correct_answers=0,
            questions=questions
        )

        logger.info(
            f"Started test session {session_id} "
            f"with {len(questions)} questions for user {user.id}"
        )

        return self.current_test

    @log_exception(logger)
    def submit_answer(
        self,
        question: TestQuestion,
        user_answer: str,
        time_taken: Optional[int] = None
    ) -> bool:
        """
        Submit an answer to a test question.

        Args:
            question: Test question being answered
            user_answer: User's answer
            time_taken: Time taken in seconds (optional)

        Returns:
            Whether the answer was correct
        """
        is_correct = question.answer(user_answer, time_taken)

        if self.current_test is not None:
            if is_correct:
                self.current_test.correct_answers += 1
            if time_taken:
                self.current_test.total_time += time_taken

        if self.current_session is not None:
            self.current_session.record_attempt(is_correct)

        logger.debug(f"Answer submitted: correct={is_correct}, time={time_taken}s")
        return is_correct

    @log_exception(logger)
    def finish_test(self, user: User) -> Optional[TestResult]:
        """
        Finish the current test and calculate results.

        Args:
            user: User who took the test

        Returns:
            TestResult with final scores
        """
        if self.current_test is None or self.current_session is None:
            return None

        # End the session
        self.current_session.end()

        if self.db is not None:
            self.db.end_study_session(
                self.current_session.id,
                self.current_session.words_studied,
                self.current_session.correct_rate
            )

        result = self.current_test
        self.current_test = None
        self.current_session = None

        logger.info(
            f"Test completed: session_id={result.session_id}, "
            f"score={result.score:.1f}%, passed={result.passed}"
        )

        return result

    @log_exception(logger)
    def get_test_history(self, user: User, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get user's test history.

        Args:
            user: User to get history for
            limit: Maximum number of entries

        Returns:
            List of test session records
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM study_sessions
                WHERE user_id = ? AND start_time IN (
                    SELECT start_time FROM study_sessions
                    WHERE user_id = ?
                    ORDER BY start_time DESC
                    LIMIT ?
                )
                ORDER BY start_time DESC
                """,
                (user.id, user.id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]


# Global instance
_test_manager_instance: Optional[TestManager] = None


def get_test_manager() -> TestManager:
    """Get the global test manager instance"""
    global _test_manager_instance
    if _test_manager_instance is None:
        from src.infrastructure.database import get_db
        _test_manager_instance = TestManager(db_manager=get_db())
    return _test_manager_instance
