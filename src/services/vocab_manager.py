"""
Vocabulary Manager Service

Manages vocabulary loading, importing, and database operations.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from config import config
from src.models.vocabulary import Vocabulary, VocabularySet
from src.infrastructure.database import DatabaseManager
from src.infrastructure.vocab_loader import VocabLoader
from src.infrastructure.logger import get_logger, log_exception

logger = get_logger(__name__)


class VocabularyManager:
    """
    Service for managing vocabulary data.

    Handles:
    - Loading vocabulary files
    - Importing to database
    - Querying vocabulary by difficulty
    - Managing multiple vocabulary sets
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        vocab_loader: Optional[VocabLoader] = None
    ):
        """
        Initialize vocabulary manager.

        Args:
            db_manager: Database manager instance
            vocab_loader: Vocabulary loader instance
        """
        self.db = db_manager
        self.loader = vocab_loader or VocabLoader()

    @log_exception(logger)
    def load_vocabulary_file(self, file_path: str) -> VocabularySet:
        """
        Load vocabulary from file.

        Args:
            file_path: Path to vocabulary file

        Returns:
            VocabularySet with loaded words
        """
        words_data = self.loader.load_vocabulary(file_path)
        words = [Vocabulary(id=None, **data) for data in words_data]

        vocab_set = VocabularySet(
            name=Path(file_path).stem,
            words=words,
            description=f"Loaded from {file_path}"
        )

        logger.info(f"Loaded vocabulary set: {vocab_set.name} ({len(words)} words)")
        return vocab_set

    @log_exception(logger)
    def import_vocabulary_to_db(self, vocab_set: VocabularySet) -> Dict[str, int]:
        """
        Import vocabulary set to database.

        Args:
            vocab_set: VocabularySet to import

        Returns:
            Dictionary with import statistics
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        imported = 0
        updated = 0
        errors = 0

        for vocab in vocab_set.words:
            try:
                vocab_data = {
                    "word": vocab.word,
                    "phonetic": vocab.phonetic,
                    "definition": vocab.definition,
                    "example": vocab.example,
                    "difficulty": vocab.difficulty,
                    "frequency": vocab.frequency,
                    "category": vocab.category,
                }

                vocab_id = self.db.insert_vocabulary(vocab_data)
                if vocab_id is not None:
                    imported += 1
                else:
                    updated += 1

            except Exception as e:
                logger.error(f"Failed to import word '{vocab.word}': {e}")
                errors += 1

        stats = {
            "imported": imported,
            "updated": updated,
            "errors": errors,
            "total": len(vocab_set.words)
        }

        logger.info(f"Import completed: {stats}")
        return stats

    @log_exception(logger)
    def get_available_vocabularies(self) -> List[Dict[str, str]]:
        """
        Get list of available vocabulary files.

        Returns:
            List of vocabulary file info dictionaries
        """
        return self.loader.get_available_vocabularies()

    @log_exception(logger)
    def get_vocabulary_by_id(self, vocab_id: int) -> Optional[Vocabulary]:
        """
        Get vocabulary by database ID.

        Args:
            vocab_id: Vocabulary ID in database

        Returns:
            Vocabulary object or None
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        data = self.db.get_vocabulary_by_id(vocab_id)
        if data is None:
            return None

        return Vocabulary.from_dict(data)

    @log_exception(logger)
    def get_vocabulary_by_word(self, word: str) -> Optional[Vocabulary]:
        """
        Get vocabulary by word text.

        Args:
            word: Word to look up

        Returns:
            Vocabulary object or None
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        data = self.db.get_vocabulary_by_word(word)
        if data is None:
            return None

        return Vocabulary.from_dict(data)

    @log_exception(logger)
    def get_vocabularies_by_difficulty(
        self,
        difficulty: int,
        limit: int = 100
    ) -> List[Vocabulary]:
        """
        Get vocabularies filtered by difficulty.

        Args:
            difficulty: Difficulty level (1-10)
            limit: Maximum number to return

        Returns:
            List of Vocabulary objects
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        data_list = self.db.get_vocabularies_by_difficulty(difficulty, limit)
        return [Vocabulary.from_dict(data) for data in data_list]

    @log_exception(logger)
    def search_vocabularies(
        self,
        query: str,
        limit: int = 50
    ) -> List[Vocabulary]:
        """
        Search vocabularies by word or definition.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching Vocabulary objects
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM vocabularies
                WHERE word LIKE ? OR definition LIKE ?
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", limit)
            )
            results = [dict(row) for row in cursor.fetchall()]

        return [Vocabulary.from_dict(data) for data in results]

    @log_exception(logger)
    def get_random_words(
        self,
        count: int = 10,
        min_difficulty: int = 1,
        max_difficulty: int = 10
    ) -> List[Vocabulary]:
        """
        Get random vocabulary words within difficulty range.

        Args:
            count: Number of words to return
            min_difficulty: Minimum difficulty level
            max_difficulty: Maximum difficulty level

        Returns:
            List of Vocabulary objects
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM vocabularies
                WHERE difficulty BETWEEN ? AND ?
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (min_difficulty, max_difficulty, count)
            )
            results = [dict(row) for row in cursor.fetchall()]

        return [Vocabulary.from_dict(data) for data in results]

    @log_exception(logger)
    def validate_vocabulary_file(self, file_path: str) -> bool:
        """
        Validate if a vocabulary file is valid.

        Args:
            file_path: Path to vocabulary file

        Returns:
            True if valid
        """
        return self.loader.validate_format(file_path)

    @log_exception(logger)
    def export_user_vocabulary(
        self,
        user_id: int,
        output_path: str,
        include_mastered: bool = False
    ) -> bool:
        """
        Export user's vocabulary to file.

        Args:
            user_id: User ID
            output_path: Output file path
            include_mastered: Whether to include mastered words

        Returns:
            True if successful
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        with self.db.get_connection() as conn:
            query = """
                SELECT v.*, wr.status, wr.state
                FROM vocabularies v
                JOIN word_records wr ON v.id = wr.vocabulary_id
                WHERE wr.user_id = ?
            """
            params = [user_id]

            if not include_mastered:
                query += " AND wr.state != 'mastered'"

            cursor = conn.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

        # Convert to VocabularySet
        words = []
        for data in results:
            vocab_data = {
                "id": data["id"],
                "word": data["word"],
                "phonetic": data["phonetic"],
                "definition": data["definition"],
                "example": data["example"],
                "difficulty": data["difficulty"],
                "frequency": data["frequency"],
                "category": data["category"],
            }
            words.append(Vocabulary(id=None, **vocab_data))

        vocab_set = VocabularySet(
            name=f"user_{user_id}_vocabulary",
            words=words,
            description=f"Vocabulary for user {user_id}"
        )

        return self.loader.export_to_json(
            [w.to_dict() for w in words],
            output_path,
            meta={
                "name": f"User {user_id} Vocabulary",
                "user_id": user_id,
                "total_words": len(words),
            }
        )

    @log_exception(logger)
    def get_difficulty_distribution(self) -> Dict[int, int]:
        """
        Get count of words at each difficulty level.

        Returns:
            Dictionary mapping difficulty -> count
        """
        if self.db is None:
            raise RuntimeError("Database manager not configured")

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT difficulty, COUNT(*) as count
                FROM vocabularies
                GROUP BY difficulty
                ORDER BY difficulty
                """
            )
            return {row["difficulty"]: row["count"] for row in cursor.fetchall()}

    @log_exception(logger)
    def initialize_builtin_vocabularies(self) -> Dict[str, Any]:
        """
        Initialize built-in vocabulary sets.

        Returns:
            Import statistics
        """
        logger.info("Initializing built-in vocabularies...")

        stats = {
            "total_imported": 0,
            "files": []
        }

        for vocab_info in self.get_available_vocabularies():
            file_path = vocab_info["path"]
            try:
                vocab_set = self.load_vocabulary_file(file_path)
                import_stats = self.import_vocabulary_to_db(vocab_set)

                stats["total_imported"] += import_stats["imported"]
                stats["files"].append({
                    "name": vocab_info["name"],
                    "stats": import_stats
                })

                logger.info(
                    f"Imported {vocab_info['name']}: "
                    f"{import_stats['imported']} words"
                )

            except Exception as e:
                logger.error(f"Failed to import {vocab_info['name']}: {e}")
                stats["files"].append({
                    "name": vocab_info["name"],
                    "error": str(e)
                })

        return stats


# Global instance
_vocab_manager_instance: Optional[VocabularyManager] = None


def get_vocab_manager() -> VocabularyManager:
    """Get the global vocabulary manager instance"""
    global _vocab_manager_instance
    if _vocab_manager_instance is None:
        from src.infrastructure.database import get_db
        _vocab_manager_instance = VocabularyManager(db_manager=get_db())
    return _vocab_manager_instance
