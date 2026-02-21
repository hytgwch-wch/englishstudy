"""
Unit tests for SM-2 Spaced Repetition System Algorithm

Tests the core SRS algorithm implementation including:
- Interval calculation
- Easiness factor updates
- Repetition tracking
- Study queue generation
"""

import pytest
from datetime import datetime, timedelta

from src.core.srs import SRSEngine
from src.models.word_record import MemoryStatus, WordState, WordRecord


class TestSRSEngine:
    """Test suite for SRSEngine class"""

    @pytest.fixture
    def srs_engine(self):
        """Create a fresh SRS engine for each test"""
        return SRSEngine(
            min_easiness=1.3,
            max_easiness=3.0,
            initial_easiness=2.5
        )

    def test_initialization(self, srs_engine):
        """Test engine initialization with custom parameters"""
        assert srs_engine.min_easiness == 1.3
        assert srs_engine.max_easiness == 3.0
        assert srs_engine.initial_easiness == 2.5

    def test_first_review_easy(self, srs_engine):
        """Test first review with EASY response"""
        interval, easiness, reps, next_review = srs_engine.calculate_next_review(
            current_interval=0,
            current_easiness=2.5,
            repetitions=0,
            feedback=MemoryStatus.EASY
        )

        assert interval == 1  # First interval is 1 day
        assert reps == 1
        assert 1.3 <= easiness <= 3.0
        assert isinstance(next_review, datetime)

    def test_second_review_easy(self, srs_engine):
        """Test second review with EASY response"""
        interval, easiness, reps, next_review = srs_engine.calculate_next_review(
            current_interval=1,
            current_easiness=2.5,
            repetitions=1,
            feedback=MemoryStatus.EASY
        )

        assert interval == 6  # Second interval is 6 days
        assert reps == 2

    def test_third_review_easy(self, srs_engine):
        """Test third review with EASY response (uses EF)"""
        interval, easiness, reps, next_review = srs_engine.calculate_next_review(
            current_interval=6,
            current_easiness=2.5,
            repetitions=2,
            feedback=MemoryStatus.EASY
        )

        # Third interval = previous * EF = 6 * 2.5 = 15
        assert interval == 15
        assert reps == 3

    def test_easy_response_increases_easiness(self, srs_engine):
        """Test that EASY response increases easiness factor"""
        _, new_easiness, _, _ = srs_engine.calculate_next_review(
            current_interval=1,
            current_easiness=2.5,
            repetitions=1,
            feedback=MemoryStatus.EASY
        )

        assert new_easiness > 2.5

    def test_hard_response_resets_interval(self, srs_engine):
        """Test that HARD response resets interval to 1 day"""
        interval, easiness, reps, next_review = srs_engine.calculate_next_review(
            current_interval=6,
            current_easiness=2.5,
            repetitions=2,
            feedback=MemoryStatus.HARD
        )

        assert interval == 1  # Reset to first interval
        assert reps == 0  # Repetitions reset

    def test_hard_response_decreases_easiness(self, srs_engine):
        """Test that HARD response decreases easiness factor"""
        _, new_easiness, _, _ = srs_engine.calculate_next_review(
            current_interval=1,
            current_easiness=2.5,
            repetitions=1,
            feedback=MemoryStatus.HARD
        )

        assert new_easiness < 2.5

    def test_easiness_clamping_upper(self, srs_engine):
        """Test that easiness factor is clamped at maximum"""
        # Start with maximum easiness
        _, new_easiness, _, _ = srs_engine.calculate_next_review(
            current_interval=1,
            current_easiness=3.0,
            repetitions=1,
            feedback=MemoryStatus.EASY
        )

        assert new_easiness == 3.0  # Should not exceed max

    def test_easiness_clamping_lower(self, srs_engine):
        """Test that easiness factor is clamped at minimum"""
        # Start with minimum easiness and give HARD response
        _, new_easiness, _, _ = srs_engine.calculate_next_review(
            current_interval=1,
            current_easiness=1.3,
            repetitions=1,
            feedback=MemoryStatus.HARD
        )

        assert new_easiness == 1.3  # Should not go below min

    def test_medium_response(self, srs_engine):
        """Test MEDIUM response behavior"""
        interval, easiness, reps, next_review = srs_engine.calculate_next_review(
            current_interval=1,
            current_easiness=2.5,
            repetitions=1,
            feedback=MemoryStatus.MEDIUM
        )

        assert interval == 6
        assert reps == 2
        # Medium may slightly decrease or maintain easiness
        assert 1.3 <= easiness <= 2.5

    def test_get_due_records_empty(self, srs_engine):
        """Test getting due records from empty list"""
        due = srs_engine.get_due_records([])
        assert due == []

    def test_get_due_records_filters_correctly(self, srs_engine):
        """Test that get_due_records filters correctly"""
        now = datetime.now()

        records = [
            WordRecord(
                id=1, user_id=1, vocabulary_id=1,
                next_review=now - timedelta(days=1),  # Due
                state=WordState.REVIEW
            ),
            WordRecord(
                id=2, user_id=1, vocabulary_id=2,
                next_review=now + timedelta(days=1),  # Not due
                state=WordState.REVIEW
            ),
            WordRecord(
                id=3, user_id=1, vocabulary_id=3,
                next_review=now - timedelta(hours=1),  # Due
                state=WordState.LEARNING
            ),
            WordRecord(
                id=4, user_id=1, vocabulary_id=4,
                next_review=now - timedelta(days=1),
                state=WordState.MASTERED  # Mastered, should be excluded
            ),
        ]

        due = srs_engine.get_due_records(records)
        assert len(due) == 2  # Only 2 due records (MASTERED excluded)

    def test_get_due_records_with_limit(self, srs_engine):
        """Test get_due_records with limit parameter"""
        now = datetime.now()

        records = [
            WordRecord(
                id=i, user_id=1, vocabulary_id=i,
                next_review=now - timedelta(days=1),
                state=WordState.REVIEW
            )
            for i in range(1, 11)  # 10 due records
        ]

        due = srs_engine.get_due_records(records, limit=5)
        assert len(due) == 5

    def test_get_new_records(self, srs_engine):
        """Test getting new (UNKNOWN) records"""
        records = [
            WordRecord(
                id=1, user_id=1, vocabulary_id=1,
                status=MemoryStatus.UNKNOWN
            ),
            WordRecord(
                id=2, user_id=1, vocabulary_id=2,
                status=MemoryStatus.EASY
            ),
            WordRecord(
                id=3, user_id=1, vocabulary_id=3,
                status=MemoryStatus.UNKNOWN
            ),
        ]

        new_records = srs_engine.get_new_records(records)
        assert len(new_records) == 2
        assert all(r.status == MemoryStatus.UNKNOWN for r in new_records)

    def test_get_new_records_with_limit(self, srs_engine):
        """Test get_new_records with limit"""
        records = [
            WordRecord(
                id=i, user_id=1, vocabulary_id=i,
                status=MemoryStatus.UNKNOWN
            )
            for i in range(1, 21)  # 20 new records
        ]

        new_records = srs_engine.get_new_records(records, limit=5)
        assert len(new_records) == 5

    def test_calculate_study_queue(self, srs_engine):
        """Test study queue calculation"""
        now = datetime.now()

        records = [
            # New words
            WordRecord(
                id=i, user_id=1, vocabulary_id=i,
                status=MemoryStatus.UNKNOWN
            )
            for i in range(1, 6)  # 5 new words
        ] + [
            # Due review words
            WordRecord(
                id=i, user_id=1, vocabulary_id=i,
                next_review=now - timedelta(days=1),
                state=WordState.REVIEW,
                status=MemoryStatus.EASY
            )
            for i in range(6, 11)  # 5 review words
        ]

        new_words, review_words = srs_engine.calculate_study_queue(
            records,
            max_new=20,
            max_review=50
        )

        assert len(new_words) == 5
        assert len(review_words) == 5

    def test_estimate_review_load(self, srs_engine):
        """Test review load estimation"""
        now = datetime.now()
        tomorrow = now + timedelta(days=1)

        records = [
            WordRecord(
                id=1, user_id=1, vocabulary_id=1,
                next_review=now,
                status=MemoryStatus.EASY
            ),
            WordRecord(
                id=2, user_id=1, vocabulary_id=2,
                next_review=tomorrow,
                status=MemoryStatus.EASY
            ),
        ]

        load = srs_engine.estimate_review_load(records, days_ahead=2)

        assert load[0] == 1  # Today: 1 due
        assert load[1] == 1  # Tomorrow: 1 due
        assert load[2] == 0  # Day 2: none

    def test_max_interval_clamping(self, srs_engine):
        """Test that intervals don't exceed maximum to prevent overflow"""
        # Simulate many successful reviews
        interval = 100
        easiness = 2.5

        for _ in range(10):
            interval, easiness, _, _ = srs_engine.calculate_next_review(
                current_interval=interval,
                current_easiness=easiness,
                repetitions=100,
                feedback=MemoryStatus.EASY
            )

        assert interval <= srs_engine.MAX_INTERVAL_DAYS

    def test_quality_score_mapping(self, srs_engine):
        """Test MemoryStatus to quality score mapping"""
        assert srs_engine._get_quality_score(MemoryStatus.EASY) == 5
        assert srs_engine._get_quality_score(MemoryStatus.MEDIUM) == 3
        assert srs_engine._get_quality_score(MemoryStatus.HARD) == 1
        assert srs_engine._get_quality_score(MemoryStatus.UNKNOWN) == 0
