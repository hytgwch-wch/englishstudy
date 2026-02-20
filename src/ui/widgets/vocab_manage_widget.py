"""
Vocabulary Manager Widget

Manages vocabulary libraries and imports.
"""

import logging
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from config import config
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)


class VocabManagerWidget(QWidget):
    """
    Widget for managing vocabulary libraries.

    Features:
    - View available vocabularies
    - Import new vocabularies
    - Delete vocabularies
    - View vocabulary statistics
    """

    # Signals
    vocab_imported = pyqtSignal(str)
    vocab_selected = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize vocabulary manager widget"""
        super().__init__(parent)

        self._setup_ui()
        self._load_vocabularies()

    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("📚 词库管理")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; color: #cba6f7;")
        layout.addWidget(title)

        layout.addSpacing(10)

        # Main content
        content_layout = QHBoxLayout()

        # Left panel - Available vocabularies
        left_panel = self._create_vocab_list_panel()
        content_layout.addWidget(left_panel)

        # Right panel - Details and actions
        right_panel = self._create_details_panel()
        content_layout.addWidget(right_panel)

        layout.addLayout(content_layout)

    def _create_vocab_list_panel(self) -> QGroupBox:
        """Create the vocabulary list panel"""
        group = QGroupBox("可用词库")
        layout = QVBoxLayout(group)

        # Vocabulary list
        self.vocab_list = QListWidget()
        self.vocab_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.vocab_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.vocab_list)

        # Import button
        import_layout = QHBoxLayout()
        self.import_button = QPushButton("导入词库")
        self.import_button.setProperty("class", "primary")
        self.import_button.clicked.connect(self._import_vocabulary)
        import_layout.addWidget(self.import_button)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self._load_vocabularies)
        import_layout.addWidget(self.refresh_button)

        layout.addLayout(import_layout)

        return group

    def _create_details_panel(self) -> QGroupBox:
        """Create the vocabulary details panel"""
        group = QGroupBox("词库详情")
        layout = QVBoxLayout(group)

        # Details labels
        grid = QGridLayout()

        self.name_label = QLabel("名称: -")
        grid.addWidget(self.name_label, 0, 0)

        self.format_label = QLabel("格式: -")
        grid.addWidget(self.format_label, 1, 0)

        self.words_label = QLabel("单词数: -")
        grid.addWidget(self.words_label, 2, 0)

        self.level_label = QLabel("难度: -")
        grid.addWidget(self.level_label, 3, 0)

        layout.addLayout(grid)

        layout.addSpacing(20)

        # Description
        desc_title = QLabel("描述:")
        desc_title.setStyleSheet("font-weight: bold;")
        layout.addWidget(desc_title)

        self.description_label = QLabel("-")
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        layout.addStretch()

        # Progress bar for import
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Action buttons
        action_layout = QHBoxLayout()

        self.select_button = QPushButton("选择此词库")
        self.select_button.setProperty("class", "success")
        self.select_button.setEnabled(False)
        self.select_button.clicked.connect(self._on_select_clicked)
        action_layout.addWidget(self.select_button)

        self.delete_button = QPushButton("删除")
        self.delete_button.setProperty("class", "danger")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self._delete_vocabulary)
        action_layout.addWidget(self.delete_button)

        layout.addLayout(action_layout)

        return group

    def _load_vocabularies(self):
        """Load available vocabularies"""
        self.vocab_list.clear()

        try:
            from src.services.vocab_manager import get_vocab_manager
            vocab_manager = get_vocab_manager()

            vocabularies = vocab_manager.get_available_vocabularies()

            for vocab_info in vocabularies:
                item = QListWidgetItem(vocab_info["name"])
                item.setData(Qt.ItemDataRole.UserRole, vocab_info)

                # Add format indicator
                format_badge = f"[{vocab_info['format']}]"
                item.setText(f"{format_badge} {vocab_info['name']}")

                self.vocab_list.addItem(item)

            logger.info(f"Loaded {len(vocabularies)} vocabularies")

        except Exception as e:
            logger.error(f"Failed to load vocabularies: {e}")
            QMessageBox.warning(self, "加载失败", f"无法加载词库列表: {e}")

    def _on_selection_changed(self):
        """Handle vocabulary selection change"""
        selected_items = self.vocab_list.selectedItems()
        if not selected_items:
            self._clear_details()
            self.select_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return

        item = selected_items[0]
        vocab_info = item.data(Qt.ItemDataRole.UserRole)

        self._display_details(vocab_info)
        self.select_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def _display_details(self, vocab_info: dict):
        """Display vocabulary details"""
        self.name_label.setText(f"名称: {vocab_info['name']}")
        self.format_label.setText(f"格式: {vocab_info['format']}")

        info = vocab_info.get('info', {})
        word_count = info.get('total_words', '?')
        self.words_label.setText(f"单词数: {word_count}")

        level = info.get('level', '-')
        level_names = {
            'elementary': '小学',
            'middle': '初中',
            'high': '高中',
            'cet4': '四级',
            'cet6': '六级'
        }
        self.level_label.setText(f"难度: {level_names.get(level, level)}")

        description = info.get('description', '-')
        self.description_label.setText(description)

    def _clear_details(self):
        """Clear the details panel"""
        self.name_label.setText("名称: -")
        self.format_label.setText("格式: -")
        self.words_label.setText("单词数: -")
        self.level_label.setText("难度: -")
        self.description_label.setText("-")

    def _on_select_clicked(self):
        """Handle select vocabulary button click"""
        selected_items = self.vocab_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        vocab_info = item.data(Qt.ItemDataRole.UserRole)

        logger.info(f"Vocabulary selected: {vocab_info['name']}")
        self.vocab_selected.emit(vocab_info['path'])

        QMessageBox.information(
            self,
            "词库已选择",
            f"已选择词库: {vocab_info['name']}\n"
            f"单词数: {vocab_info['info'].get('total_words', '?')}"
        )

    def _import_vocabulary(self):
        """Handle import vocabulary button click"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入词库",
            "",
            "词库文件 (*.json *.csv *.txt);;JSON 文件 (*.json);;CSV 文件 (*.csv);;文本文件 (*.txt);;所有文件 (*.*)"
        )

        if not file_path:
            return

        logger.info(f"Importing vocabulary: {file_path}")

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        try:
            from src.services.vocab_manager import get_vocab_manager
            vocab_manager = get_vocab_manager()

            # Load vocabulary
            vocab_set = vocab_manager.load_vocabulary_file(file_path)

            # Import to database
            stats = vocab_manager.import_vocabulary_to_db(vocab_set)

            self.progress_bar.setVisible(False)

            QMessageBox.information(
                self,
                "导入成功",
                f"词库导入成功！\n\n"
                f"新增: {stats['imported']} 个单词\n"
                f"更新: {stats['updated']} 个单词\n"
                f"错误: {stats['errors']} 个单词"
            )

            self.vocab_imported.emit(file_path)
            self._load_vocabularies()

        except Exception as e:
            self.progress_bar.setVisible(False)
            logger.error(f"Failed to import vocabulary: {e}")
            QMessageBox.critical(
                self,
                "导入失败",
                f"无法导入词库:\n{e}"
            )

    def _delete_vocabulary(self):
        """Handle delete vocabulary button click"""
        selected_items = self.vocab_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        vocab_info = item.data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除词库 \"{vocab_info['name']}\" 吗？\n\n"
            f"这将删除词库文件，但不会影响已学习的进度。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            logger.info(f"Deleting vocabulary: {vocab_info['path']}")

            try:
                import os
                os.remove(vocab_info['path'])

                QMessageBox.information(
                    self,
                    "删除成功",
                    f"词库 \"{vocab_info['name']}\" 已删除"
                )

                self._load_vocabularies()

            except Exception as e:
                logger.error(f"Failed to delete vocabulary: {e}")
                QMessageBox.critical(
                    self,
                    "删除失败",
                    f"无法删除词库:\n{e}"
                )

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle vocabulary item double-click"""
        self._on_select_clicked()
