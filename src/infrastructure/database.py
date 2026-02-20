"""
Database Manager for EnglishStudy application

Handles SQLite database initialization, connections, and CRUD operations.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from datetime import datetime
from config import config
from src.infrastructure.logger import get_logger, log_exception


logger = get_logger(__name__)


class DatabaseManager:
    """
    SQLite database manager with connection pooling and error handling.

    Usage:
        db = DatabaseManager()
        db.init_database()

        with db.get_connection() as conn:
            result = db.get_word_record(conn, record_id=1)
    """

    # SQL schema definitions
    SQL_CREATE_USERS = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            level VARCHAR(20) NOT NULL DEFAULT 'elementary',
            rating FLOAT DEFAULT 1000.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """

    SQL_CREATE_VOCABULARIES = """
        CREATE TABLE IF NOT EXISTS vocabularies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word VARCHAR(100) NOT NULL UNIQUE,
            phonetic VARCHAR(100),
            definition TEXT NOT NULL,
            example TEXT,
            difficulty INTEGER DEFAULT 1,
            frequency INTEGER DEFAULT 1,
            category VARCHAR(50)
        );
    """

    SQL_CREATE_WORD_RECORDS = """
        CREATE TABLE IF NOT EXISTS word_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vocabulary_id INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'unknown',
            easiness FLOAT DEFAULT 2.5,
            interval INTEGER DEFAULT 0,
            repetitions INTEGER DEFAULT 0,
            next_review TIMESTAMP,
            last_review TIMESTAMP,
            state VARCHAR(20) DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (vocabulary_id) REFERENCES vocabularies(id),
            UNIQUE(user_id, vocabulary_id)
        );
    """

    SQL_CREATE_MISTAKE_BOOK = """
        CREATE TABLE IF NOT EXISTS mistake_book (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            word_record_id INTEGER NOT NULL UNIQUE,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (word_record_id) REFERENCES word_records(id)
        );
    """

    SQL_CREATE_NEW_WORD_BOOK = """
        CREATE TABLE IF NOT EXISTS new_word_book (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            word_record_id INTEGER NOT NULL UNIQUE,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (word_record_id) REFERENCES word_records(id)
        );
    """

    SQL_CREATE_STUDY_SESSIONS = """
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            words_studied INTEGER DEFAULT 0,
            correct_rate FLOAT DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """

    SQL_CREATE_INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_word_records_next_review ON word_records(next_review);",
        "CREATE INDEX IF NOT EXISTS idx_word_records_user_vocab ON word_records(user_id, vocabulary_id);",
        "CREATE INDEX IF NOT EXISTS idx_mistake_book_user ON mistake_book(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_new_word_book_user ON new_word_book(user_id);",
    ]

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to database file (default: from config)
        """
        self.db_path = db_path or config.db_path
        self._ensure_user_data_dir()

    def _ensure_user_data_dir(self) -> None:
        """Ensure user data directory exists"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Database path: {self.db_path}")

    @contextmanager
    def get_connection(self):
        """
        Get a database connection with automatic cleanup.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=config.DB_TIMEOUT
            )
            conn.row_factory = sqlite3.Row  # Enable column access by name
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
            logger.debug("Database connection established")
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
                logger.debug("Database connection closed")

    @log_exception(logger)
    def init_database(self) -> bool:
        """
        Initialize database schema.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                # Create tables
                conn.execute(self.SQL_CREATE_USERS)
                conn.execute(self.SQL_CREATE_VOCABULARIES)
                conn.execute(self.SQL_CREATE_WORD_RECORDS)
                conn.execute(self.SQL_CREATE_MISTAKE_BOOK)
                conn.execute(self.SQL_CREATE_NEW_WORD_BOOK)
                conn.execute(self.SQL_CREATE_STUDY_SESSIONS)

                # Create indexes
                for index_sql in self.SQL_CREATE_INDEXES:
                    conn.execute(index_sql)

                conn.commit()
                logger.info("Database schema initialized successfully")
                return True

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

    # ========== User Operations ==========

    @log_exception(logger)
    def create_user(self, name: str, level: str = "elementary") -> Optional[int]:
        """
        Create a new user.

        Args:
            name: User name
            level: User proficiency level

        Returns:
            User ID if successful, None otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (name, level) VALUES (?, ?)",
                (name, level)
            )
            conn.commit()
            user_id = cursor.lastrowid
            logger.info(f"Created user: {name} (ID: {user_id}, Level: {level})")
            return user_id

    @log_exception(logger)
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @log_exception(logger)
    def update_user_rating(self, user_id: int, rating: float) -> bool:
        """Update user ELO rating"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users SET rating = ? WHERE id = ?",
                (rating, user_id)
            )
            conn.commit()
            logger.debug(f"Updated user {user_id} rating to {rating}")
            return True

    # ========== Vocabulary Operations ==========

    @log_exception(logger)
    def insert_vocabulary(self, vocab_data: Dict[str, Any]) -> Optional[int]:
        """
        Insert a vocabulary entry.

        Args:
            vocab_data: Dictionary with keys: word, phonetic, definition,
                       example, difficulty, frequency, category

        Returns:
            Vocabulary ID if successful, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT OR REPLACE INTO vocabularies
                    (word, phonetic, definition, example, difficulty, frequency, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        vocab_data.get("word"),
                        vocab_data.get("phonetic"),
                        vocab_data.get("definition", ""),
                        vocab_data.get("example"),
                        vocab_data.get("difficulty", 1),
                        vocab_data.get("frequency", 1),
                        vocab_data.get("category")
                    )
                )
                conn.commit()
                vocab_id = cursor.lastrowid
                logger.debug(f"Inserted vocabulary: {vocab_data.get('word')} (ID: {vocab_id})")
                return vocab_id
        except sqlite3.IntegrityError:
            # Word already exists, get its ID
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT id FROM vocabularies WHERE word = ?",
                    (vocab_data.get("word"),)
                )
                row = cursor.fetchone()
                return row["id"] if row else None

    @log_exception(logger)
    def get_vocabulary_by_word(self, word: str) -> Optional[Dict[str, Any]]:
        """Get vocabulary entry by word"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM vocabularies WHERE word = ?",
                (word,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @log_exception(logger)
    def get_vocabulary_by_id(self, vocab_id: int) -> Optional[Dict[str, Any]]:
        """Get vocabulary entry by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM vocabularies WHERE id = ?",
                (vocab_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @log_exception(logger)
    def get_vocabularies_by_difficulty(
        self,
        difficulty: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get vocabularies by difficulty level"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM vocabularies WHERE difficulty = ? LIMIT ?",
                (difficulty, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ========== Word Record Operations ==========

    @log_exception(logger)
    def get_or_create_word_record(
        self,
        user_id: int,
        vocabulary_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing word record or create a new one.

        Args:
            user_id: User ID
            vocabulary_id: Vocabulary ID

        Returns:
            Word record dictionary
        """
        with self.get_connection() as conn:
            # Try to get existing record
            cursor = conn.execute(
                """
                SELECT * FROM word_records
                WHERE user_id = ? AND vocabulary_id = ?
                """,
                (user_id, vocabulary_id)
            )
            row = cursor.fetchone()

            if row:
                return dict(row)

            # Create new record
            cursor = conn.execute(
                """
                INSERT INTO word_records (user_id, vocabulary_id)
                VALUES (?, ?)
                """,
                (user_id, vocabulary_id)
            )
            conn.commit()

            cursor = conn.execute(
                "SELECT * FROM word_records WHERE id = ?",
                (cursor.lastrowid,)
            )
            return dict(cursor.fetchone())

    @log_exception(logger)
    def update_word_record(
        self,
        record_id: int,
        status: str,
        easiness: float,
        interval: int,
        repetitions: int,
        next_review: Optional[str] = None,
        state: str = "learning"
    ) -> bool:
        """
        Update word record after study.

        Args:
            record_id: Word record ID
            status: Memory status (easy/medium/hard)
            easiness: SM-2 easiness factor
            interval: Review interval in days
            repetitions: Number of repetitions
            next_review: Next review date (ISO format string)
            state: Learning state (new/learning/review/mastered)

        Returns:
            True if successful
        """
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE word_records
                SET status = ?, easiness = ?, interval = ?,
                    repetitions = ?, next_review = ?, state = ?,
                    last_review = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, easiness, interval, repetitions, next_review, state, record_id)
            )
            conn.commit()
            logger.debug(f"Updated word record {record_id}: status={status}, interval={interval}")
            return True

    @log_exception(logger)
    def get_due_words(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get words due for review.

        Args:
            user_id: User ID

        Returns:
            List of word records with vocabulary data
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT wr.*, v.word, v.phonetic, v.definition, v.example, v.difficulty, v.id as vocab_id
                FROM word_records wr
                JOIN vocabularies v ON wr.vocabulary_id = v.id
                WHERE wr.user_id = ?
                  AND wr.next_review IS NOT NULL
                  AND wr.next_review <= datetime('now')
                  AND wr.state != 'mastered'
                ORDER BY wr.next_review ASC
                """,
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    @log_exception(logger)
    def get_new_words(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get new words for the user to learn.

        Args:
            user_id: User ID
            limit: Maximum number of words to return

        Returns:
            List of vocabulary entries not yet studied
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT v.*
                FROM vocabularies v
                LEFT JOIN word_records wr
                    ON v.id = wr.vocabulary_id AND wr.user_id = ?
                WHERE wr.id IS NULL
                LIMIT ?
                """,
                (user_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ========== Mistake Book Operations ==========

    @log_exception(logger)
    def add_to_mistake_book(
        self,
        user_id: int,
        word_record_id: int,
        note: str = ""
    ) -> bool:
        """Add a word to the mistake book"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO mistake_book
                    (user_id, word_record_id, note)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, word_record_id, note)
                )
                conn.commit()
                logger.debug(f"Added word record {word_record_id} to mistake book")
                return True
        except sqlite3.IntegrityError:
            logger.debug(f"Word record {word_record_id} already in mistake book")
            return True

    @log_exception(logger)
    def get_mistake_book(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all entries in the mistake book"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT mb.*, wr.user_id, v.word, v.definition
                FROM mistake_book mb
                JOIN word_records wr ON mb.word_record_id = wr.id
                JOIN vocabularies v ON wr.vocabulary_id = v.id
                WHERE mb.user_id = ?
                ORDER BY mb.created_at DESC
                """,
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ========== New Word Book Operations ==========

    @log_exception(logger)
    def add_to_new_word_book(
        self,
        user_id: int,
        word_record_id: int,
        note: str = ""
    ) -> bool:
        """Add a word to the new word book"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO new_word_book
                    (user_id, word_record_id, note)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, word_record_id, note)
                )
                conn.commit()
                logger.debug(f"Added word record {word_record_id} to new word book")
                return True
        except sqlite3.IntegrityError:
            logger.debug(f"Word record {word_record_id} already in new word book")
            return True

    @log_exception(logger)
    def get_new_word_book(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all entries in the new word book"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT nwb.*, wr.user_id, v.word, v.definition
                FROM new_word_book nwb
                JOIN word_records wr ON nwb.word_record_id = wr.id
                JOIN vocabularies v ON wr.vocabulary_id = v.id
                WHERE nwb.user_id = ?
                ORDER BY nwb.created_at DESC
                """,
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ========== Study Session Operations ==========

    @log_exception(logger)
    def create_study_session(self, user_id: int) -> Optional[int]:
        """Create a new study session"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO study_sessions (user_id, start_time)
                VALUES (?, datetime('now'))
                """,
                (user_id,)
            )
            conn.commit()
            session_id = cursor.lastrowid
            logger.info(f"Created study session {session_id} for user {user_id}")
            return session_id

    @log_exception(logger)
    def end_study_session(
        self,
        session_id: int,
        words_studied: int,
        correct_rate: float
    ) -> bool:
        """End a study session with statistics"""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE study_sessions
                SET end_time = datetime('now'),
                    words_studied = ?,
                    correct_rate = ?
                WHERE id = ?
                """,
                (words_studied, correct_rate, session_id)
            )
            conn.commit()
            logger.info(f"Ended session {session_id}: {words_studied} words, {correct_rate:.2%} correct")
            return True

    @log_exception(logger)
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get overall user statistics"""
        with self.get_connection() as conn:
            # Total words studied
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM word_records WHERE user_id = ? AND status != 'unknown'",
                (user_id,)
            )
            total_studied = cursor.fetchone()["count"]

            # Mastered words
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM word_records WHERE user_id = ? AND state = 'mastered'",
                (user_id,)
            )
            mastered = cursor.fetchone()["count"]

            # Due for review
            cursor = conn.execute(
                """
                SELECT COUNT(*) as count FROM word_records
                WHERE user_id = ?
                  AND next_review IS NOT NULL
                  AND next_review <= datetime('now')
                """,
                (user_id,)
            )
            due = cursor.fetchone()["count"]

            return {
                "total_studied": total_studied,
                "mastered": mastered,
                "due_for_review": due,
            }


# Global database instance
_db_instance: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Get the global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
        _db_instance.init_database()
    return _db_instance
