"""
Vocabulary Loader for EnglishStudy application

Handles loading vocabulary data from JSON files and user imports.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum

from config import config
from src.infrastructure.logger import get_logger, log_exception

logger = get_logger(__name__)


class VocabFormat(Enum):
    """Supported vocabulary file formats"""
    JSON = "json"
    CSV = "csv"
    TXT = "txt"


class VocabLoader:
    """
    Vocabulary loader with support for multiple file formats.

    Supported formats:
    - JSON: Structured format with full word information
    - CSV: Simple word-definition format
    - TXT: Plain text word list
    """

    # JSON schema validation
    REQUIRED_JSON_FIELDS = ["word", "definition"]
    OPTIONAL_JSON_FIELDS = ["phonetic", "example", "difficulty", "frequency", "category"]

    # Default values
    DEFAULT_DIFFICULTY = 1
    DEFAULT_FREQUENCY = 1

    def __init__(self, vocab_dir: Optional[Path] = None):
        """
        Initialize vocabulary loader.

        Args:
            vocab_dir: Path to vocabulary directory (default: from config)
        """
        self.vocab_dir = vocab_dir or config.vocab_path
        self._ensure_vocab_dir()

    def _ensure_vocab_dir(self) -> None:
        """Ensure vocabulary directory exists"""
        self.vocab_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Vocabulary directory: {self.vocab_dir}")

    @log_exception(logger)
    def load_vocabulary(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load vocabulary from file based on format.

        Args:
            file_path: Path to vocabulary file (relative or absolute)

        Returns:
            List of vocabulary dictionaries

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.vocab_dir / path

        if not path.exists():
            raise FileNotFoundError(f"Vocabulary file not found: {path}")

        # Detect format from extension
        format_map = {
            ".json": VocabFormat.JSON,
            ".csv": VocabFormat.CSV,
            ".txt": VocabFormat.TXT,
        }

        suffix = path.suffix.lower()
        if suffix not in format_map:
            raise ValueError(f"Unsupported file format: {suffix}")

        file_format = format_map[suffix]

        # Load based on format
        if file_format == VocabFormat.JSON:
            return self._load_json(path)
        elif file_format == VocabFormat.CSV:
            return self._load_csv(path)
        else:  # TXT
            return self._load_txt(path)

    @log_exception(logger)
    def _load_json(self, path: Path) -> List[Dict[str, Any]]:
        """
        Load vocabulary from JSON file.

        Expected format:
        {
            "meta": {...},
            "words": [
                {
                    "word": "abandon",
                    "phonetic": "/əˈbændən/",
                    "definition": "v. 遗弃；放弃",
                    "example": "He decided to abandon the project.",
                    "difficulty": 4,
                    "frequency": 3,
                    "category": "verb"
                },
                ...
            ]
        }
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Support both wrapped and direct array formats
        if isinstance(data, dict) and "words" in data:
            words = data["words"]
            meta = data.get("meta", {})
            logger.info(f"Loading vocabulary: {meta.get('name', path.name)}")
        elif isinstance(data, list):
            words = data
        else:
            raise ValueError("Invalid JSON format: expected object with 'words' or array")

        # Validate and normalize
        validated = []
        for i, word_data in enumerate(words):
            try:
                validated.append(self._validate_word_entry(word_data))
            except ValueError as e:
                logger.warning(f"Skipping word at index {i}: {e}")

        logger.info(f"Loaded {len(validated)} words from {path.name}")
        return validated

    @log_exception(logger)
    def _load_csv(self, path: Path) -> List[Dict[str, Any]]:
        """
        Load vocabulary from CSV file.

        Expected format (comma or tab separated):
        word,definition,phonetic,example,difficulty,frequency,category
        abandon,v. 遗弃；放弃,/əˈbændən/,He decided to abandon the project.,4,3,verb
        """
        words = []

        with open(path, "r", encoding="utf-8") as f:
            # Detect delimiter
            first_line = f.readline()
            f.seek(0)

            if "\t" in first_line:
                import csv
                reader = csv.DictReader(f, delimiter="\t")
            else:
                import csv
                reader = csv.DictReader(f)

            for row in reader:
                word_data = {
                    "word": row.get("word", "").strip(),
                    "definition": row.get("definition", "").strip(),
                    "phonetic": row.get("phonetic", "").strip() or None,
                    "example": row.get("example", "").strip() or None,
                    "difficulty": self._parse_int(row.get("difficulty", self.DEFAULT_DIFFICULTY)),
                    "frequency": self._parse_int(row.get("frequency", self.DEFAULT_FREQUENCY)),
                    "category": row.get("category", "").strip() or None,
                }
                try:
                    words.append(self._validate_word_entry(word_data))
                except ValueError as e:
                    logger.warning(f"Skipping word {word_data.get('word')}: {e}")

        logger.info(f"Loaded {len(words)} words from CSV: {path.name}")
        return words

    @log_exception(logger)
    def _load_txt(self, path: Path) -> List[Dict[str, Any]]:
        """
        Load vocabulary from plain text file.

        Expected format (one word per line):
        abandon
        ability
        academy
        ...
        Or with definition (word - definition):
        abandon - v. 遗弃；放弃
        ability - n. 能力；才能
        """
        words = []

        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):  # Skip empty and comments
                    continue

                # Try to parse as "word - definition" format
                if " - " in line:
                    word, definition = line.split(" - ", 1)
                    word_data = {
                        "word": word.strip(),
                        "definition": definition.strip(),
                    }
                else:
                    # Just the word
                    word_data = {
                        "word": line,
                        "definition": "",  # Will need to be filled later
                    }

                try:
                    words.append(self._validate_word_entry(word_data))
                except ValueError as e:
                    logger.warning(f"Skipping line {line_num}: {e}")

        logger.info(f"Loaded {len(words)} words from TXT: {path.name}")
        return words

    def _validate_word_entry(self, word_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize a word entry.

        Args:
            word_data: Raw word data dictionary

        Returns:
            Validated and normalized word data

        Raises:
            ValueError: If required fields are missing
        """
        # Check required fields
        for field in self.REQUIRED_JSON_FIELDS:
            if field not in word_data or not word_data[field]:
                raise ValueError(f"Missing required field: {field}")

        # Normalize and validate
        validated = {
            "word": word_data["word"].strip(),
            "definition": word_data["definition"].strip(),
            "phonetic": word_data.get("phonetic", "").strip() if word_data.get("phonetic") else None,
            "example": word_data.get("example", "").strip() if word_data.get("example") else None,
            "difficulty": self._parse_int(
                word_data.get("difficulty", self.DEFAULT_DIFFICULTY),
                min_val=1,
                max_val=10
            ),
            "frequency": self._parse_int(
                word_data.get("frequency", self.DEFAULT_FREQUENCY),
                min_val=1
            ),
            "category": word_data.get("category", "").strip() if word_data.get("category") else None,
        }

        return validated

    def _parse_int(self, value: Any, min_val: int = 1, max_val: int = 100) -> int:
        """Parse integer with bounds checking"""
        try:
            parsed = int(value)
            return max(min_val, min(parsed, max_val))
        except (ValueError, TypeError):
            return min_val

    @log_exception(logger)
    def validate_format(self, file_path: str) -> bool:
        """
        Validate if a vocabulary file has a valid format.

        Args:
            file_path: Path to vocabulary file

        Returns:
            True if valid, False otherwise
        """
        try:
            words = self.load_vocabulary(file_path)
            return len(words) > 0
        except Exception as e:
            logger.error(f"Format validation failed for {file_path}: {e}")
            return False

    @log_exception(logger)
    def get_available_vocabularies(self) -> List[Dict[str, str]]:
        """
        Get list of available vocabulary files.

        Returns:
            List of dictionaries with 'name', 'path', 'format', 'info'
        """
        vocabularies = []

        for path in self.vocab_dir.iterdir():
            if path.is_file() and path.suffix.lower() in [".json", ".csv", ".txt"]:
                # Try to read metadata for JSON files
                info = {}
                if path.suffix.lower() == ".json":
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, dict) and "meta" in data:
                                info = data["meta"]
                    except Exception:
                        pass

                vocabularies.append({
                    "name": path.stem,
                    "path": str(path),
                    "format": path.suffix[1:].upper(),
                    "info": info
                })

        # Sort by name
        vocabularies.sort(key=lambda x: x["name"])
        return vocabularies

    @log_exception(logger)
    def export_to_json(
        self,
        words: List[Dict[str, Any]],
        output_path: str,
        meta: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Export vocabulary list to JSON file.

        Args:
            words: List of word dictionaries
            output_path: Output file path
            meta: Optional metadata dictionary

        Returns:
            True if successful
        """
        output = {
            "meta": meta or {
                "name": "Exported Vocabulary",
                "version": "1.0",
                "total_words": len(words)
            },
            "words": words
        }

        path = Path(output_path)
        if not path.is_absolute():
            path = self.vocab_dir / path

        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported {len(words)} words to {path}")
        return True


# Global vocabulary loader instance
_vocab_loader_instance: Optional[VocabLoader] = None


def get_vocab_loader() -> VocabLoader:
    """Get the global vocabulary loader instance"""
    global _vocab_loader_instance
    if _vocab_loader_instance is None:
        _vocab_loader_instance = VocabLoader()
    return _vocab_loader_instance
