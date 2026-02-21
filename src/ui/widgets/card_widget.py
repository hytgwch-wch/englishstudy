"""
Word Card Widget

Displays a vocabulary word with user interaction for learning.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from config import config
from src.models.word_record import MemoryStatus
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)


class WordCardWidget(QWidget):
    """
    Widget displaying a vocabulary word for study.

    Features:
    - Word display with phonetic
    - Definition and example
    - Three-button memory status feedback
    - Progress tracking
    - Session statistics
    """

    # Signals
    answer_submitted = pyqtSignal(int, str)  # vocabulary_id, status
    next_requested = pyqtSignal()
    previous_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize word card widget"""
        super().__init__(parent)

        self.current_word: Optional[Dict[str, Any]] = None
        self.session_stats = {
            "total": 0,
            "correct": 0,
            "remaining": 0
        }

        self._setup_ui()
        self._update_buttons_state(False)

    def _setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Session info bar
        self._create_session_info_bar(layout)

        # Container widget for content (no scroll area - let parent handle scrolling)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        # Word card frame
        card_frame = self._create_card_frame()
        content_layout.addWidget(card_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add spacing to ensure buttons don't overlap with card
        content_layout.addSpacing(20)

        # Status buttons
        self._create_status_buttons(content_layout)

        # Navigation buttons
        self._create_navigation_buttons(content_layout)

        layout.addWidget(content_widget)
        layout.addStretch()

    def _create_session_info_bar(self, layout: QVBoxLayout):
        """Create session information bar"""
        info_layout = QHBoxLayout()

        self.session_label = QLabel("本次学习: 0/0")
        self.session_label.setStyleSheet("font-size: 12pt; color: #a6adc8;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setTextVisible(False)

        self.correct_label = QLabel("正确率: 0%")
        self.correct_label.setStyleSheet("font-size: 12pt; color: #a6adc8;")

        info_layout.addWidget(self.session_label)
        info_layout.addStretch()
        info_layout.addWidget(self.progress_bar)
        info_layout.addWidget(self.correct_label)

        layout.addLayout(info_layout)

    def _create_card_frame(self) -> QFrame:
        """Create the main word display card"""
        frame = QFrame()
        frame.setObjectName("cardFrame")
        frame.setMinimumWidth(700)
        frame.setMinimumHeight(350)
        # Prevent clipping of children
        from PyQt6.QtWidgets import QSizePolicy
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Disable auto-clip of children to rounded corners
        frame.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(40, 40, 40, 40)
        frame_layout.setSpacing(20)

        # Word label
        self.word_label = QLabel("准备学习")
        self.word_label.setObjectName("wordLabel")
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        frame_layout.addWidget(self.word_label)

        # Phonetic label - add more spacing
        self.phonetic_label = QLabel("")
        self.phonetic_label.setObjectName("phoneticLabel")
        self.phonetic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phonetic_label.setStyleSheet("font-size: 14pt; color: #a6adc8;")
        frame_layout.addWidget(self.phonetic_label)

        # Separator
        separator = QLabel("─" * 25)
        separator.setStyleSheet("color: #45475a; letter-spacing: 1px;")
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_layout.addWidget(separator)

        # Definition label
        self.definition_label = QLabel("")
        self.definition_label.setObjectName("definitionLabel")
        self.definition_label.setWordWrap(True)
        self.definition_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.definition_label.setStyleSheet("font-size: 16pt; color: #cdd6f4;")
        frame_layout.addWidget(self.definition_label)

        # Example label
        self.example_label = QLabel("")
        self.example_label.setObjectName("exampleLabel")
        self.example_label.setWordWrap(True)
        self.example_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.example_label.setStyleSheet("font-size: 12pt; color: #a6adc8;")
        frame_layout.addWidget(self.example_label)

        frame_layout.addStretch()

        # Difficulty indicator
        self.difficulty_label = QLabel("")
        self.difficulty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.difficulty_label.setStyleSheet("font-size: 10pt; color: #6c7086;")
        frame_layout.addWidget(self.difficulty_label)

        return frame

    def _create_status_buttons(self, layout: QVBoxLayout):
        """Create the three status feedback buttons"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        # Hard button (不认识)
        self.hard_button = QPushButton("不认识")
        self.hard_button.setObjectName("hardButton")
        self.hard_button.setProperty("class", "statusButton")
        self.hard_button.setMinimumHeight(70)
        self.hard_button.clicked.connect(lambda: self._submit_answer(MemoryStatus.HARD))

        # Medium button (模糊)
        self.medium_button = QPushButton("模  糊")
        self.medium_button.setObjectName("mediumButton")
        self.medium_button.setProperty("class", "statusButton")
        self.medium_button.setMinimumHeight(70)
        self.medium_button.clicked.connect(lambda: self._submit_answer(MemoryStatus.MEDIUM))

        # Easy button (认识)
        self.easy_button = QPushButton("认  识")
        self.easy_button.setObjectName("easyButton")
        self.easy_button.setProperty("class", "statusButton")
        self.easy_button.setMinimumHeight(70)
        self.easy_button.clicked.connect(lambda: self._submit_answer(MemoryStatus.EASY))

        button_layout.addWidget(self.hard_button)
        button_layout.addWidget(self.medium_button)
        button_layout.addWidget(self.easy_button)

        layout.addLayout(button_layout)

        # Keyboard shortcuts hint
        hint = QLabel("快捷键: 1=不认识, 2=模糊, 3=认识 | Space=下一题")
        hint.setStyleSheet("font-size: 10pt; color: #6c7086;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def _create_navigation_buttons(self, layout: QVBoxLayout):
        """Create navigation buttons"""
        nav_layout = QHBoxLayout()

        self.previous_button = QPushButton("← 上一题")
        self.previous_button.setEnabled(False)
        self.previous_button.clicked.connect(self.previous_requested.emit)

        self.next_button = QPushButton("下一题 →")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.next_requested.emit)

        nav_layout.addWidget(self.previous_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_button)

        layout.addLayout(nav_layout)

    def _submit_answer(self, status: MemoryStatus):
        """Handle answer submission"""
        if self.current_word is None:
            return

        vocab_id = self.current_word.get("id")
        if vocab_id is None:
            return

        logger.debug(f"Answer submitted: vocab_id={vocab_id}, status={status.value}")
        self.answer_submitted.emit(vocab_id, status.value)

    def _update_session_display(self):
        """Update session statistics display"""
        total = self.session_stats["total"]
        remaining = self.session_stats["remaining"]
        correct = self.session_stats["correct"]
        total_studied = total + remaining

        self.session_label.setText(f"本次学习: {total}/{total_studied}")

        if total_studied > 0:
            progress = int((total / total_studied) * 100)
            self.progress_bar.setValue(progress)
        else:
            self.progress_bar.setValue(0)

        if total > 0:
            correct_rate = int((correct / total) * 100)
            self.correct_label.setText(f"正确率: {correct_rate}%")
        else:
            self.correct_label.setText("正确率: 0%")

    def _update_buttons_state(self, enabled: bool):
        """Enable or disable answer buttons"""
        self.hard_button.setEnabled(enabled)
        self.medium_button.setEnabled(enabled)
        self.easy_button.setEnabled(enabled)

    def display_word(self, word_data: Dict[str, Any], remaining: int = 0):
        """
        Display a vocabulary word.

        Args:
            word_data: Dictionary with word information
            remaining: Number of words remaining
        """
        self.current_word = word_data

        # Update labels
        self.word_label.setText(word_data.get("word", ""))

        phonetic = word_data.get("phonetic", "")
        self.phonetic_label.setText(phonetic if phonetic else "")
        self.phonetic_label.setVisible(bool(phonetic))

        self.definition_label.setText(word_data.get("definition", ""))

        example = word_data.get("example", "")
        self.example_label.setText(f"例句: {example}" if example else "")
        self.example_label.setVisible(bool(example))

        # Difficulty indicator
        difficulty = word_data.get("difficulty", 1)
        difficulty_stars = "★" * difficulty
        self.difficulty_label.setText(f"难度: {difficulty_stars} ({difficulty}/10)")

        # Color code difficulty
        difficulty_colors = {
            1: "#a6e3a1", 2: "#94e2d5", 3: "#89dceb", 4: "#89b4fa",
            5: "#b4befe", 6: "#cba6f7", 7: "#f5c2e7", 8: "#eba0ac",
            9: "#f38ba8", 10: "#f38ba8"
        }
        color = difficulty_colors.get(difficulty, "#cba6f7")
        self.difficulty_label.setStyleSheet(
            f"font-size: 10pt; color: {color};"
        )

        # Update session stats
        self.session_stats["remaining"] = remaining
        self._update_session_display()

        # Enable buttons
        self._update_buttons_state(True)

        # Reset navigation
        self.next_button.setEnabled(False)

        logger.debug(f"Displayed word: {word_data.get('word')}")

    def clear_card(self):
        """Clear the card display"""
        self.current_word = None
        self.word_label.setText("准备学习")
        self.phonetic_label.setText("")
        self.phonetic_label.setVisible(False)
        self.definition_label.setText("")
        self.example_label.setText("")
        self.example_label.setVisible(False)
        self.difficulty_label.setText("")
        self._update_buttons_state(False)
        self.next_button.setEnabled(False)
        self.previous_button.setEnabled(False)

    def set_session_stats(self, total: int, correct: int, remaining: int):
        """
        Set session statistics.

        Args:
            total: Total words studied
            correct: Correct answers
            remaining: Words remaining
        """
        self.session_stats = {
            "total": total,
            "correct": correct,
            "remaining": remaining
        }
        self._update_session_display()

    def enable_navigation(self, can_go_back: bool, can_go_forward: bool):
        """
        Enable/disable navigation buttons.

        Args:
            can_go_back: Whether previous button should be enabled
            can_go_forward: Whether next button should be enabled
        """
        self.previous_button.setEnabled(can_go_back)
        self.next_button.setEnabled(can_go_forward)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if not self.hard_button.isEnabled():
            return

        key_map = {
            Qt.Key.Key_1: MemoryStatus.HARD,
            Qt.Key.Key_2: MemoryStatus.MEDIUM,
            Qt.Key.Key_3: MemoryStatus.EASY,
        }

        if event.key() in key_map:
            self._submit_answer(key_map[event.key()])
        elif event.key() == Qt.Key.Key_Space:
            if self.next_button.isEnabled():
                self.next_requested.emit()
        else:
            super().keyPressEvent(event)
