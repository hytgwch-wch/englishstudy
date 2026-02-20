"""
Vocabulary model for EnglishStudy application

Represents a vocabulary word with its metadata.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class WordCategory(Enum):
    """Word part of speech categories"""
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PRONOUN = "pronoun"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    INTERJECTION = "interjection"
    PHRASE = "phrase"
    OTHER = "other"

    @classmethod
    def from_string(cls, value: str) -> "WordCategory":
        """Create WordCategory from string value"""
        value_lower = value.lower()
        for category in cls:
            if category.value == value_lower:
                return category
        return cls.OTHER

    @classmethod
    def display_name(cls, category: str) -> str:
        """Get display name for a category"""
        names = {
            cls.NOUN.value: "名词",
            cls.VERB.value: "动词",
            cls.ADJECTIVE.value: "形容词",
            cls.ADVERB.value: "副词",
            cls.PRONOUN.value: "代词",
            cls.PREPOSITION.value: "介词",
            cls.CONJUNCTION.value: "连词",
            cls.INTERJECTION.value: "感叹词",
            cls.PHRASE.value: "短语",
            cls.OTHER.value: "其他",
        }
        return names.get(category.lower(), category)


@dataclass
class Vocabulary:
    """
    Vocabulary entity representing a word.

    Attributes:
        id: Vocabulary's unique identifier (None for new words)
        word: The English word
        phonetic: Phonetic transcription (IPA)
        definition: Chinese definition
        example: Example sentence showing usage
        difficulty: Difficulty level (1-10)
        frequency: Frequency ranking (higher = more common)
        category: Part of speech category
    """
    id: Optional[int]
    word: str
    definition: str
    phonetic: Optional[str] = None
    example: Optional[str] = None
    difficulty: int = 1
    frequency: int = 1
    category: Optional[str] = None

    def __post_init__(self):
        """Validate fields after initialization"""
        # Clamp difficulty to 1-10
        self.difficulty = max(1, min(10, self.difficulty))
        # Ensure frequency is at least 1
        self.frequency = max(1, self.frequency)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "word": self.word,
            "phonetic": self.phonetic,
            "definition": self.definition,
            "example": self.example,
            "difficulty": self.difficulty,
            "frequency": self.frequency,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Vocabulary":
        """Create Vocabulary from dictionary"""
        return cls(
            id=data.get("id"),
            word=data["word"],
            phonetic=data.get("phonetic"),
            definition=data.get("definition", ""),
            example=data.get("example"),
            difficulty=data.get("difficulty", 1),
            frequency=data.get("frequency", 1),
            category=data.get("category"),
        )

    @property
    def category_display(self) -> str:
        """Get display name for the word's category"""
        if not self.category:
            return ""
        return WordCategory.display_name(self.category)

    def matches_difficulty(self, min_diff: int, max_diff: int) -> bool:
        """
        Check if word difficulty falls within range.

        Args:
            min_diff: Minimum difficulty level
            max_diff: Maximum difficulty level

        Returns:
            True if difficulty is within range
        """
        return min_diff <= self.difficulty <= max_diff


@dataclass
class VocabularySet:
    """
    A collection of vocabulary words (a vocabulary book).

    Attributes:
        name: Name of the vocabulary set
        description: Description of the vocabulary set
        level: Target user level
        words: List of vocabulary words
    """
    name: str
    words: list[Vocabulary] = field(default_factory=list)
    description: str = ""
    level: str = ""
    version: str = "1.0"

    def __len__(self) -> int:
        """Get total number of words"""
        return len(self.words)

    def __iter__(self):
        """Allow iteration over words"""
        return iter(self.words)

    def filter_by_difficulty(self, min_diff: int, max_diff: int) -> list[Vocabulary]:
        """Filter words by difficulty range"""
        return [
            w for w in self.words
            if w.matches_difficulty(min_diff, max_diff)
        ]

    def get_word_by_text(self, word: str) -> Optional[Vocabulary]:
        """Find a word by its text (case-insensitive)"""
        word_lower = word.lower()
        for vocab in self.words:
            if vocab.word.lower() == word_lower:
                return vocab
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for JSON export)"""
        return {
            "meta": {
                "name": self.name,
                "description": self.description,
                "level": self.level,
                "version": self.version,
                "total_words": len(self.words),
            },
            "words": [w.to_dict() for w in self.words],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VocabularySet":
        """Create VocabularySet from dictionary (from JSON import)"""
        meta = data.get("meta", {})
        words_data = data.get("words", [])

        return cls(
            name=meta.get("name", "Imported Vocabulary"),
            description=meta.get("description", ""),
            level=meta.get("level", ""),
            version=meta.get("version", "1.0"),
            words=[Vocabulary.from_dict(w) for w in words_data],
        )
