"""
Test Widget

Administers vocabulary tests with various question types.
"""

import logging
from typing import List, Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QButtonGroup,
    QRadioButton, QFrame, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIntValidator

from config import config
from src.models.session import TestQuestion, TestResult
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)


class TestConfigWidget(QWidget):
    """
    Test configuration widget.

    Allows users to configure test parameters before starting.
    """

    # Signal: (word_count, test_type, difficulty_range)
    test_configured = pyqtSignal(int, str, tuple)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize test configuration widget"""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("📝 测试配置")
        title.setStyleSheet("font-size: 24pt; font-weight: bold; color: #cba6f7;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(20)

        # Test type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("题型:"))

        self.type_buttons = QButtonGroup(self)
        test_types = [
            ("单选题", "multiple_choice"),
            ("拼写题", "spelling"),
            ("混合", "mixed")
        ]

        for i, (label, value) in enumerate(test_types):
            radio = QRadioButton(label)
            self.type_buttons.addButton(radio, i)
            type_layout.addWidget(radio)
            if i == 0:  # Default to first option
                radio.setChecked(True)

        type_layout.addStretch()
        layout.addLayout(type_layout)

        # Word count
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("题目数量:"))

        self.count_input = QLineEdit(str(config.DEFAULT_TEST_QUESTIONS))
        self.count_input.setValidator(QIntValidator(1, 100))
        self.count_input.setMaximumWidth(100)
        count_layout.addWidget(self.count_input)
        count_layout.addStretch()
        layout.addLayout(count_layout)

        # Difficulty range
        diff_layout = QHBoxLayout()
        diff_layout.addWidget(QLabel("难度范围:"))

        from PyQt6.QtWidgets import QSpinBox
        self.min_diff_spin = QSpinBox()
        self.min_diff_spin.setRange(1, 10)
        self.min_diff_spin.setValue(1)

        diff_layout.addWidget(QLabel("从"))
        diff_layout.addWidget(self.min_diff_spin)

        self.max_diff_spin = QSpinBox()
        self.max_diff_spin.setRange(1, 10)
        self.max_diff_spin.setValue(10)

        diff_layout.addWidget(QLabel("到"))
        diff_layout.addWidget(self.max_diff_spin)
        diff_layout.addStretch()
        layout.addLayout(diff_layout)

        layout.addSpacing(30)

        # Start button
        start_button = QPushButton("开始测试")
        start_button.setProperty("class", "primary")
        start_button.setMinimumHeight(50)
        start_button.clicked.connect(self._on_start_clicked)
        layout.addWidget(start_button)

        layout.addStretch()

    def _on_start_clicked(self):
        """Handle start button click"""
        count = int(self.count_input.text() or 10)
        min_diff = self.min_diff_spin.value()
        max_diff = self.max_diff_spin.value()

        if min_diff > max_diff:
            QMessageBox.warning(self, "配置错误", "最小难度不能大于最大难度")
            return

        # Get test type
        checked = self.type_buttons.checkedButton()
        type_map = {
            0: "multiple_choice",
            1: "spelling",
            2: "mixed"
        }
        test_type = type_map[self.type_buttons.id(checked)]

        self.test_configured.emit(count, test_type, (min_diff, max_diff))


class TestQuestionWidget(QWidget):
    """
    Widget displaying a single test question.
    """

    # Signal: (question_index, answer)
    answer_submitted = pyqtSignal(int, str)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize test question widget"""
        super().__init__(parent)

        self.current_question: Optional[TestQuestion] = None
        self.current_index = 0
        self.total_questions = 0
        self.start_time: Optional[float] = None
        self.elapsed_seconds = 0  # Track elapsed time

        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header with progress
        header_layout = QHBoxLayout()

        self.progress_label = QLabel("题目 1/10")
        self.progress_label.setStyleSheet("font-size: 14pt; color: #a6adc8;")
        header_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(300)
        header_layout.addWidget(self.progress_bar)

        header_layout.addStretch()

        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet("font-size: 14pt; color: #89b4fa;")
        header_layout.addWidget(self.timer_label)

        layout.addLayout(header_layout)
        layout.addSpacing(20)

        # Question frame
        self.question_frame = self._create_question_frame()
        layout.addWidget(self.question_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        # Answer area
        self.answer_area = self._create_answer_area()
        layout.addWidget(self.answer_area)

        # Submit button
        self.submit_button = QPushButton("提交答案")
        self.submit_button.setProperty("class", "primary")
        self.submit_button.setMinimumHeight(50)
        self.submit_button.clicked.connect(self._on_submit_clicked)
        layout.addWidget(self.submit_button)

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_timer)

    def _create_question_frame(self) -> QFrame:
        """Create the question display frame"""
        frame = QFrame()
        frame.setObjectName("cardFrame")
        frame.setMinimumWidth(500)
        frame.setMaximumWidth(700)
        frame.setMinimumHeight(200)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 24, 24, 24)

        self.question_label = QLabel("准备开始测试...")
        self.question_label.setObjectName("definitionLabel")
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.question_label)

        return frame

    def _create_answer_area(self) -> QWidget:
        """Create the answer input area"""
        widget = QWidget()

        layout = QVBoxLayout(widget)

        # For multiple choice - will be populated dynamically
        self.choice_layout = QHBoxLayout()
        self.choice_buttons: List[QRadioButton] = []
        layout.addLayout(self.choice_layout)

        # For text input
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("请输入答案...")
        self.text_input.setMinimumHeight(50)
        self.text_input.setStyleSheet("font-size: 14pt;")
        layout.addWidget(self.text_input)

        # Initially hide text input
        self.text_input.setVisible(False)

        return widget

    def display_question(
        self,
        question: TestQuestion,
        index: int,
        total: int
    ):
        """
        Display a test question.

        Args:
            question: TestQuestion to display
            index: Question index (0-based)
            total: Total number of questions
        """
        self.current_question = question
        self.current_index = index
        self.total_questions = total

        # Update progress
        self.progress_label.setText(f"题目 {index + 1}/{total}")
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(index + 1)

        # Display question text
        self.question_label.setText(question.question)

        # Setup answer area based on question type
        if question.question_type == "multiple_choice":
            self._setup_multiple_choice(question)
        else:
            self._setup_text_input(question)

        # Start or reset timer
        if index == 0:
            # First question - reset elapsed time
            self.elapsed_seconds = 0

        # Start the timer
        self.timer.start(1000)  # Update every second
        self._update_timer()

        # Clear previous answer
        self.text_input.clear()
        self.text_input.setFocus()

        logger.debug(f"Displayed question {index + 1}/{total}: type={question.question_type}")

    def _setup_multiple_choice(self, question: TestQuestion):
        """Setup multiple choice buttons"""
        # Hide text input
        self.text_input.setVisible(False)

        # Clear previous buttons
        for btn in self.choice_buttons:
            btn.deleteLater()
        self.choice_buttons.clear()

        # Parse options from question text (format: "A. option1\nB. option2\n...")
        lines = question.question.split('\n')
        options = []
        for line in lines[1:]:  # Skip first line (question)
            line = line.strip()
            if line and len(line) > 2 and line[1] == '.':
                option_text = line[3:].strip()  # Remove "A. " prefix
                options.append(option_text)

        # Create radio buttons
        for i, option in enumerate(options):
            radio = QRadioButton(option)
            radio.setStyleSheet("font-size: 12pt; padding: 8px;")
            self.choice_layout.addWidget(radio)
            self.choice_buttons.append(radio)

        self.choice_layout.addStretch()

    def _setup_text_input(self, question: TestQuestion):
        """Setup text input for spelling/definition questions"""
        # Hide choice buttons
        for btn in self.choice_buttons:
            btn.setVisible(False)

        # Show text input
        self.text_input.setVisible(True)

        if question.question_type == "spelling":
            self.text_input.setPlaceholderText("请拼写单词...")
        else:
            self.text_input.setPlaceholderText("请输入答案...")

    def _on_submit_clicked(self):
        """Handle submit button click"""
        if self.current_question is None:
            return

        # Get answer
        if self.current_question.question_type == "multiple_choice":
            # Find checked radio button
            answer = ""
            for i, btn in enumerate(self.choice_buttons):
                if btn.isChecked():
                    # Map back to option letter (A, B, C, D)
                    answer_letter = chr(65 + i)
                    # Get the option text
                    lines = self.current_question.question.split('\n')
                    for line in lines[1:]:
                        if line.startswith(f"{answer_letter}."):
                            answer = line[3:].strip()
                            break
                    break
        else:
            answer = self.text_input.text().strip()

        if not answer:
            QMessageBox.warning(self, "请输入答案", "请先输入答案再提交")
            return

        # Calculate time taken
        time_taken = None
        if self.start_time is not None:
            elapsed = QTimer.remainingTime(self.timer) if self.timer.isActive() else 0
            # time_taken would be calculated properly with elapsed time tracking

        logger.debug(f"Answer submitted for question {self.current_index}: {answer}")
        self.answer_submitted.emit(self.current_index, answer)

    def _update_timer(self):
        """Update the timer display"""
        # Increment elapsed time
        self.elapsed_seconds += 1

        # Format as MM:SS
        minutes = self.elapsed_seconds // 60
        seconds = self.elapsed_seconds % 60
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

    def clear_display(self):
        """Clear the question display"""
        self.question_label.setText("测试完成")
        self.text_input.setVisible(False)
        for btn in self.choice_buttons:
            btn.setVisible(False)
        self.submit_button.setEnabled(False)
        self.timer.stop()  # Stop the timer
        self.timer_label.setText("00:00")  # Reset display


