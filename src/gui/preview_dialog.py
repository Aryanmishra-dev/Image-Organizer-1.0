"""Dialog to preview duplicate groups with dark theme."""
from __future__ import annotations

from PyQt6 import QtWidgets
from PyQt6.QtGui import QFont


# Dark Theme Color Tokens (matching main_window.py)
DARK_BG_PRIMARY = "#121212"
DARK_BG_SECONDARY = "#1E1E1E"
DARK_BG_TERTIARY = "#252525"
DARK_BG_HOVER = "#2A2A2A"
DARK_TEXT_PRIMARY = "#EAEAEA"
DARK_TEXT_SECONDARY = "#B0B0B0"
DARK_BORDER = "#2E2E2E"
ACCENT_BLUE = "#3B82F6"


class PreviewDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Duplicate Preview")
        self.resize(900, 600)
        self._setup_ui()
        self._apply_dark_theme()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QtWidgets.QLabel("🔍 Duplicate Preview")
        header.setFont(QFont("SF Pro Display", 20, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(header)
        
        # List view
        self.list_view = QtWidgets.QListWidget()
        self.list_view.setStyleSheet(f"""
            QListWidget {{
                background-color: {DARK_BG_SECONDARY};
                border: 1px solid {DARK_BORDER};
                border-radius: 10px;
                color: {DARK_TEXT_PRIMARY};
                padding: 8px;
            }}
            QListWidget::item {{
                padding: 12px;
                border-radius: 6px;
                color: {DARK_TEXT_PRIMARY};
            }}
            QListWidget::item:hover {{
                background-color: {DARK_BG_HOVER};
            }}
            QListWidget::item:selected {{
                background-color: {ACCENT_BLUE};
                color: #FFFFFF;
            }}
        """)
        layout.addWidget(self.list_view)
        
        # Close button
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_BG_TERTIARY};
                color: {DARK_TEXT_PRIMARY};
                border: 1px solid {DARK_BORDER};
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {DARK_BG_HOVER};
            }}
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

    def _apply_dark_theme(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DARK_BG_PRIMARY};
            }}
        """)
