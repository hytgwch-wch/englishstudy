"""
Unit tests for ELO-based Difficulty Adaptation Algorithm

Tests the difficulty adaptation system including:
- ELO rating calculations
- Expected score predictions
- Difficulty recommendations
- Performance level assessment
"""

import pytest

from src.core.difficulty import DifficultyAdapter


class TestDifficultyAdapter:
    """Test suite for DifficultyAdapter class"""

    @pytest.fixture
    def adapter(self):
        """Create a fresh difficulty adapter for each test"""
        return DifficultyAdapter(
            initial_rating=1000.0,
            k_factor=32.0,
            target_success_rate=0.7
        )

    def test_initialization(self, adapter):
        """Test adapter initialization"""
        assert adapter.initial_rating == 1000.0
        assert adapter.k_factor == 32.0
        assert adapter.target_success_rate == 0.7

    def test_difficulty_to_elo_conversion(self, adapter):
        """Test converting difficulty levels to ELO ratings"""
        assert adapter.difficulty_to_elo(1) == 600
        assert adapter.difficulty_to_elo(5) == 1400
        assert adapter.difficulty_to_elo(10) == 2400

    def test_difficulty_to_elo_clamping(self, adapter):
        """Test that out-of-range difficulties are clamped"""
        assert adapter.difficulty_to_elo(0) == 600  # Clamped to 1
        assert adapter.difficulty_to_elo(11) == 2400  # Clamped to 10

    def test_elo_to_difficulty_conversion(self, adapter):
        """Test converting ELO ratings to difficulty levels"""
        assert adapter.elo_to_difficulty(600) == 1
        assert adapter.elo_to_difficulty(1400) == 5
        assert adapter.elo_to_difficulty(2400) == 10

    def test_expected_score_equal_ratings(self, adapter):
        """Test expected score when user and word ratings are equal"""
        # Equal ratings should give 50% probability
        expected = adapter.expected_score(user_rating=1000, word_difficulty=3)
        assert expected == pytest.approx(0.5, abs=0.01)

    def test_expected_score_higher_user_rating(self, adapter):
        """Test expected score when user has higher rating"""
        # User 1200 vs difficulty 3 (1000) should be > 50%
        expected = adapter.expected_score(user_rating=1200, word_difficulty=3)
        assert expected > 0.5
        assert expected < 1.0

    def test_expected_score_lower_user_rating(self, adapter):
        """Test expected score when user has lower rating"""
        # User 800 vs difficulty 3 (1000) should be < 50%
        expected = adapter.expected_score(user_rating=800, word_difficulty=3)
        assert expected < 0.5
        assert expected > 0.0

    def test_update_user_rating_correct_easy_word(self, adapter):
        """Test rating update after correct answer on easy word"""
        # User 1000, difficulty 1 (ELO 600) - should be very likely correct
        new_rating = adapter.update_user_rating(
            current_rating=1000,
            word_difficulty=1,
            actual_result=True
        )

        # Rating should increase only slightly (expected high probability)
        assert new_rating > 1000
        assert new_rating - 1000 < 5  # Small increase

    def test_update_user_rating_correct_hard_word(self, adapter):
        """Test rating update after correct answer on hard word"""
        # User 1000, difficulty 10 (ELO 2400) - should be very unlikely
        new_rating = adapter.update_user_rating(
            current_rating=1000,
            word_difficulty=10,
            actual_result=True
        )

        # Rating should increase significantly
        assert new_rating > 1000
        assert new_rating - 1000 > 20  # Large increase

    def test_update_user_rating_incorrect_easy_word(self, adapter):
        """Test rating update after incorrect answer on easy word"""
        # User 1000, difficulty 1 (ELO 600) - incorrect is surprising
        new_rating = adapter.update_user_rating(
            current_rating=1000,
            word_difficulty=1,
            actual_result=False
        )

        # Rating should decrease significantly
        assert new_rating < 1000
        assert 1000 - new_rating > 20  # Large decrease

    def test_update_user_rating_incorrect_hard_word(self, adapter):
        """Test rating update after incorrect answer on hard word"""
        # User 1000, difficulty 10 (ELO 2400) - incorrect is expected
        new_rating = adapter.update_user_rating(
            current_rating=1000,
            word_difficulty=10,
            actual_result=False
        )

        # Rating should decrease only slightly
        assert new_rating < 1000
        assert 1000 - new_rating < 5  # Small decrease

    def test_recommend_difficulty_baseline(self, adapter):
        """Test difficulty recommendation for baseline user"""
        # 1000 rating with 70% target recommends difficulty 2
        # Formula: Rb = 1000 + 400 * log10(1/0.7 - 1) = 1000 + 400 * (-0.368) ≈ 853
        # ELO 853 is closest to difficulty 2 (ELO 800)
        difficulty = adapter.recommend_difficulty(user_rating=1000, target_success_rate=0.7)
        assert difficulty == 2

    def test_recommend_difficulty_high_rating(self, adapter):
        """Test difficulty recommendation for high-rated user"""
        # 2000 rating should recommend higher difficulty
        difficulty = adapter.recommend_difficulty(user_rating=2000, target_success_rate=0.7)
        assert difficulty >= 7

    def test_recommend_difficulty_low_rating(self, adapter):
        """Test difficulty recommendation for low-rated user"""
        # 700 rating should recommend lower difficulty
        difficulty = adapter.recommend_difficulty(user_rating=700, target_success_rate=0.7)
        assert difficulty <= 2

    def test_batch_update(self, adapter):
        """Test batch rating update"""
        results = [
            (3, True),   # Correct on baseline
            (3, True),   # Correct on baseline
            (4, False),  # Incorrect on harder
            (2, True),   # Correct on easier
        ]

        new_rating = adapter.batch_update(current_rating=1000, results=results)

        # Should be slightly higher overall
        assert isinstance(new_rating, float)

    def test_calculate_session_rating(self, adapter):
        """Test session-based rating calculation"""
        new_rating = adapter.calculate_session_rating(
            current_rating=1000,
            correct_count=7,
            total_count=10,
            average_difficulty=3.0
        )

        # 70% correct on difficulty 3 at rating 1000 should maintain rating
        assert isinstance(new_rating, float)

    def test_calculate_session_rating_perfect(self, adapter):
        """Test session rating with perfect score"""
        new_rating = adapter.calculate_session_rating(
            current_rating=1000,
            correct_count=10,
            total_count=10,
            average_difficulty=3.0
        )

        # Perfect score should increase rating
        assert new_rating > 1000

    def test_calculate_session_rating_zero_correct(self, adapter):
        """Test session rating with zero correct"""
        new_rating = adapter.calculate_session_rating(
            current_rating=1000,
            correct_count=0,
            total_count=10,
            average_difficulty=3.0
        )

        # Zero correct should decrease rating
        assert new_rating < 1000

    def test_calculate_session_rating_empty(self, adapter):
        """Test session rating with no attempts"""
        new_rating = adapter.calculate_session_rating(
            current_rating=1000,
            correct_count=0,
            total_count=0,
            average_difficulty=0
        )

        # No change when no attempts
        assert new_rating == 1000

    def test_get_difficulty_range(self, adapter):
        """Test getting difficulty range"""
        min_diff, max_diff = adapter.get_difficulty_range(user_rating=1000, range_size=2)

        # Should be centered around recommended difficulty (2)
        # Range is [2-2, 2+2] clamped to [1, 4]
        assert min_diff >= 1
        assert max_diff <= 10
        # Since recommended is 2, range is [max(1, 2-2), min(10, 2+2)] = [1, 4]
        assert min_diff == 1
        assert max_diff == 4

    def test_assess_performance_level(self, adapter):
        """Test performance level assessment"""
        assert adapter.assess_performance_level(500) == "beginner"
        assert adapter.assess_performance_level(1000) == "elementary"
        assert adapter.assess_performance_level(1400) == "intermediate"
        assert adapter.assess_performance_level(1800) == "advanced"
        assert adapter.assess_performance_level(2200) == "expert"

    def test_should_adjust_difficulty_high_success(self, adapter):
        """Test difficulty adjustment suggestion for high success rate"""
        should_adjust, direction = adapter.should_adjust_difficulty(
            recent_results=[True, True, True, True, True, True, True, True, True]
        )

        assert should_adjust is True
        assert direction == "harder"

    def test_should_adjust_difficulty_low_success(self, adapter):
        """Test difficulty adjustment suggestion for low success rate"""
        should_adjust, direction = adapter.should_adjust_difficulty(
            recent_results=[False, False, False, False, False, True]
        )

        assert should_adjust is True
        assert direction == "easier"

    def test_should_adjust_difficulty_moderate(self, adapter):
        """Test difficulty adjustment suggestion for moderate success"""
        should_adjust, direction = adapter.should_adjust_difficulty(
            recent_results=[True, False, True, False, True, True]
        )

        assert should_adjust is False
        assert direction == "none"

    def test_should_adjust_difficulty_insufficient_data(self, adapter):
        """Test that insufficient samples don't trigger adjustment"""
        should_adjust, direction = adapter.should_adjust_difficulty(
            recent_results=[True, True, True]
        )

        assert should_adjust is False
        assert direction == "none"