class TestResultWidget(QWidget):
    """
    Widget displaying test results.
    """

    # Signal: back_to_config, retry
    back_requested = pyqtSignal()
    retry_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize test result widget"""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.result_frame = self._create_result_frame()
        layout.addWidget(self.result_frame)

        layout.addSpacing(30)

        # Buttons
        button_layout = QHBoxLayout()

        self.back_button = QPushButton("返回配置")
        self.back_button.clicked.connect(self.back_requested.emit)
        button_layout.addWidget(self.back_button)

        self.retry_button = QPushButton("再测一次")
        self.retry_button.setProperty("class", "primary")
        self.retry_button.clicked.connect(self.retry_requested.emit)
        button_layout.addWidget(self.retry_button)

        layout.addLayout(button_layout)

    def _create_result_frame(self) -> QFrame:
        """Create the result display frame"""
        frame = QFrame()
        frame.setObjectName("cardFrame")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        self.title_label = QLabel("测试完成！")
        self.title_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: #cba6f7;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Score
        self.score_label = QLabel("得分: 0%")
        self.score_label.setStyleSheet("font-size: 36pt; font-weight: bold;")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.score_label)

        # Pass/Fail
        self.pass_label = QLabel("")
        self.pass_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        self.pass_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.pass_label)

        layout.addSpacing(20)

        # Details
        self.details_label = QLabel("")
        self.details_label.setStyleSheet("font-size: 14pt; color: #a6adc8;")
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.details_label)

        return frame

    def display_results(self, result: TestResult):
        """
        Display test results.

        Args:
            result: TestResult object
        """
        score = result.score
        passed = result.passed

        self.score_label.setText(f"得分: {score:.0f}%")

        # Color code based on score
        if score >= 90:
            color = "#a6e3a1"  # Green
        elif score >= 60:
            color = "#f9e2af"  # Yellow
        else:
            color = "#f38ba8"  # Red
        self.score_label.setStyleSheet(
            f"font-size: 36pt; font-weight: bold; color: {color};"
        )

        # Pass/Fail
        if passed:
            self.pass_label.setText("✓ 通过")
            self.pass_label.setStyleSheet("font-size: 18pt; font-weight: bold; color: #a6e3a1;")
        else:
            self.pass_label.setText("✗ 未通过")
            self.pass_label.setStyleSheet("font-size: 18pt; font-weight: bold; color: #f38ba8;")

        # Details
        details = (
            f"答对: {result.correct_answers} / {result.total_questions}\n"
            f"平均用时: {result.average_time_per_question:.1f} 秒/题"
        )
        self.details_label.setText(details)

        logger.info(f"Displayed test results: score={score:.0f}%, passed={passed}")


class TestWidget(QWidget):
    """
    Main test widget combining config, questions, and results.
    """

    # Signals
    test_completed = pyqtSignal(object)  # TestResult

    def __init__(self, test_manager=None, parent: Optional[QWidget] = None):
        """Initialize test widget"""
        super().__init__(parent)

        self.test_manager = test_manager
        self.current_result: Optional[TestResult] = None
        self.current_questions: List[TestQuestion] = []
        self.current_answers: Dict[int, str] = {}  # question_index -> answer
        self.current_question_index: int = 0

        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for different states
        from PyQt6.QtWidgets import QStackedWidget
        self.stacked_widget = QStackedWidget()

        # Config page
        self.config_widget = TestConfigWidget()
        self.config_widget.test_configured.connect(self._on_test_configured)
        self.stacked_widget.addWidget(self.config_widget)

        # Question page
        self.question_widget = TestQuestionWidget()
        self.question_widget.answer_submitted.connect(self._on_answer_submitted)
        self.stacked_widget.addWidget(self.question_widget)

        # Result page
        self.result_widget = TestResultWidget()
        self.result_widget.back_requested.connect(self._back_to_config)
        self.result_widget.retry_requested.connect(self._retry_test)
        self.stacked_widget.addWidget(self.result_widget)

        layout.addWidget(self.stacked_widget)

        # Start at config
        self.stacked_widget.setCurrentWidget(self.config_widget)

    def _on_test_configured(self, count: int, test_type: str, difficulty_range: tuple):
        """Handle test configuration"""
        logger.info(f"Test configured: count={count}, type={test_type}, range={difficulty_range}")

        # Check if test_manager is available
        if self.test_manager is None:
            logger.error("Test manager not set!")
            QMessageBox.warning(self, "错误", "测试管理器未初始化")
            return

        # Generate questions
        try:
            # Get vocabulary words for the test
            from src.infrastructure.database import get_db
            db = get_db()

            # Get words within difficulty range
            min_diff, max_diff = difficulty_range
            with db.get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM vocabularies
                       WHERE difficulty BETWEEN ? AND ?
                       ORDER BY RANDOM()
                       LIMIT ?""",
                    (min_diff, max_diff, count)
                )
                words = [dict(row) for row in cursor.fetchall()]

            if not words:
                QMessageBox.warning(self, "没有可用单词", "指定难度范围内没有找到单词")
                return

            # Generate questions
            self.current_questions = []
            for word in words:
                question = self._generate_question(word, test_type)
                if question:
                    self.current_questions.append(question)

            if not self.current_questions:
                QMessageBox.warning(self, "生成失败", "无法生成测试题目")
                return

            # Reset state
            self.current_answers = {}
            self.current_question_index = 0
            # Reset timer in question widget
            self.question_widget.elapsed_seconds = 0

            # Display first question
            self._display_current_question()

            # Switch to question page
            self.stacked_widget.setCurrentWidget(self.question_widget)

            logger.info(f"Generated {len(self.current_questions)} test questions")

        except Exception as e:
            logger.error(f"Failed to generate test questions: {e}")
            QMessageBox.critical(self, "错误", f"生成测试题目失败: {e}")

    def _generate_question(self, word: Dict[str, Any], test_type: str) -> Optional[TestQuestion]:
        """Generate a test question from a vocabulary word"""
        word_text = word.get("word", "")
        definition = word.get("definition", "")
        difficulty = word.get("difficulty", 1)
        vocab_id = word.get("id")

        if test_type == "multiple_choice":
            # Generate multiple choice question
            question_text = f"单词 \"{word_text}\" 的意思是？"

            # Get distractors
            from src.infrastructure.database import get_db
            db = get_db()
            with db.get_connection() as conn:
                cursor = conn.execute(
                    """SELECT word, definition FROM vocabularies
                       WHERE word != ? AND difficulty BETWEEN ? AND ?
                       ORDER BY RANDOM()
                       LIMIT 3""",
                    (word_text, max(1, difficulty - 2), min(10, difficulty + 2))
                )
                distractors = [dict(row) for row in cursor.fetchall()]

            if len(distractors) < 3:
                # Not enough distractors, skip this question
                return None

            import random
            options = [definition] + [d["definition"] for d in distractors[:3]]
            random.shuffle(options)

            # Format question with options
            letters = ["A", "B", "C", "D"]
            formatted_options = "\n".join([f"{letters[i]}. {opt}" for i, opt in enumerate(options)])
            full_question = f"{question_text}\n{formatted_options}"

            # Find correct answer
            correct_letter = letters[options.index(definition)]
            correct_answer = f"{correct_letter}. {definition}"

            return TestQuestion(
                vocabulary_id=vocab_id,
                question_type="multiple_choice",
                question=full_question,
                correct_answer=correct_answer
            )

        elif test_type == "spelling":
            # Spelling question
            question_text = f"请拼写以下中文含义的英文单词：{definition}"

            return TestQuestion(
                vocabulary_id=vocab_id,
                question_type="spelling",
                question=question_text,
                correct_answer=word_text
            )

        else:  # mixed - randomly choose
            import random
            actual_type = random.choice(["multiple_choice", "spelling"])
            return self._generate_question(word, actual_type)

    def _display_current_question(self):
        """Display the current question"""
        if 0 <= self.current_question_index < len(self.current_questions):
            question = self.current_questions[self.current_question_index]
            self.question_widget.display_question(
                question,
                self.current_question_index,
                len(self.current_questions)
            )
        else:
            # All questions answered
            self._finish_test()

    def _on_answer_submitted(self, index: int, answer: str):
        """Handle answer submission"""
        logger.debug(f"Answer submitted for question {index}: {answer}")

        # Store answer
        self.current_answers[index] = answer

        # Move to next question
        self.current_question_index += 1
        self._display_current_question()

    def _finish_test(self):
        """Finish the test and show results"""
        if not self.current_questions:
            return

        # Calculate score and collect wrong answers
        correct = 0
        wrong_questions = []
        for i, question in enumerate(self.current_questions):
            user_answer = self.current_answers.get(i, "")

            # Normalize answers for comparison
            # For multiple choice, correct_answer might be "A. definition" while user_answer is "definition"
            normalized_correct = question.correct_answer.lower()
            if len(normalized_correct) > 2 and normalized_correct[1] == '.':
                # Remove "A. " prefix if present
                normalized_correct = normalized_correct[3:].strip()

            normalized_user = user_answer.lower().strip()

            if normalized_user == normalized_correct:
                correct += 1
                logger.debug(f"Question {i}: CORRECT - '{normalized_user}' == '{normalized_correct}'")
            else:
                logger.debug(f"Question {i}: WRONG - '{normalized_user}' != '{normalized_correct}'")
                # Collect wrong question for mistake book
                wrong_questions.append(question)

        total = len(self.current_questions)
        score = (correct / total * 100) if total > 0 else 0
        passed = score >= 60

        # Add wrong answers to mistake book
        self._add_wrong_answers_to_mistake_book(wrong_questions)

        # Get total elapsed time from question widget
        total_time_seconds = self.question_widget.elapsed_seconds

        # Create result - TestResult requires session_id as first parameter
        # Use 0 for session_id since we're not creating a database record
        result = TestResult(
            session_id=0,
            total_questions=total,
            correct_answers=correct,
            total_time=int(total_time_seconds),
            questions=[]
        )

        self.current_result = result

        # Display results
        self.result_widget.display_results(result)
        self.stacked_widget.setCurrentWidget(self.result_widget)

        # Emit completion signal
        self.test_completed.emit(result)

        logger.info(f"Test completed: score={score:.0f}%, passed={passed}")

    def _back_to_config(self):
        """Return to configuration page"""
        self.stacked_widget.setCurrentWidget(self.config_widget)

    def _retry_test(self):
        """Retry the test with same configuration"""
        self.stacked_widget.setCurrentWidget(self.question_widget)

    def _add_wrong_answers_to_mistake_book(self, wrong_questions: List[TestQuestion]):
        """Add wrong answers to mistake book"""
        logger.info(f"_add_wrong_answers_to_mistake_book called with {len(wrong_questions)} wrong questions")

        if not wrong_questions:
            logger.info("No wrong questions to add to mistake book")
            return

        try:
            from src.infrastructure.database import get_db
            db = get_db()

            # Get current user ID (default to 1 for now)
            user_id = 1

            for i, question in enumerate(wrong_questions):
                try:
                    logger.info(f"Processing wrong question {i}: vocab_id={question.vocabulary_id}, type={question.question_type}")

                    # Get or create word record
                    word_record = db.get_or_create_word_record(
                        user_id,
                        question.vocabulary_id
                    )

                    if word_record:
                        logger.info(f"Got word_record: id={word_record.get('id')}")
                        db.add_to_mistake_book(
                            user_id,
                            word_record["id"],
                            note=f"Test error: {question.question_type}"
                        )
                        logger.info(f"Added vocab_id {question.vocabulary_id} to mistake book")
                    else:
                        logger.warning(f"Failed to get word_record for vocab_id {question.vocabulary_id}")

                except Exception as e:
                    logger.error(f"Failed to add word {question.vocabulary_id} to mistake book: {e}")

            logger.info(f"Completed adding wrong answers to mistake book")
        except Exception as e:
            logger.error(f"Failed to add wrong answers to mistake book: {e}")
