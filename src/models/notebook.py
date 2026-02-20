"""
Notebook models for EnglishStudy application

MistakeBook and NewWordBook for tracking important words.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class NotebookType(Enum):
    """Type of notebook"""
    MISTAKE = "mistake"      # 错题本
    NEW_WORD = "new_word"    # 生词本

    @classmethod
    def from_string(cls, value: str) -> "NotebookType":
        """Create NotebookType from string value"""
        for nb_type in cls:
            if nb_type.value == value.lower():
                return nb_type
        return cls.MISTAKE

    @classmethod
    def display_name(cls, notebook_type: str) -> str:
        """Get display name for a notebook type"""
        names = {
            cls.MISTAKE.value: "错题本",
            cls.NEW_WORD.value: "生词本",
        }
        return names.get(notebook_type, notebook_type)


@dataclass
class NotebookEntry:
    """
    Base class for notebook entries.

    Attributes:
        id: Entry's unique identifier
        user_id: User ID who owns this entry
        word_record_id: Associated word record ID
        note: User's personal note
        created_at: Entry creation timestamp
        notebook_type: Type of notebook
    """
    id: Optional[int]
    user_id: int
    word_record_id: int
    note: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    notebook_type: NotebookType = NotebookType.MISTAKE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "word_record_id": self.word_record_id,
            "note": self.note,
            "created_at": self.created_at.isoformat(),
            "notebook_type": self.notebook_type.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotebookEntry":
        """Create NotebookEntry from dictionary"""
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            word_record_id=data["word_record_id"],
            note=data.get("note", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            notebook_type=NotebookType.from_string(data.get("notebook_type", "mistake")),
        )


@dataclass
class MistakeEntry(NotebookEntry):
    """
    Entry in the mistake book (错题本).

    Tracks words that the user answered incorrectly or found difficult.
    """
    notebook_type: NotebookType = NotebookType.MISTAKE

    def __post_init__(self):
        """Ensure notebook type is MISTAKE"""
        self.notebook_type = NotebookType.MISTAKE


@dataclass
class NewWordEntry(NotebookEntry):
    """
    Entry in the new word book (生词本).

    Tracks words that the user wants to remember or study more.
    """
    notebook_type: NotebookType = NotebookType.NEW_WORD

    def __post_init__(self):
        """Ensure notebook type is NEW_WORD"""
        self.notebook_type = NotebookType.NEW_WORD


@dataclass
class NotebookEntryDetail:
    """
    Detailed view of a notebook entry with word information.

    Attributes:
        entry: The notebook entry
        word: The vocabulary word
        definition: Word definition
        phonetic: Word phonetic (optional)
        example: Example sentence (optional)
    """
    entry: NotebookEntry
    word: str
    definition: str
    phonetic: Optional[str] = None
    example: Optional[str] = None
    difficulty: Optional[int] = None

    @property
    def notebook_type_display(self) -> str:
        """Get display name for notebook type"""
        return NotebookType.display_name(self.entry.notebook_type.value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "entry": self.entry.to_dict(),
            "word": self.word,
            "definition": self.definition,
            "phonetic": self.phonetic,
            "example": self.example,
            "difficulty": self.difficulty,
        }


@dataclass
class Notebook:
    """
    A collection of notebook entries for a user.

    Attributes:
        user_id: User ID
        entries: List of notebook entries
        notebook_type: Type of notebook
    """
    user_id: int
    entries: List[NotebookEntry] = field(default_factory=list)
    notebook_type: NotebookType = NotebookType.MISTAKE

    def __len__(self) -> int:
        """Get total number of entries"""
        return len(self.entries)

    def __iter__(self):
        """Allow iteration over entries"""
        return iter(self.entries)

    def add_entry(self, entry: NotebookEntry) -> bool:
        """
        Add an entry to the notebook.

        Args:
            entry: Entry to add

        Returns:
            True if added, False if already exists
        """
        # Check if entry already exists
        for existing in self.entries:
            if existing.word_record_id == entry.word_record_id:
                return False

        self.entries.append(entry)
        return True

    def remove_entry(self, word_record_id: int) -> bool:
        """
        Remove an entry from the notebook.

        Args:
            word_record_id: Word record ID to remove

        Returns:
            True if removed, False if not found
        """
        for i, entry in enumerate(self.entries):
            if entry.word_record_id == word_record_id:
                self.entries.pop(i)
                return True
        return False

    def get_entry_by_word_record(self, word_record_id: int) -> Optional[NotebookEntry]:
        """Get an entry by word record ID"""
        for entry in self.entries:
            if entry.word_record_id == word_record_id:
                return entry
        return None

    def sort_by_date(self, descending: bool = True) -> None:
        """Sort entries by creation date"""
        self.entries.sort(
            key=lambda e: e.created_at,
            reverse=descending
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "notebook_type": self.notebook_type.value,
            "total_entries": len(self.entries),
            "entries": [e.to_dict() for e in self.entries],
        }


class MistakeBook(Notebook):
    """Specialized notebook for mistakes"""

    def __init__(self, user_id: int):
        super().__init__(user_id, notebook_type=NotebookType.MISTAKE)


class NewWordBook(Notebook):
    """Specialized notebook for new words"""

    def __init__(self, user_id: int):
        super().__init__(user_id, notebook_type=NotebookType.NEW_WORD)
