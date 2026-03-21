"""Settings panel with dark theme styling."""

from __future__ import annotations

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Dark Theme Color Tokens (matching main_window.py)
DARK_BG_PRIMARY = "#121212"
DARK_BG_SECONDARY = "#1E1E1E"
DARK_BG_TERTIARY = "#252525"
DARK_TEXT_PRIMARY = "#EAEAEA"
DARK_TEXT_SECONDARY = "#B0B0B0"
DARK_BORDER = "#2E2E2E"
ACCENT_BLUE = "#3B82F6"


class SettingsPanel(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._apply_dark_theme()

    def _setup_ui(self) -> None:
        form = QtWidgets.QFormLayout()
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(16)

        # Similarity slider with label
        slider_container = QtWidgets.QWidget()
        slider_layout = QtWidgets.QHBoxLayout(slider_container)
        slider_layout.setContentsMargins(0, 0, 0, 0)

        self.similarity_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.similarity_slider.setRange(85, 100)
        self.similarity_slider.setValue(90)
        self.similarity_slider.setMinimumWidth(200)

        self.similarity_value = QtWidgets.QLabel("90%")
        self.similarity_value.setFont(QFont("SF Pro Text", 13, QFont.Weight.Bold))
        self.similarity_value.setStyleSheet(f"color: {ACCENT_BLUE}; background: transparent;")

        self.similarity_slider.valueChanged.connect(
            lambda v: self.similarity_value.setText(f"{v}%")
        )

        slider_layout.addWidget(self.similarity_slider)
        slider_layout.addWidget(self.similarity_value)

        # Label for the form row
        label = QtWidgets.QLabel("Image similarity %")
        label.setFont(QFont("SF Pro Text", 14))
        label.setStyleSheet(f"color: {DARK_TEXT_SECONDARY}; background: transparent;")

        form.addRow(label, slider_container)
        self.setLayout(form)

    def _apply_dark_theme(self) -> None:
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {DARK_BG_PRIMARY};
            }}
            QSlider::groove:horizontal {{
                height: 8px;
                background: {DARK_BG_TERTIARY};
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {ACCENT_BLUE};
                border: none;
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }}
            QSlider::sub-page:horizontal {{
                background: {ACCENT_BLUE};
                border-radius: 4px;
            }}
        """)
