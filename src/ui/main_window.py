"""
Main Window for EnglishStudy Application

Primary UI window with navigation and content management.
"""

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QStatusBar,
    QToolBar, QMenuBar, QMenu, QMessageBox, QFileDialog,
    QDialog, QListWidget, QListWidgetItem, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from config import config
from src.ui.styles.dark_theme import load_stylesheet
from src.ui.widgets.card_widget import WordCardWidget
from src.ui.widgets.test_widget import TestWidget
from src.ui.widgets.vocab_manage_widget import VocabManagerWidget
from src.models.user import User, UserLevel
from src.models.word_record import MemoryStatus
from src.infrastructure.logger import get_logger
from src.infrastructure.database import DatabaseManager, get_db
from src.services.vocab_manager import VocabularyManager, get_vocab_manager
from src.services.study_manager import StudyManager, get_study_manager
from src.services.test_manager import TestManager, get_test_manager

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window.
    """

    vocab_selection_changed = pyqtSignal(str)

    def __init__(self):
        """Initialize main window"""
        super().__init__()

        # Initialize managers
        self.db = get_db()
        self.db.init_database()
        self.vocab_manager = get_vocab_manager()
        self.study_manager = StudyManager(db_manager=self.db)
        self.test_manager = TestManager(db_manager=self.db)

        # User
        self._ensure_user()
        self.current_user_id = 1
        self.current_user = self._get_or_create_user()

        # Current vocabulary filter
        self.current_vocab_filter = None  # None = all vocabularies

        # Widgets
        self.welcome_view = None
        self.study_view = None
        self.test_view = None
        self.vocab_view = None
        self.stats_view = None
        self.mistake_view = None
        self.new_word_view = None

        # Study session state
        self.study_queue = []
        self.current_word_index = 0
        self.session_stats = {"correct": 0, "total": 0}
        self.session_mode = "study"  # "study" or "review"

        self._setup_window()
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        self._initialize_builtin_vocabularies()

        logger.info("Main window initialized")

    def _ensure_user(self):
        """Ensure default user exists"""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM users LIMIT 1")
            user = cursor.fetchone()
            if user is None:
                conn.execute(
                    "INSERT INTO users (name, level) VALUES (?, ?)",
                    ("学生", "elementary")
                )
                conn.commit()
                logger.info("Created default user")

    def _get_or_create_user(self) -> User:
        """Get or create the current user"""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM users LIMIT 1")
            user_data = cursor.fetchone()
            if user_data:
                return User.from_dict(dict(user_data))
            return User(id=None, name="学生", level=UserLevel.ELEMENTARY)

    def _setup_window(self):
        """Configure window properties"""
        self.setWindowTitle(f"{config.APP_NAME} v{config.VERSION}")
        self.setMinimumSize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.setStyleSheet(load_stylesheet())

    def _setup_ui(self):
        """Setup central widget and layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        self._create_views()
        self.stacked_widget.setCurrentWidget(self.welcome_view)

    def _create_views(self):
        """Create all application views"""
        # Welcome view
        self.welcome_view = self._create_welcome_view()
        self.stacked_widget.addWidget(self.welcome_view)

        # Study view
        self.study_view = self._create_study_view()
        self.stacked_widget.addWidget(self.study_view)

        # Test view
        self.test_view = TestWidget(test_manager=self.test_manager)
        self.test_view.test_completed.connect(self._on_test_completed)
        self.stacked_widget.addWidget(self.test_view)

        # Vocab manager view
        self.vocab_view = VocabManagerWidget()
        self.vocab_view.vocab_imported.connect(self._on_vocab_imported)
        self.vocab_view.vocab_selected.connect(self._on_vocab_selected)
        self.stacked_widget.addWidget(self.vocab_view)

        # Statistics view
        self.stats_view = self._create_stats_view()
        self.stacked_widget.addWidget(self.stats_view)

        # Mistake book view
        self.mistake_view = self._create_notebook_view("mistake")
        self.stacked_widget.addWidget(self.mistake_view)

        # New word book view
        self.new_word_view = self._create_notebook_view("new_word")
        self.stacked_widget.addWidget(self.new_word_view)

    def _create_welcome_view(self) -> QWidget:
        """Create welcome view"""
        welcome = QWidget()
        layout = QVBoxLayout(welcome)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("📚 EnglishStudy")
        title.setStyleSheet("font-size: 32pt; font-weight: bold; color: #cba6f7;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("个性化英语单词学习软件")
        subtitle.setStyleSheet("font-size: 16pt; color: #a6adc8;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Current vocab display
        self.current_vocab_label = QLabel("当前词库: 全部词库")
        self.current_vocab_label.setStyleSheet("font-size: 12pt; color: #89b4fa; margin-top: 10px;")
        self.current_vocab_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Quick action buttons
        button_layout = QHBoxLayout()

        study_btn = QPushButton("开始学习")
        study_btn.setProperty("class", "primary")
        study_btn.setMinimumSize(150, 50)
        study_btn.clicked.connect(self._start_study)

        vocab_btn = QPushButton("词库管理")
        vocab_btn.setMinimumSize(150, 50)
        vocab_btn.clicked.connect(self._show_vocab_manager)

        button_layout.addWidget(study_btn)
        button_layout.addWidget(vocab_btn)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("快捷键: Ctrl+S 学习 | Ctrl+T 测试 | Ctrl+R 复习")
        hint.setStyleSheet("font-size: 10pt; color: #6c7086; margin-top: 30px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.current_vocab_label)
        layout.addSpacing(20)
        layout.addLayout(button_layout)
        layout.addWidget(hint)
        layout.addStretch()

        return welcome

    def _create_study_view(self) -> QWidget:
        """Create study view with word card"""
        study_widget = QWidget()
        layout = QVBoxLayout(study_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QHBoxLayout()
        back_btn = QPushButton("← 返回")
        back_btn.clicked.connect(self._back_to_welcome)

        title = QLabel("学习模式")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #cba6f7;")

        header.addWidget(back_btn)
        header.addWidget(title)
        header.addStretch()

        layout.addLayout(header)

        # Word card
        self.word_card = WordCardWidget()
        self.word_card.answer_submitted.connect(self._on_answer_submitted)
        self.word_card.next_requested.connect(self._show_next_word)
        self.word_card.previous_requested.connect(self._show_previous_word)

        layout.addWidget(self.word_card, alignment=Qt.AlignmentFlag.AlignCenter)

        return study_widget

    def _create_stats_view(self) -> QWidget:
        """Create statistics view"""
        stats_widget = QWidget()
        layout = QVBoxLayout(stats_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("📊 学习统计")
        title.setStyleSheet("font-size: 24pt; font-weight: bold; color: #cba6f7;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(30)

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("font-size: 14pt; color: #cdd6f4;")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stats_label)

        layout.addSpacing(20)

        refresh_btn = QPushButton("刷新统计")
        refresh_btn.clicked.connect(self._refresh_stats)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        back_btn = QPushButton("返回")
        back_btn.clicked.connect(self._back_to_welcome)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return stats_widget

    def _create_notebook_view(self, notebook_type: str) -> QWidget:
        """Create notebook view (mistake or new word)"""
        notebook_widget = QWidget()
        layout = QVBoxLayout(notebook_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()

        back_btn = QPushButton("← 返回")
        back_btn.clicked.connect(self._back_to_welcome)

        title = QLabel("错题本" if notebook_type == "mistake" else "生词本")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #cba6f7;")

        header_layout.addWidget(back_btn)
        header_layout.addWidget(title)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Word list - each notebook view has its own list
        list_widget = QListWidget()
        list_widget.setStyleSheet("font-size: 12pt;")
        layout.addWidget(list_widget)

        # Store the list widget as an attribute of the notebook widget
        notebook_widget.list_widget = list_widget
        # Store notebook type
        notebook_widget.notebook_type = notebook_type

        return notebook_widget

    def _initialize_builtin_vocabularies(self):
        """Initialize built-in vocabularies"""
        try:
            stats = self.vocab_manager.initialize_builtin_vocabularies()
            if stats["total_imported"] > 0:
                self.update_status(f"已导入 {stats['total_imported']} 个内置单词", 5000)
                logger.info(f"Initialized {stats['total_imported']} built-in words")
        except Exception as e:
            logger.error(f"Failed to initialize built-in vocabularies: {e}")

    def _setup_menu_bar(self):
        """Setup menu bar"""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("文件(&F)")

        import_action = QAction("导入词库(&I)...", self)
        import_action.setShortcut(QKeySequence.StandardKey.Open)
        import_action.setStatusTip("导入词库文件")
        import_action.triggered.connect(self._import_vocabulary)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip("退出应用")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Study Menu
        study_menu = menubar.addMenu("学习(&S)")

        start_study_action = QAction("开始学习(&S)", self)
        start_study_action.setShortcut(QKeySequence("Ctrl+S"))
        start_study_action.setStatusTip("开始学习新单词")
        start_study_action.triggered.connect(self._start_study)
        study_menu.addAction(start_study_action)

        review_action = QAction("今日复习(&R)", self)
        review_action.setShortcut(QKeySequence("Ctrl+R"))
        review_action.setStatusTip("复习今日待复习单词")
        review_action.triggered.connect(self._start_review)
        study_menu.addAction(review_action)

        study_menu.addSeparator()

        mistake_book_action = QAction("错题本(&M)", self)
        mistake_book_action.setStatusTip("查看错题本")
        mistake_book_action.triggered.connect(self._show_mistake_book)
        study_menu.addAction(mistake_book_action)

        new_word_book_action = QAction("生词本(&N)", self)
        new_word_book_action.setStatusTip("查看生词本")
        new_word_book_action.triggered.connect(self._show_new_word_book)
        study_menu.addAction(new_word_book_action)

        # Test Menu
        test_menu = menubar.addMenu("测试(&T)")

        quick_test_action = QAction("快速测试(&Q)", self)
        quick_test_action.setShortcut(QKeySequence("Ctrl+T"))
        quick_test_action.setStatusTip("开始快速测试")
        quick_test_action.triggered.connect(self._start_test)
        test_menu.addAction(quick_test_action)

        # View Menu
        view_menu = menubar.addMenu("视图(&V)")

        vocab_manage_action = QAction("词库管理(&V)", self)
        vocab_manage_action.setStatusTip("管理词库")
        vocab_manage_action.triggered.connect(self._show_vocab_manager)
        view_menu.addAction(vocab_manage_action)

        clear_vocab_action = QAction("清除词库筛选(&C)", self)
        clear_vocab_action.setStatusTip("显示全部词库")
        clear_vocab_action.triggered.connect(self._clear_vocab_filter)
        view_menu.addAction(clear_vocab_action)

        view_menu.addSeparator()

        stats_action = QAction("学习统计(&S)", self)
        stats_action.setStatusTip("查看学习统计")
        stats_action.triggered.connect(self._show_statistics)
        view_menu.addAction(stats_action)

        # Help Menu
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.setStatusTip("关于 EnglishStudy")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Setup toolbar"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        study_action = QAction("开始学习", self)
        study_action.triggered.connect(self._start_study)
        toolbar.addAction(study_action)

        review_action = QAction("今日复习", self)
        review_action.triggered.connect(self._start_review)
        toolbar.addAction(review_action)

        toolbar.addSeparator()

        test_action = QAction("快速测试", self)
        test_action.triggered.connect(self._start_test)
        toolbar.addAction(test_action)

        toolbar.addSeparator()

        vocab_action = QAction("词库管理", self)
        vocab_action.triggered.connect(self._show_vocab_manager)
        toolbar.addAction(vocab_action)

    def _setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("欢迎使用 EnglishStudy！")

    # ========== Study Session ==========

    def _start_study(self):
        """Start study session"""
        self.session_mode = "study"
        self._load_study_session(new_words=10, review_words=0)

    def _start_review(self):
        """Start review session"""
        self.session_mode = "review"
        self._load_study_session(new_words=0, review_words=50)

    def _load_study_session(self, new_words: int, review_words: int):
        """Load study session with specified word counts"""
        try:
            queue = self._get_filtered_study_queue(new_words, review_words)

            self.study_queue = queue.get("new", []) + queue.get("review", [])
            self.current_word_index = 0
            self.session_stats = {"correct": 0, "total": 0}

            if not self.study_queue:
                QMessageBox.information(
                    self, self.session_mode.capitalize(),
                    "没有可学习的单词。\n\n请先导入词库或更换词库。"
                )
                return

            self.study_manager.start_session(self.current_user, self.session_mode)
            self._show_current_word()
            self.stacked_widget.setCurrentWidget(self.study_view)

            total = len(self.study_queue)
            self.word_card.set_session_stats(0, 0, total)

            logger.info(f"Started {self.session_mode} session with {total} words")

        except Exception as e:
            logger.error(f"Failed to start study: {e}")
            QMessageBox.critical(self, "错误", f"无法开始学习: {e}")

    def _get_filtered_study_queue(self, new_words: int, review_words: int) -> dict:
        """Get study queue filtered by current vocabulary selection"""
        # If a specific vocab is selected, we need to get words from that vocab
        if self.current_vocab_filter:
            # Get words from the selected vocabulary file
            vocab_info = self._get_vocab_info_by_name(self.current_vocab_filter)
            if vocab_info:
                # Get the vocabulary IDs from this file
                vocab_ids = self._get_vocab_ids_from_file(vocab_info["path"])
                if vocab_ids:
                    return self._get_study_queue_from_vocab_ids(vocab_ids, new_words, review_words)

        # Default: use all vocabularies
        return self.study_manager.get_study_queue(
            self.current_user,
            max_new=new_words,
            max_review=review_words
        )

    def _get_vocab_info_by_name(self, name: str) -> Optional[dict]:
        """Get vocabulary info by name"""
        for vocab in self.vocab_manager.get_available_vocabularies():
            if vocab["name"] == name:
                return vocab
        return None

    def _get_vocab_ids_from_file(self, file_path: str) -> list:
        """Get vocabulary IDs from a specific file"""
        from src.infrastructure.vocab_loader import VocabLoader
        loader = VocabLoader()

        try:
            vocab_set = loader.load_vocabulary(file_path)
            vocab_ids = []

            with self.db.get_connection() as conn:
                # Get vocab words from the VocabularySet
                words = vocab_set.words if hasattr(vocab_set, 'words') else []
                for vocab in words:
                    word = vocab.word if hasattr(vocab, 'word') else vocab.get('word', '')
                    cursor = conn.execute(
                        "SELECT id FROM vocabularies WHERE word = ?",
                        (word,)
                    )
                    row = cursor.fetchone()
                    if row:
                        vocab_ids.append(row[0])

            return vocab_ids
        except Exception as e:
            logger.error(f"Failed to get vocab IDs from file: {e}")
            return []

    def _get_study_queue_from_vocab_ids(self, vocab_ids: list, new_words: int, review_words: int) -> dict:
        """Get study queue from specific vocabulary IDs"""
        new_words_data = []
        review_words_data = []

        with self.db.get_connection() as conn:
            # Get due review words from selected vocab
            if review_words > 0:
                placeholders = ",".join("?" * len(vocab_ids))
                cursor = conn.execute(
                    f"""
                    SELECT wr.*, v.word, v.phonetic, v.definition, v.example, v.difficulty, v.id as vocab_id
                    FROM word_records wr
                    JOIN vocabularies v ON wr.vocabulary_id = v.id
                    WHERE wr.user_id = ?
                      AND wr.vocabulary_id IN ({placeholders})
                      AND wr.next_review IS NOT NULL
                      AND wr.next_review <= datetime('now')
                      AND wr.state != 'mastered'
                    ORDER BY wr.next_review ASC
                    LIMIT ?
                    """,
                    [self.current_user.id] + vocab_ids + [review_words]
                )
                review_words_data = [dict(row) for row in cursor.fetchall()]

            # Get new words from selected vocab
            if new_words > 0:
                cursor = conn.execute(
                    f"""
                    SELECT v.*, v.id as vocab_id
                    FROM vocabularies v
                    WHERE v.id IN ({placeholders})
                      AND v.id NOT IN (
                          SELECT wr.vocabulary_id
                          FROM word_records wr
                          WHERE wr.user_id = ?
                      )
                    LIMIT ?
                    """,
                    vocab_ids + [self.current_user.id, new_words]
                )
                new_words_data = [dict(row) for row in cursor.fetchall()]

        return {"new": new_words_data, "review": review_words_data}

    def _show_current_word(self):
        """Show current word in card"""
        if 0 <= self.current_word_index < len(self.study_queue):
            word_data = self.study_queue[self.current_word_index]
            remaining = len(self.study_queue) - self.current_word_index - 1
            self.word_card.display_word(word_data, remaining)

            can_go_back = self.current_word_index > 0
            can_go_forward = self.current_word_index < len(self.study_queue) - 1
            self.word_card.enable_navigation(can_go_back, can_go_forward)
        else:
            self._finish_study_session()

    def _show_next_word(self):
        """Show next word"""
        # First increment the index
        self.current_word_index += 1

        # Check if we've completed all words
        if self.current_word_index >= len(self.study_queue):
            # Session completed
            self._finish_study_session()
        else:
            # Show next word
            self._show_current_word()

    def _show_previous_word(self):
        """Show previous word"""
        if self.current_word_index > 0:
            self.current_word_index -= 1
            self._show_current_word()

    def _on_answer_submitted(self, vocab_id: int, status: str):
        """Handle answer submission"""
        try:
            memory_status = MemoryStatus.from_string(status)

            result = self.study_manager.submit_answer(
                self.current_user,
                vocab_id,
                memory_status
            )

            # Add to new word book if user doesn't know the word
            if memory_status == MemoryStatus.HARD:
                self._add_to_new_word_book(vocab_id)

            self.session_stats["total"] += 1
            if memory_status.is_correct():
                self.session_stats["correct"] += 1

            remaining = len(self.study_queue) - self.current_word_index - 1
            self.word_card.set_session_stats(
                self.session_stats["total"],
                self.session_stats["correct"],
                remaining
            )

            self._show_next_word()

        except Exception as e:
            logger.error(f"Failed to submit answer: {e}")

    def _finish_study_session(self):
        """Finish study session and show results"""
        try:
            # Disable buttons immediately to prevent further clicks
            self.word_card.clear_card()

            self.study_manager.end_session()

            total = self.session_stats["total"]
            correct = self.session_stats["correct"]
            accuracy = int((correct / total * 100)) if total > 0 else 0

            # Ask if user wants to continue
            reply = QMessageBox.question(
                self,
                "学习完成",
                f"🎉 本次学习完成！\n\n"
                f"学习单词: {total} 个\n"
                f"正确率: {accuracy}%\n\n"
                f"是否继续学习更多单词？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Load more words
                if self.session_mode == "review":
                    self._load_study_session(0, 50)
                else:
                    self._load_study_session(10, 0)
            else:
                self._back_to_welcome()

        except Exception as e:
            logger.error(f"Failed to finish session: {e}")
            self._back_to_welcome()

    def _add_to_new_word_book(self, vocab_id: int):
        """Add a word to the new word book"""
        try:
            # Get or create word record
            word_record = self.db.get_or_create_word_record(
                self.current_user_id,
                vocab_id
            )
            if word_record:
                self.db.add_to_new_word_book(
                    self.current_user_id,
                    word_record["id"],
                    note=""
                )
                logger.info(f"Added vocab_id {vocab_id} to new word book")
        except Exception as e:
            logger.error(f"Failed to add to new word book: {e}")

    # ========== Test ==========

    def _start_test(self):
        """Start test"""
        self.stacked_widget.setCurrentWidget(self.test_view)

    def _on_test_completed(self, result):
        """Handle test completion"""
        QMessageBox.information(
            self, "测试完成",
            f"测试得分: {result.score:.0f}%\n"
            f"{'通过 ✓' if result.passed else '未通过 ✗'}"
        )

    # ========== Vocabulary Management ==========

    def _import_vocabulary(self):
        """Import vocabulary from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入词库",
            str(config.vocab_path),
            "词库文件 (*.json *.csv *.txt);;所有文件 (*.*)"
        )

        if file_path:
            try:
                vocab_set = self.vocab_manager.load_vocabulary_file(file_path)
                stats = self.vocab_manager.import_vocabulary_to_db(vocab_set)

                QMessageBox.information(
                    self, "导入成功",
                    f"词库导入成功！\n\n"
                    f"新增: {stats['imported']} 个\n"
                    f"更新: {stats['updated']} 个\n"
                    f"错误: {stats['errors']} 个"
                )

                self._on_vocab_imported(file_path)

            except Exception as e:
                logger.error(f"Failed to import vocabulary: {e}")
                QMessageBox.critical(self, "导入失败", f"无法导入词库:\n{e}")

    def _on_vocab_imported(self, file_path: str):
        """Handle vocabulary import"""
        self.update_status(f"已导入: {Path(file_path).name}", 3000)

    def _on_vocab_selected(self, vocab_path: str):
        """Handle vocabulary selection - set as current vocabulary"""
        vocab_name = Path(vocab_path).stem
        self.current_vocab_filter = vocab_name
        self.current_vocab_label.setText(f"当前词库: {vocab_name}")
        self.update_status(f"已选择词库: {vocab_name}", 3000)

        # Check if user is currently in study mode
        if self.stacked_widget.currentWidget() == self.study_view:
            # If there's an active study session, ask if user wants to restart with new vocabulary
            if self.study_queue and self.current_word_index >= 0:
                reply = QMessageBox.question(
                    self, "切换词库",
                    f"已选择词库: {vocab_name}\n\n"
                    f"当前正在学习中，是否立即切换到新词库？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    # Restart study session with new vocabulary
                    self._start_learning()
                    return

        # Otherwise, just show info message
        QMessageBox.information(
            self, "词库已选择",
            f"已切换到词库: {vocab_name}\n\n"
            f"现在开始学习将只学习该词库的单词。"
        )

    def _clear_vocab_filter(self):
        """Clear vocabulary filter - use all vocabularies"""
        self.current_vocab_filter = None
        self.current_vocab_label.setText("当前词库: 全部词库")
        self.update_status("已清除词库筛选，使用全部词库", 3000)

    # ========== Notebook Views ==========

    def _show_mistake_book(self):
        """Show mistake book"""
        self.stacked_widget.setCurrentWidget(self.mistake_view)
        self._load_notebook("mistake")

    def _show_new_word_book(self):
        """Show new word book"""
        self.stacked_widget.setCurrentWidget(self.new_word_view)
        self._load_notebook("new_word")

    def _load_notebook(self, notebook_type: str):
        """Load notebook entries"""
        try:
            logger.info(f"Loading notebook: {notebook_type} for user {self.current_user_id}")

            if notebook_type == "mistake":
                entries = self.study_manager.get_mistake_book(self.current_user)
                list_widget = self.mistake_view.list_widget
            else:
                entries = self.study_manager.get_new_word_book(self.current_user)
                list_widget = self.new_word_view.list_widget

            logger.info(f"Got {len(entries)} entries for {notebook_type} notebook")

            list_widget.clear()

            if not entries:
                list_widget.addItem("📭 暂无单词")
                logger.info(f"No entries found in {notebook_type} notebook")
                return

            for entry in entries:
                word = entry.get("word", "")
                definition = entry.get("definition", "")
                item_text = f"{word} - {definition}"
                list_widget.addItem(item_text)
                logger.debug(f"Added to list: {item_text}")

            logger.info(f"Successfully loaded {len(entries)} entries to UI")

        except Exception as e:
            logger.error(f"Failed to load notebook: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # ========== Statistics ==========

    def _show_statistics(self):
        """Show statistics view"""
        self._refresh_stats()
        self.stacked_widget.setCurrentWidget(self.stats_view)

    def _refresh_stats(self):
        """Refresh statistics display"""
        try:
            stats = self.study_manager.get_user_stats(self.current_user)

            text = f"""
            <h3>学习统计</h3>

            <table style="margin: 20px auto;">
                <tr><td><b>已学习单词</b></td><td>{stats['total_studied']} 个</td></tr>
                <tr><td><b>已掌握单词</b></td><td>{stats['mastered']} 个</td></tr>
                <tr><td><b>待复习单词</b></td><td>{stats['due_for_review']} 个</td></tr>
                <tr><td><b>用户等级</b></td><td>{stats['user_rating']:.0f}</td></tr>
                <tr><td><b>推荐难度</b></td><td>{stats['recommended_difficulty']}/10</td></tr>
                <tr><td><b>能力评级</b></td><td>{stats['performance_level']}</td></tr>
            </table>

            <p style="text-align: center; color: #6c7086; margin-top: 30px;">
                {stats['total_studied']} 个单词中，已掌握 {stats['mastered']} 个
                ({int(stats.get('progress_rate', 0) * 100)}%)
            </p>
            """

            self.stats_label.setText(text)

        except Exception as e:
            logger.error(f"Failed to load statistics: {e}")
            self.stats_label.setText("加载统计失败")

    # ========== View Management ==========

    def _show_vocab_manager(self):
        """Show vocabulary manager"""
        self.stacked_widget.setCurrentWidget(self.vocab_view)

    def _back_to_welcome(self):
        """Return to welcome view"""
        self.stacked_widget.setCurrentWidget(self.welcome_view)

    def _show_about(self):
        """Show about dialog"""
        about_text = f"""
        <h2>{config.APP_NAME}</h2>
        <p>版本 {config.VERSION}</p>
        <p>个性化英语单词学习软件</p>
        <p>基于 SM-2 间隔重复算法和 ELO 难度自适应系统</p>
        <hr>
        <p>© 2026 EnglishStudy Team</p>
        """

        QMessageBox.about(self, f"关于 {config.APP_NAME}", about_text)

    def update_status(self, message: str, timeout: int = 0):
        """Update status bar message"""
        self.status_bar.showMessage(message, timeout)


def load_stylesheet() -> str:
    """Load the dark theme stylesheet"""
    style_path = Path(__file__).parent / "styles" / "dark_theme.qss"
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load stylesheet: {e}")
        return ""
