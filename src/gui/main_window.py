"""
Image Organizer - Modern AI-Powered File Management
Clean PyQt6 interface with smart duplicate detection and organization.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QProgressBar,
    QMessageBox,
    QHeaderView,
    QComboBox,
    QSpinBox,
    QGroupBox,
    QFormLayout,
    QSplitter,
    QFrame,
    QCheckBox,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QGridLayout,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QMenu,
    QSlider,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QMimeData, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap, QDragEnterEvent, QDropEvent

from core.scanner import FileScanner, ScanConfig, format_size
from core.hasher import ParallelHasher
from core.comparator import DuplicateComparator, ComparisonResult
from core.agent import DuplicateAgent
from core.cleaner import Cleaner


class ScanThread(QThread):
    """Background thread for scanning and hashing files."""
    
    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(object)  # ComparisonResult
    error = pyqtSignal(str)
    
    def __init__(
        self,
        folders: List[Path],
        file_type: str,
        similarity: int,
        include_perceptual: bool,
    ):
        super().__init__()
        self.folders = folders
        self.file_type = file_type
        self.similarity = similarity
        self.include_perceptual = include_perceptual
    
    def run(self):
        try:
            # Configure scanner
            config = ScanConfig(batch_size=500, min_size=1)
            
            if self.file_type != "all":
                config.file_extensions = FileScanner.get_extensions_for_type(self.file_type)
            
            scanner = FileScanner(config)
            hasher = ParallelHasher(
                compute_perceptual=self.include_perceptual and self.file_type in ("all", "images"),
            )
            comparator = DuplicateComparator(similarity_threshold=self.similarity)
            
            # Stage 1: Scan
            self.progress.emit(0, 0, "🔍 Scanning folders...")
            all_files = []
            for batch in scanner.scan(self.folders):
                all_files.extend(batch)
                self.progress.emit(len(all_files), 0, f"Found {len(all_files):,} files...")
            
            if not all_files:
                self.progress.emit(0, 0, "No files found")
                self.finished.emit(ComparisonResult())
                return
            
            # Stage 2: Group by size (optimization)
            self.progress.emit(0, 0, "📊 Grouping by size...")
            size_groups = {}
            for f in all_files:
                if f.size not in size_groups:
                    size_groups[f.size] = []
                size_groups[f.size].append(f)
            
            # Only hash files with size duplicates
            candidates = []
            for size, group in size_groups.items():
                if len(group) > 1:
                    candidates.extend(group)
            
            if not candidates:
                self.progress.emit(100, 100, "No potential duplicates found")
                self.finished.emit(ComparisonResult())
                return
            
            # Stage 3: Hash candidates
            total = len(candidates)
            self.progress.emit(0, total, f"🔐 Hashing {total:,} candidates...")
            
            def hash_progress(done: int, t: int):
                self.progress.emit(done, t, f"Hashing {done:,}/{t:,} files...")
            
            hasher.hash_files(candidates, progress_callback=hash_progress)
            
            # Stage 4: Find duplicates
            self.progress.emit(total, total, "🔎 Finding duplicates...")
            result = comparator.find_all_duplicates(
                candidates,
                include_perceptual=self.include_perceptual,
            )
            
            self.progress.emit(100, 100, "✅ Scan complete!")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class AnalysisThread(QThread):
    """Background thread for AI analysis."""
    
    finished = pyqtSignal(dict)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, duplicate_groups: List[dict], preferences: dict):
        super().__init__()
        self.duplicate_groups = duplicate_groups
        self.preferences = preferences
    
    def run(self):
        try:
            self.status.emit("🤖 Smart agent analyzing duplicates...")
            agent = DuplicateAgent()
            analysis = agent.analyze_duplicates(
                self.duplicate_groups,
                self.preferences,
                status_callback=self.status.emit,
            )
            self.finished.emit(analysis)
        except Exception as e:
            self.error.emit(str(e))


# =============================================================================
# DARK THEME COLOR TOKENS (WCAG 2.1 AA Compliant)
# =============================================================================
# Primary Backgrounds
DARK_BG_PRIMARY = "#121212"        # Main app background
DARK_BG_SECONDARY = "#1E1E1E"     # Cards, panels
DARK_BG_TERTIARY = "#252525"      # Elevated surfaces
DARK_BG_HOVER = "#2A2A2A"         # Hover states
DARK_BG_ACTIVE = "#333333"        # Active/pressed states

# Text Colors (all meet 4.5:1 contrast on dark backgrounds)
DARK_TEXT_PRIMARY = "#EAEAEA"     # Primary text - high contrast
DARK_TEXT_SECONDARY = "#B0B0B0"   # Secondary text
DARK_TEXT_MUTED = "#8A8A8A"       # Muted/placeholder text
DARK_TEXT_DISABLED = "#5C5C5C"    # Disabled text

# Borders & Dividers
DARK_BORDER = "#2E2E2E"           # Subtle borders
DARK_BORDER_LIGHT = "#3A3A3A"     # Lighter borders for emphasis
DARK_DIVIDER = "#2E2E2E"          # Section dividers

# Accent Colors (vibrant for dark backgrounds)
ACCENT_BLUE = "#3B82F6"           # Primary actions
ACCENT_GREEN = "#22C55E"          # Success, positive
ACCENT_PURPLE = "#8B5CF6"         # AI/Smart features
ACCENT_ORANGE = "#F59E0B"         # Warnings, duplicates
ACCENT_RED = "#EF4444"            # Errors, delete
ACCENT_CYAN = "#06B6D4"           # Info

# Accent Hover States
ACCENT_BLUE_HOVER = "#2563EB"
ACCENT_GREEN_HOVER = "#16A34A"
ACCENT_PURPLE_HOVER = "#7C3AED"
ACCENT_ORANGE_HOVER = "#D97706"
ACCENT_RED_HOVER = "#DC2626"


class StatCard(QFrame):
    """Modern statistics card widget with dark theme."""
    
    def __init__(self, title: str, value: str, icon: str, color: str):
        super().__init__()
        self.setObjectName("statCard")
        self.color = color
        self._setup_ui(title, value, icon)
    
    def _setup_ui(self, title: str, value: str, icon: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Icon and title row
        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("SF Pro Display", 22))
        header.addWidget(icon_label)
        header.addStretch()
        layout.addLayout(header)
        
        # Value - bright accent color for emphasis
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("SF Pro Display", 32, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {self.color}; background: transparent;")
        layout.addWidget(self.value_label)
        
        # Title - secondary text for hierarchy
        title_label = QLabel(title)
        title_label.setFont(QFont("SF Pro Text", 13))
        title_label.setStyleSheet(f"color: {DARK_TEXT_SECONDARY}; background: transparent;")
        layout.addWidget(title_label)
        
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: {DARK_BG_SECONDARY};
                border-radius: 12px;
                border: 1px solid {DARK_BORDER};
            }}
            QFrame#statCard:hover {{
                border: 2px solid {self.color};
                background-color: {DARK_BG_TERTIARY};
            }}
        """)
    
    def update_value(self, value: str):
        self.value_label.setText(value)


class DragDropArea(QFrame):
    """Drag and drop area for adding folders with dark theme."""
    
    folders_dropped = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon = QLabel("📂")
        icon.setFont(QFont("SF Pro Display", 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        
        text = QLabel("Drag & Drop Folders Here")
        text.setFont(QFont("SF Pro Text", 15, QFont.Weight.DemiBold))
        text.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text)
        
        subtext = QLabel("or click the button below to browse")
        subtext.setFont(QFont("SF Pro Text", 12))
        subtext.setStyleSheet(f"color: {DARK_TEXT_MUTED}; background: transparent;")
        subtext.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtext)
        
        self.setMinimumHeight(180)
        self._update_style(False)
    
    def _update_style(self, active: bool):
        if active:
            self.setStyleSheet(f"""
                QFrame#dropArea {{
                    background-color: rgba(59, 130, 246, 0.15);
                    border: 3px dashed {ACCENT_BLUE};
                    border-radius: 16px;
                }}
                QFrame#dropArea QLabel {{
                    color: {ACCENT_BLUE};
                    background: transparent;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#dropArea {{
                    background-color: {DARK_BG_SECONDARY};
                    border: 3px dashed {DARK_BORDER_LIGHT};
                    border-radius: 16px;
                }}
                QFrame#dropArea:hover {{
                    border-color: {ACCENT_BLUE};
                    background-color: {DARK_BG_TERTIARY};
                }}
                QFrame#dropArea QLabel {{
                    color: {DARK_TEXT_SECONDARY};
                    background: transparent;
                }}
            """)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._update_style(True)
    
    def dragLeaveEvent(self, event):
        self._update_style(False)
    
    def dropEvent(self, event: QDropEvent):
        self._update_style(False)
        folders = []
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_dir():
                folders.append(path)
        if folders:
            self.folders_dropped.emit(folders)


class QuickActionButton(QPushButton):
    """Styled quick action button with dark theme."""
    
    def __init__(self, text: str, icon: str, color: str):
        super().__init__(f"{icon}  {text}")
        self.setMinimumHeight(50)
        self.setFont(QFont("SF Pro Text", 13, QFont.Weight.DemiBold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 12px 20px;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color, 0.2)};
            }}
            QPushButton:disabled {{
                background-color: {DARK_BG_TERTIARY};
                color: {DARK_TEXT_DISABLED};
            }}
        """)
    
    def _darken_color(self, hex_color: str, factor: float = 0.1) -> str:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f"#{r:02x}{g:02x}{b:02x}"


class MainWindow(QMainWindow):
    """Main application window with modern UI."""
    
    def __init__(self):
        super().__init__()
        self.scan_result: Optional[ComparisonResult] = None
        self.analysis_results: Optional[dict] = None
        self.selected_folders: List[Path] = []
        self.scan_history: List[dict] = []
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowTitle("Image Organizer")
        self.setGeometry(100, 100, 1500, 950)
        self._apply_style()
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top Navigation Bar
        nav_bar = self._create_nav_bar()
        main_layout.addWidget(nav_bar)
        
        # Main Content Area
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sidebar Navigation
        sidebar = self._create_sidebar()
        content_layout.addWidget(sidebar)
        
        # Stacked Widget for different views
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_dashboard_view())
        self.stack.addWidget(self._create_scan_view())
        self.stack.addWidget(self._create_results_view())
        self.stack.addWidget(self._create_settings_view())
        content_layout.addWidget(self.stack, 1)
        
        main_layout.addWidget(content, 1)
        
        # Status Bar
        status_bar = self._create_status_bar()
        main_layout.addWidget(status_bar)
    
    def _create_nav_bar(self) -> QWidget:
        """Create top navigation bar with dark theme."""
        nav = QFrame()
        nav.setObjectName("navBar")
        nav.setFixedHeight(64)
        nav.setStyleSheet(f"""
            QFrame#navBar {{
                background-color: {DARK_BG_SECONDARY};
                border-bottom: 1px solid {DARK_BORDER};
            }}
        """)
        
        layout = QHBoxLayout(nav)
        layout.setContentsMargins(24, 0, 24, 0)
        
        # App Logo/Title
        logo_layout = QHBoxLayout()
        logo_icon = QLabel("🖼️")
        logo_icon.setFont(QFont("SF Pro Display", 26))
        logo_layout.addWidget(logo_icon)
        
        title = QLabel("Image Organizer")
        title.setFont(QFont("SF Pro Display", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {DARK_TEXT_PRIMARY};")
        logo_layout.addWidget(title)
        logo_layout.addSpacing(10)
        
        version = QLabel("v2.0")
        version.setFont(QFont("SF Pro Text", 11))
        version.setStyleSheet(f"color: {DARK_TEXT_MUTED}; padding-top: 4px;")
        logo_layout.addWidget(version)
        
        layout.addLayout(logo_layout)
        layout.addStretch()
        
        # Quick Actions in Nav
        self.quick_scan_btn = QPushButton("⚡ Quick Scan")
        self.quick_scan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_BLUE};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {ACCENT_BLUE_HOVER}; }}
        """)
        self.quick_scan_btn.clicked.connect(self._quick_scan)
        layout.addWidget(self.quick_scan_btn)
        
        # Help button
        help_btn = QPushButton("❓")
        help_btn.setFixedSize(40, 40)
        help_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_BG_TERTIARY};
                border: 1px solid {DARK_BORDER};
                border-radius: 20px;
                font-size: 16px;
            }}
            QPushButton:hover {{ background-color: {DARK_BG_HOVER}; }}
        """)
        help_btn.clicked.connect(self._show_help)
        layout.addWidget(help_btn)
        
        return nav
    
    def _create_sidebar(self) -> QWidget:
        """Create left sidebar navigation with dark theme."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background-color: {DARK_BG_SECONDARY};
                border-right: 1px solid {DARK_BORDER};
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 24, 14, 24)
        layout.setSpacing(6)
        
        # Navigation Items
        nav_items = [
            ("📊", "Dashboard", 0),
            ("🔍", "Scan Files", 1),
            ("📋", "Results", 2),
            ("⚙️", "Settings", 3),
        ]
        
        self.nav_buttons = []
        for icon, text, index in nav_items:
            btn = QPushButton(f"  {icon}  {text}")
            btn.setCheckable(True)
            btn.setFont(QFont("SF Pro Text", 14))
            btn.setMinimumHeight(48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {DARK_TEXT_SECONDARY};
                    border: none;
                    border-radius: 10px;
                    text-align: left;
                    padding-left: 14px;
                }}
                QPushButton:hover {{
                    background-color: {DARK_BG_HOVER};
                    color: {DARK_TEXT_PRIMARY};
                }}
                QPushButton:checked {{
                    background-color: {ACCENT_BLUE};
                    color: #FFFFFF;
                }}
            """)
            btn.clicked.connect(lambda checked, i=index: self._switch_view(i))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)
        
        self.nav_buttons[0].setChecked(True)
        
        layout.addStretch()
        
        # Storage Info
        storage_frame = QFrame()
        storage_frame.setObjectName("storageFrame")
        storage_frame.setStyleSheet(f"""
            QFrame#storageFrame {{
                background-color: {DARK_BG_TERTIARY};
                border-radius: 12px;
                border: 1px solid {DARK_BORDER};
            }}
        """)
        storage_layout = QVBoxLayout(storage_frame)
        storage_layout.setContentsMargins(16, 16, 16, 16)
        
        storage_title = QLabel("💾 Space Saved")
        storage_title.setFont(QFont("SF Pro Text", 12, QFont.Weight.DemiBold))
        storage_title.setStyleSheet(f"color: {DARK_TEXT_SECONDARY}; background: transparent;")
        storage_layout.addWidget(storage_title)
        
        self.space_saved_label = QLabel("0 MB")
        self.space_saved_label.setFont(QFont("SF Pro Display", 24, QFont.Weight.Bold))
        self.space_saved_label.setStyleSheet(f"color: {ACCENT_GREEN}; background: transparent;")
        storage_layout.addWidget(self.space_saved_label)
        
        layout.addWidget(storage_frame)
        
        return sidebar
    
    def _create_dashboard_view(self) -> QWidget:
        """Create dashboard view with statistics and quick actions - dark theme."""
        view = QScrollArea()
        view.setWidgetResizable(True)
        view.setStyleSheet(f"QScrollArea {{ border: none; background-color: {DARK_BG_PRIMARY}; }}")
        
        content = QWidget()
        content.setStyleSheet(f"background-color: {DARK_BG_PRIMARY};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(28)
        
        # Welcome Section
        welcome = QLabel("👋 Welcome to Image Organizer")
        welcome.setFont(QFont("SF Pro Display", 30, QFont.Weight.Bold))
        welcome.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(welcome)
        
        subtitle = QLabel("Organize your files intelligently with AI-powered duplicate detection")
        subtitle.setFont(QFont("SF Pro Text", 15))
        subtitle.setStyleSheet(f"color: {DARK_TEXT_SECONDARY}; background: transparent;")
        layout.addWidget(subtitle)
        
        # Stats Cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        self.stat_files_scanned = StatCard("Files Scanned", "0", "📁", ACCENT_BLUE)
        self.stat_duplicates_found = StatCard("Duplicates Found", "0", "🔍", ACCENT_ORANGE)
        self.stat_space_recoverable = StatCard("Space Recoverable", "0 MB", "💾", ACCENT_GREEN)
        self.stat_scans_completed = StatCard("Scans Completed", "0", "✅", ACCENT_PURPLE)
        
        stats_layout.addWidget(self.stat_files_scanned)
        stats_layout.addWidget(self.stat_duplicates_found)
        stats_layout.addWidget(self.stat_space_recoverable)
        stats_layout.addWidget(self.stat_scans_completed)
        
        layout.addLayout(stats_layout)
        
        # Quick Actions Section
        actions_label = QLabel("⚡ Quick Actions")
        actions_label.setFont(QFont("SF Pro Display", 20, QFont.Weight.DemiBold))
        actions_label.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; margin-top: 20px; background: transparent;")
        layout.addWidget(actions_label)
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(20)
        
        scan_action = QuickActionButton("Start New Scan", "🔍", ACCENT_BLUE)
        scan_action.clicked.connect(lambda: self._switch_view(1))
        actions_layout.addWidget(scan_action)
        
        analyze_action = QuickActionButton("View Results", "📊", ACCENT_PURPLE)
        analyze_action.clicked.connect(lambda: self._switch_view(2))
        actions_layout.addWidget(analyze_action)
        
        cleanup_action = QuickActionButton("Quick Cleanup", "🧹", ACCENT_GREEN)
        cleanup_action.clicked.connect(self._quick_cleanup)
        actions_layout.addWidget(cleanup_action)
        
        layout.addLayout(actions_layout)
        
        # Recent Activity
        activity_label = QLabel("📜 Recent Activity")
        activity_label.setFont(QFont("SF Pro Display", 20, QFont.Weight.DemiBold))
        activity_label.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; margin-top: 20px; background: transparent;")
        layout.addWidget(activity_label)
        
        self.activity_list = QListWidget()
        self.activity_list.setMinimumHeight(220)
        self.activity_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {DARK_BG_SECONDARY};
                border: 1px solid {DARK_BORDER};
                border-radius: 12px;
                padding: 10px;
                color: {DARK_TEXT_PRIMARY};
            }}
            QListWidget::item {{
                padding: 14px;
                border-radius: 8px;
                color: {DARK_TEXT_PRIMARY};
                background: transparent;
            }}
            QListWidget::item:hover {{
                background-color: {DARK_BG_HOVER};
            }}
            QListWidget::item:selected {{
                background-color: {ACCENT_BLUE};
                color: #FFFFFF;
            }}
        """)
        self.activity_list.addItem("🚀 Welcome! Add folders to start organizing your images.")
        layout.addWidget(self.activity_list)
        
        layout.addStretch()
        view.setWidget(content)
        return view
    
    def _create_scan_view(self) -> QWidget:
        """Create scan configuration view with dark theme."""
        view = QScrollArea()
        view.setWidgetResizable(True)
        view.setStyleSheet(f"QScrollArea {{ border: none; background-color: {DARK_BG_PRIMARY}; }}")
        
        content = QWidget()
        content.setStyleSheet(f"background-color: {DARK_BG_PRIMARY};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(24)
        
        # Header
        header = QLabel("🔍 Scan for Duplicates")
        header.setFont(QFont("SF Pro Display", 26, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(header)
        
        # Drag & Drop Area
        self.drop_area = DragDropArea()
        self.drop_area.folders_dropped.connect(self._add_folders)
        layout.addWidget(self.drop_area)
        
        # Folder List & Controls
        folder_section = QFrame()
        folder_section.setObjectName("folderSection")
        folder_section.setStyleSheet(f"""
            QFrame#folderSection {{
                background-color: {DARK_BG_SECONDARY};
                border-radius: 12px;
                border: 1px solid {DARK_BORDER};
            }}
        """)
        folder_layout = QVBoxLayout(folder_section)
        folder_layout.setContentsMargins(20, 20, 20, 20)
        
        folder_header = QHBoxLayout()
        folder_title = QLabel("📁 Selected Folders")
        folder_title.setFont(QFont("SF Pro Text", 15, QFont.Weight.DemiBold))
        folder_title.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
        folder_header.addWidget(folder_title)
        folder_header.addStretch()
        
        add_btn = QPushButton("+ Add Folder")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_BLUE};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {ACCENT_BLUE_HOVER}; }}
        """)
        add_btn.clicked.connect(self._add_folder)
        folder_header.addWidget(add_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_RED};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
            }}
            QPushButton:hover {{ background-color: {ACCENT_RED_HOVER}; }}
        """)
        clear_btn.clicked.connect(self._clear_folders)
        folder_header.addWidget(clear_btn)
        
        folder_layout.addLayout(folder_header)
        
        self.folder_list_widget = QListWidget()
        self.folder_list_widget.setMinimumHeight(120)
        self.folder_list_widget.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {DARK_BORDER};
                border-radius: 8px;
                background-color: {DARK_BG_TERTIARY};
                color: {DARK_TEXT_PRIMARY};
            }}
            QListWidget::item {{
                padding: 12px;
                color: {DARK_TEXT_PRIMARY};
            }}
            QListWidget::item:selected {{
                background-color: {ACCENT_BLUE};
                color: #FFFFFF;
            }}
        """)
        folder_layout.addWidget(self.folder_list_widget)
        layout.addWidget(folder_section)
        
        # Scan Options
        options_section = QFrame()
        options_section.setObjectName("optionsSection")
        options_section.setStyleSheet(f"""
            QFrame#optionsSection {{
                background-color: {DARK_BG_SECONDARY};
                border-radius: 12px;
                border: 1px solid {DARK_BORDER};
            }}
        """)
        options_layout = QVBoxLayout(options_section)
        options_layout.setContentsMargins(24, 24, 24, 24)
        
        options_title = QLabel("⚙️ Scan Options")
        options_title.setFont(QFont("SF Pro Text", 15, QFont.Weight.DemiBold))
        options_title.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; margin-bottom: 12px; background: transparent;")
        options_layout.addWidget(options_title)
        
        options_grid = QGridLayout()
        options_grid.setSpacing(20)
        
        # File Type
        file_type_label = QLabel("File Type:")
        file_type_label.setStyleSheet(f"color: {DARK_TEXT_SECONDARY}; background: transparent;")
        options_grid.addWidget(file_type_label, 0, 0)
        self.file_type = QComboBox()
        self.file_type.addItems(["All Files", "Images Only", "Documents", "Videos", "Audio"])
        self.file_type.setCurrentIndex(1)  # Default to images
        self.file_type.setMinimumWidth(200)
        options_grid.addWidget(self.file_type, 0, 1)
        
        # Detection Mode
        detection_label = QLabel("Detection Mode:")
        detection_label.setStyleSheet(f"color: {DARK_TEXT_SECONDARY}; background: transparent;")
        options_grid.addWidget(detection_label, 0, 2)
        self.detection_mode = QComboBox()
        self.detection_mode.addItems(["Exact Match", "Similar Files", "Both"])
        self.detection_mode.setCurrentIndex(2)
        self.detection_mode.setMinimumWidth(200)
        options_grid.addWidget(self.detection_mode, 0, 3)
        
        # Keep Strategy
        keep_label = QLabel("Keep Strategy:")
        keep_label.setStyleSheet(f"color: {DARK_TEXT_SECONDARY}; background: transparent;")
        options_grid.addWidget(keep_label, 1, 0)
        self.keep_strategy = QComboBox()
        self.keep_strategy.addItems(["Newest File", "Oldest File", "Largest File", "Smallest File", "Best Quality"])
        self.keep_strategy.setMinimumWidth(200)
        options_grid.addWidget(self.keep_strategy, 1, 1)
        
        # Similarity Threshold
        similarity_label = QLabel("Similarity:")
        similarity_label.setStyleSheet(f"color: {DARK_TEXT_SECONDARY}; background: transparent;")
        options_grid.addWidget(similarity_label, 1, 2)
        similarity_widget = QWidget()
        similarity_widget.setStyleSheet("background: transparent;")
        sim_layout = QHBoxLayout(similarity_widget)
        sim_layout.setContentsMargins(0, 0, 0, 0)
        self.similarity = QSlider(Qt.Orientation.Horizontal)
        self.similarity.setRange(70, 100)
        self.similarity.setValue(90)
        self.similarity_label = QLabel("90%")
        self.similarity_label.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; font-weight: bold; background: transparent;")
        self.similarity.valueChanged.connect(lambda v: self.similarity_label.setText(f"{v}%"))
        sim_layout.addWidget(self.similarity)
        sim_layout.addWidget(self.similarity_label)
        options_grid.addWidget(similarity_widget, 1, 3)
        
        options_layout.addLayout(options_grid)
        
        # Advanced Options
        self.include_perceptual = QCheckBox("🔬 Use perceptual hashing for image comparison")
        self.include_perceptual.setChecked(True)
        self.include_perceptual.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
        options_layout.addWidget(self.include_perceptual)
        
        self.include_subdirs = QCheckBox("📂 Include subdirectories")
        self.include_subdirs.setChecked(True)
        self.include_subdirs.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
        options_layout.addWidget(self.include_subdirs)
        
        layout.addWidget(options_section)
        
        # Progress Section
        progress_section = QFrame()
        progress_section.setObjectName("progressSection")
        progress_section.setStyleSheet(f"""
            QFrame#progressSection {{
                background-color: {DARK_BG_SECONDARY};
                border-radius: 12px;
                border: 1px solid {DARK_BORDER};
            }}
        """)
        progress_layout = QVBoxLayout(progress_section)
        progress_layout.setContentsMargins(24, 20, 24, 20)
        
        self.progress_label = QLabel("Ready to scan")
        self.progress_label.setFont(QFont("SF Pro Text", 14))
        self.progress_label.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 5px;
                background-color: {DARK_BG_TERTIARY};
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT_BLUE};
                border-radius: 5px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_section)
        
        # Action Buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(20)
        
        self.scan_btn = QuickActionButton("Start Scan", "🔍", ACCENT_BLUE)
        self.scan_btn.clicked.connect(self._start_scan)
        self.scan_btn.setEnabled(False)
        actions_layout.addWidget(self.scan_btn)
        
        self.analyze_btn = QuickActionButton("AI Analyze", "🤖", ACCENT_PURPLE)
        self.analyze_btn.clicked.connect(self._start_analysis)
        self.analyze_btn.setEnabled(False)
        actions_layout.addWidget(self.analyze_btn)
        
        layout.addLayout(actions_layout)
        
        layout.addStretch()
        view.setWidget(content)
        return view
    
    def _create_results_view(self) -> QWidget:
        """Create results view with table and preview - dark theme."""
        view = QWidget()
        view.setStyleSheet(f"background-color: {DARK_BG_PRIMARY};")
        layout = QVBoxLayout(view)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(24)
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("📋 Scan Results")
        header.setFont(QFont("SF Pro Display", 26, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        # Export button
        export_btn = QPushButton("📤 Export Report")
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {ACCENT_BLUE};
                border: 1px solid {ACCENT_BLUE};
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: rgba(59, 130, 246, 0.15);
            }}
        """)
        export_btn.clicked.connect(self._export_report)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Summary Bar
        self.summary_frame = QFrame()
        self.summary_frame.setObjectName("summaryFrame")
        self.summary_frame.setStyleSheet(f"""
            QFrame#summaryFrame {{
                background-color: {DARK_BG_SECONDARY};
                border-radius: 12px;
                border: 1px solid {DARK_BORDER};
            }}
        """)
        summary_layout = QHBoxLayout(self.summary_frame)
        summary_layout.setContentsMargins(24, 18, 24, 18)
        
        self.summary_label = QLabel("📈 No scan performed yet. Go to 'Scan Files' to start.")
        self.summary_label.setFont(QFont("SF Pro Text", 14))
        self.summary_label.setStyleSheet(f"color: {DARK_TEXT_SECONDARY}; background: transparent;")
        summary_layout.addWidget(self.summary_label)
        
        layout.addWidget(self.summary_frame)
        
        # Results Table
        table_frame = QFrame()
        table_frame.setObjectName("tableFrame")
        table_frame.setStyleSheet(f"""
            QFrame#tableFrame {{
                background-color: {DARK_BG_SECONDARY};
                border-radius: 12px;
                border: 1px solid {DARK_BORDER};
            }}
        """)
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(2, 2, 2, 2)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "✓", "Group", "Keep File", "Remove", "Space Saved", "Reason", "Confidence"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(0, 44)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setStyleSheet(f"""
            QTableWidget {{
                border: none;
                border-radius: 12px;
                gridline-color: {DARK_BORDER};
                background-color: {DARK_BG_SECONDARY};
                color: {DARK_TEXT_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 12px;
                color: {DARK_TEXT_PRIMARY};
                background-color: {DARK_BG_SECONDARY};
                border-bottom: 1px solid {DARK_BORDER};
            }}
            QTableWidget::item:alternate {{
                background-color: {DARK_BG_TERTIARY};
            }}
            QTableWidget::item:selected {{
                background-color: {ACCENT_BLUE};
                color: #FFFFFF;
            }}
            QHeaderView::section {{
                background-color: {DARK_BG_TERTIARY};
                color: {DARK_TEXT_PRIMARY};
                padding: 14px;
                border: none;
                border-bottom: 2px solid {ACCENT_BLUE};
                font-weight: bold;
                font-size: 13px;
            }}
            QHeaderView::section:first {{
                border-top-left-radius: 12px;
            }}
            QHeaderView::section:last {{
                border-top-right-radius: 12px;
            }}
        """)
        table_layout.addWidget(self.results_table)
        
        layout.addWidget(table_frame, 1)
        
        # Action Buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(16)
        
        select_all_btn = QPushButton("☑️ Select All")
        select_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_BG_SECONDARY};
                color: {DARK_TEXT_PRIMARY};
                border: 1px solid {DARK_BORDER};
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 500;
            }}
            QPushButton:hover {{ 
                background-color: {DARK_BG_HOVER};
                border-color: {DARK_BORDER_LIGHT};
            }}
        """)
        select_all_btn.clicked.connect(self._select_all_results)
        actions_layout.addWidget(select_all_btn)
        
        deselect_btn = QPushButton("☐ Deselect All")
        deselect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_BG_SECONDARY};
                color: {DARK_TEXT_PRIMARY};
                border: 1px solid {DARK_BORDER};
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 500;
            }}
            QPushButton:hover {{ 
                background-color: {DARK_BG_HOVER};
                border-color: {DARK_BORDER_LIGHT};
            }}
        """)
        deselect_btn.clicked.connect(self._deselect_all_results)
        actions_layout.addWidget(deselect_btn)
        
        actions_layout.addStretch()
        
        self.execute_btn = QuickActionButton("Execute Cleanup", "🧹", ACCENT_GREEN)
        self.execute_btn.clicked.connect(self._execute_plan)
        self.execute_btn.setEnabled(False)
        actions_layout.addWidget(self.execute_btn)
        
        layout.addLayout(actions_layout)
        
        return view
    
    def _create_settings_view(self) -> QWidget:
        """Create settings view with dark theme."""
        view = QScrollArea()
        view.setWidgetResizable(True)
        view.setStyleSheet(f"QScrollArea {{ border: none; background-color: {DARK_BG_PRIMARY}; }}")
        
        content = QWidget()
        content.setStyleSheet(f"background-color: {DARK_BG_PRIMARY};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(24)
        
        # Header
        header = QLabel("⚙️ Settings")
        header.setFont(QFont("SF Pro Display", 26, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(header)
        
        # General Settings
        general_section = self._create_settings_section("🔧 General", [
            ("Backup Location", "~/.image_organizer_backup"),
            ("Auto-backup before cleanup", True),
            ("Show notifications", True),
        ])
        layout.addWidget(general_section)
        
        # Performance Settings
        perf_section = self._create_settings_section("⚡ Performance", [
            ("Max concurrent files", "500"),
            ("Enable GPU acceleration", False),
            ("Cache scan results", True),
        ])
        layout.addWidget(perf_section)
        
        # AI Settings
        ai_section = self._create_settings_section("🤖 AI Analysis", [
            ("Confidence threshold", "medium"),
            ("Auto-suggest cleanup", True),
            ("Learn from decisions", True),
        ])
        layout.addWidget(ai_section)
        
        layout.addStretch()
        view.setWidget(content)
        return view
    
    def _create_settings_section(self, title: str, settings: list) -> QFrame:
        """Create a settings section with dark theme."""
        section = QFrame()
        # Use unique object name based on title
        obj_name = title.replace(" ", "").replace("🔧", "").replace("⚡", "").replace("🤖", "")
        section.setObjectName(f"settingsSection{obj_name}")
        section.setStyleSheet(f"""
            QFrame#settingsSection{obj_name} {{
                background-color: {DARK_BG_SECONDARY};
                border-radius: 12px;
                border: 1px solid {DARK_BORDER};
            }}
        """)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(24, 20, 24, 20)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("SF Pro Text", 15, QFont.Weight.DemiBold))
        title_label.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(title_label)
        
        for setting_name, default_value in settings:
            row = QHBoxLayout()
            label = QLabel(setting_name)
            label.setFont(QFont("SF Pro Text", 14))
            label.setStyleSheet(f"color: {DARK_TEXT_SECONDARY}; background: transparent;")
            row.addWidget(label)
            row.addStretch()
            
            if isinstance(default_value, bool):
                toggle = QCheckBox()
                toggle.setChecked(default_value)
                toggle.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; background: transparent;")
                row.addWidget(toggle)
            else:
                input_field = QComboBox() if default_value in ["medium", "high", "low"] else QLabel(str(default_value))
                if isinstance(input_field, QComboBox):
                    input_field.addItems(["low", "medium", "high"])
                    input_field.setCurrentText(default_value)
                else:
                    input_field.setStyleSheet(f"color: {DARK_TEXT_MUTED}; background: transparent;")
                row.addWidget(input_field)
            
            layout.addLayout(row)
        
        return section
    
    def _create_status_bar(self) -> QWidget:
        """Create bottom status bar with dark theme."""
        status = QFrame()
        status.setObjectName("statusBar")
        status.setFixedHeight(36)
        status.setStyleSheet(f"""
            QFrame#statusBar {{
                background-color: {DARK_BG_SECONDARY};
                border-top: 1px solid {DARK_BORDER};
            }}
        """)
        
        layout = QHBoxLayout(status)
        layout.setContentsMargins(24, 0, 24, 0)
        
        self.status_text = QLabel("✅ Ready")
        self.status_text.setFont(QFont("SF Pro Text", 12))
        self.status_text.setStyleSheet(f"color: {DARK_TEXT_SECONDARY};")
        layout.addWidget(self.status_text)
        
        layout.addStretch()
        
        time_label = QLabel(datetime.now().strftime("%H:%M"))
        time_label.setFont(QFont("SF Mono", 12))
        time_label.setStyleSheet(f"color: {DARK_TEXT_MUTED};")
        layout.addWidget(time_label)
        
        # Update time every minute
        timer = QTimer(self)
        timer.timeout.connect(lambda: time_label.setText(datetime.now().strftime("%H:%M")))
        timer.start(60000)
        
        return status
    
    def _apply_style(self):
        """Apply modern dark theme styling."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {DARK_BG_PRIMARY};
            }}
            QLabel {{
                color: {DARK_TEXT_PRIMARY};
                background: transparent;
            }}
            QComboBox {{
                padding: 10px 14px;
                border: 1px solid {DARK_BORDER};
                border-radius: 8px;
                background-color: {DARK_BG_TERTIARY};
                color: {DARK_TEXT_PRIMARY};
                min-width: 140px;
                selection-background-color: {ACCENT_BLUE};
            }}
            QComboBox:hover {{
                border-color: {DARK_BORDER_LIGHT};
                background-color: {DARK_BG_HOVER};
            }}
            QComboBox:focus {{
                border-color: {ACCENT_BLUE};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {DARK_TEXT_SECONDARY};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DARK_BG_TERTIARY};
                color: {DARK_TEXT_PRIMARY};
                selection-background-color: {ACCENT_BLUE};
                selection-color: #FFFFFF;
                border-radius: 8px;
                border: 1px solid {DARK_BORDER};
                padding: 4px;
            }}
            QCheckBox {{
                color: {DARK_TEXT_PRIMARY};
                spacing: 10px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 6px;
                border: 2px solid {DARK_BORDER_LIGHT};
                background-color: {DARK_BG_TERTIARY};
            }}
            QCheckBox::indicator:hover {{
                border-color: {ACCENT_BLUE};
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT_BLUE};
                border-color: {ACCENT_BLUE};
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
            QSlider::handle:horizontal:hover {{
                background: {ACCENT_BLUE_HOVER};
            }}
            QSlider::sub-page:horizontal {{
                background: {ACCENT_BLUE};
                border-radius: 4px;
            }}
            QListWidget {{
                border: 1px solid {DARK_BORDER};
                border-radius: 10px;
                background-color: {DARK_BG_SECONDARY};
            }}
            QListWidget::item {{
                padding: 10px;
                color: {DARK_TEXT_PRIMARY};
            }}
            QListWidget::item:selected {{
                background-color: {ACCENT_BLUE};
                color: #FFFFFF;
                border-radius: 6px;
            }}
            QListWidget::item:hover:!selected {{
                background-color: {DARK_BG_HOVER};
            }}
            QScrollBar:vertical {{
                background: {DARK_BG_PRIMARY};
                width: 10px;
                margin: 0;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {DARK_BORDER_LIGHT};
                border-radius: 5px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {DARK_TEXT_MUTED};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                background: {DARK_BG_PRIMARY};
                height: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background: {DARK_BORDER_LIGHT};
                border-radius: 5px;
                min-width: 40px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {DARK_TEXT_MUTED};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
            QToolTip {{
                background-color: {DARK_BG_TERTIARY};
                color: {DARK_TEXT_PRIMARY};
                border: 1px solid {DARK_BORDER};
                border-radius: 6px;
                padding: 6px 10px;
            }}
            QMessageBox {{
                background-color: {DARK_BG_SECONDARY};
            }}
            QMessageBox QLabel {{
                color: {DARK_TEXT_PRIMARY};
            }}
        """)
    
    def _switch_view(self, index: int):
        """Switch to a different view."""
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.stack.setCurrentIndex(index)
    
    def _log(self, message: str):
        """Add message to activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_list.insertItem(0, f"[{timestamp}] {message}")
        self.status_text.setText(message)
        
        # Keep only last 50 items
        while self.activity_list.count() > 50:
            self.activity_list.takeItem(self.activity_list.count() - 1)
    
    def _add_folder(self):
        """Add a single folder via dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if folder:
            self._add_folders([Path(folder)])
    
    def _add_folders(self, folders: List[Path]):
        """Add multiple folders."""
        for path in folders:
            if path not in self.selected_folders:
                self.selected_folders.append(path)
                item = QListWidgetItem(f"📁 {path}")
                self.folder_list_widget.addItem(item)
                self._log(f"Added folder: {path.name}")
        
        self.scan_btn.setEnabled(len(self.selected_folders) > 0)
    
    def _clear_folders(self):
        """Clear all selected folders."""
        self.selected_folders.clear()
        self.folder_list_widget.clear()
        self.scan_btn.setEnabled(False)
        self._log("Cleared all folders")
    
    def _quick_scan(self):
        """Perform a quick scan of common locations."""
        # Switch to scan view
        self._switch_view(1)
        
        # Add common image locations
        home = Path.home()
        common_paths = [
            home / "Pictures",
            home / "Downloads",
            home / "Desktop",
        ]
        
        folders_to_add = [p for p in common_paths if p.exists()]
        if folders_to_add:
            self._add_folders(folders_to_add)
            self._log("Quick scan: Added common image folders")
    
    def _quick_cleanup(self):
        """Quick cleanup based on last analysis."""
        if self.analysis_results:
            self._switch_view(2)
            self._execute_plan()
        else:
            QMessageBox.information(
                self,
                "No Results",
                "Please run a scan and AI analysis first before cleanup."
            )
    
    def _show_help(self):
        """Show help dialog."""
        QMessageBox.information(
            self,
            "Help - Image Organizer",
            "🖼️ <b>Image Organizer v2.0</b><br><br>"
            "<b>How to use:</b><br>"
            "1. Add folders to scan (drag & drop or browse)<br>"
            "2. Configure scan options<br>"
            "3. Click 'Start Scan' to find duplicates<br>"
            "4. Use 'AI Analyze' for smart recommendations<br>"
            "5. Review and execute cleanup<br><br>"
            "<b>Features:</b><br>"
            "• Exact duplicate detection<br>"
            "• Perceptual image matching<br>"
            "• AI-powered cleanup suggestions<br>"
            "• Safe backup before deletion<br><br>"
            "Files are backed up to ~/.image_organizer_backup"
        )
    
    def _export_report(self):
        """Export scan results to a file."""
        if not self.analysis_results:
            QMessageBox.warning(self, "No Data", "No scan results to export.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Report", "scan_report.json", "JSON Files (*.json)"
        )
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(self.analysis_results, f, indent=2, default=str)
            self._log(f"Report exported to {file_path}")
            QMessageBox.information(self, "Export Complete", f"Report saved to:\n{file_path}")
    
    def _select_all_results(self):
        """Select all rows in results table."""
        for row in range(self.results_table.rowCount()):
            checkbox_item = self.results_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Checked)
    
    def _deselect_all_results(self):
        """Deselect all rows in results table."""
        for row in range(self.results_table.rowCount()):
            checkbox_item = self.results_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Unchecked)
    
    def _get_file_type_value(self) -> str:
        """Convert UI file type to scanner value."""
        mapping = {
            "All Files": "all",
            "Images Only": "images",
            "Documents": "documents",
            "Videos": "videos",
            "Audio": "audio"
        }
        return mapping.get(self.file_type.currentText(), "all")
    
    def _get_keep_strategy_value(self) -> str:
        """Convert UI keep strategy to scanner value."""
        mapping = {
            "Newest File": "newest",
            "Oldest File": "oldest",
            "Largest File": "largest",
            "Smallest File": "smallest",
            "Best Quality": "highest_quality"
        }
        return mapping.get(self.keep_strategy.currentText(), "newest")
    
    def _start_scan(self):
        if not self.selected_folders:
            return
        
        self._log("🚀 Starting scan...")
        self.scan_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results_table.setRowCount(0)
        
        # Determine if perceptual hashing should be used
        include_perceptual = (
            self.include_perceptual.isChecked() and 
            (self.detection_mode.currentIndex() >= 1)  # Similar or Both
        )
        
        self.scan_thread = ScanThread(
            folders=self.selected_folders,
            file_type=self._get_file_type_value(),
            similarity=self.similarity.value(),
            include_perceptual=include_perceptual,
        )
        self.scan_thread.progress.connect(self._on_scan_progress)
        self.scan_thread.finished.connect(self._on_scan_complete)
        self.scan_thread.error.connect(self._on_scan_error)
        self.scan_thread.start()
    
    def _on_scan_progress(self, current: int, total: int, message: str):
        self.progress_label.setText(message)
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
    
    def _on_scan_complete(self, result: ComparisonResult):
        self.scan_result = result
        self.scan_btn.setEnabled(True)
        
        total_groups = len(result.exact_groups) + len(result.perceptual_groups)
        total_files = sum(len(g.members) for g in result.exact_groups + result.perceptual_groups)
        
        # Update dashboard stats
        self.stat_files_scanned.update_value(f"{total_files:,}")
        self.stat_duplicates_found.update_value(str(total_groups))
        self.stat_space_recoverable.update_value(format_size(result.total_wasted_bytes))
        
        if total_groups == 0:
            self._log("✅ No duplicates found!")
            self.summary_label.setText("📈 No duplicates found - your files are unique!")
            QMessageBox.information(self, "Scan Complete", "No duplicate files found!")
            return
        
        self._log(f"✅ Found {total_groups} duplicate groups")
        self._log(f"💾 Potential savings: {format_size(result.total_wasted_bytes)}")
        
        self.summary_label.setText(
            f"📈 Found <b>{len(result.exact_groups)}</b> exact + <b>{len(result.perceptual_groups)}</b> similar groups | "
            f"Space recoverable: <b>{format_size(result.total_wasted_bytes)}</b>"
        )
        
        self.analyze_btn.setEnabled(True)
        
        # Switch to results view and populate
        self._switch_view(2)
        self._populate_scan_results(result)
    
    def _on_scan_error(self, error: str):
        self._log(f"❌ Error: {error}")
        self.scan_btn.setEnabled(True)
        QMessageBox.critical(self, "Scan Error", f"An error occurred:\n{error}")
    
    def _populate_scan_results(self, result: ComparisonResult):
        """Populate table with scan results (before AI analysis)."""
        all_groups = result.exact_groups + result.perceptual_groups
        self.results_table.setRowCount(len(all_groups))
        
        for idx, group in enumerate(all_groups):
            # Checkbox
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox.setCheckState(Qt.CheckState.Checked)
            self.results_table.setItem(idx, 0, checkbox)
            
            self.results_table.setItem(idx, 1, QTableWidgetItem(str(group.group_id)))
            self.results_table.setItem(idx, 2, QTableWidgetItem(group.members[0].path.name if group.members else ""))
            self.results_table.setItem(idx, 3, QTableWidgetItem(f"{group.count - 1} files"))
            self.results_table.setItem(idx, 4, QTableWidgetItem(format_size(group.wasted_size)))
            self.results_table.setItem(idx, 5, QTableWidgetItem(group.duplicate_type.value))
            
            pending_item = QTableWidgetItem("⏳ pending")
            pending_item.setForeground(QColor("#8e8e93"))
            self.results_table.setItem(idx, 6, pending_item)
    
    def _start_analysis(self):
        if not self.scan_result:
            return
        
        self._log("🤖 Starting AI analysis...")
        self.analyze_btn.setEnabled(False)
        
        # Convert scan results to format expected by agent
        all_groups = self.scan_result.exact_groups + self.scan_result.perceptual_groups
        groups_data = [
            {"files": [str(m.path) for m in g.members]}
            for g in all_groups
        ]
        
        preferences = {
            "keep_strategy": self._get_keep_strategy_value(),
            "similarity_threshold": self.similarity.value(),
            "preserve_folders": [],
        }
        
        self.analysis_thread = AnalysisThread(groups_data, preferences)
        self.analysis_thread.status.connect(self._log)
        self.analysis_thread.finished.connect(self._on_analysis_complete)
        self.analysis_thread.error.connect(self._on_analysis_error)
        self.analysis_thread.start()
    
    def _on_analysis_complete(self, analysis: dict):
        self.analysis_results = analysis
        self.analyze_btn.setEnabled(True)
        
        method = analysis.get("method", "ai")
        self._log(f"✅ Analysis complete ({method})")
        self._log(f"📋 {analysis.get('summary', '')}")
        self._log(f"💾 Space to save: {analysis.get('space_to_save_mb', 0):.2f} MB")
        
        # Update space saved in sidebar
        self.space_saved_label.setText(f"{analysis.get('space_to_save_mb', 0):.1f} MB")
        
        self.summary_label.setText(
            f"📈 {analysis.get('summary', '')} | "
            f"Save: <b>{analysis.get('space_to_save_mb', 0):.2f} MB</b>"
        )
        
        # Update table with AI recommendations
        recommendations = analysis.get("recommendations", [])
        self.results_table.setRowCount(len(recommendations))
        
        for idx, rec in enumerate(recommendations):
            keep_file = Path(rec.get("keep_file", ""))
            remove_files = rec.get("remove_files", [])
            
            # Checkbox
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox.setCheckState(Qt.CheckState.Checked)
            self.results_table.setItem(idx, 0, checkbox)
            
            self.results_table.setItem(idx, 1, QTableWidgetItem(str(rec.get("group_id", idx))))
            self.results_table.setItem(idx, 2, QTableWidgetItem(keep_file.name))
            self.results_table.setItem(idx, 3, QTableWidgetItem(f"{len(remove_files)} files"))
            
            # Calculate space
            space = sum(Path(f).stat().st_size for f in remove_files if Path(f).exists())
            self.results_table.setItem(idx, 4, QTableWidgetItem(format_size(space)))
            
            reason = rec.get("reason", "")[:50]
            self.results_table.setItem(idx, 5, QTableWidgetItem(reason))
            
            confidence = rec.get("confidence", "medium")
            conf_item = QTableWidgetItem(f"{'🟢' if confidence == 'high' else '🟡' if confidence == 'medium' else '🔴'} {confidence}")
            if confidence == "high":
                conf_item.setForeground(QColor("#34C759"))
            elif confidence == "low":
                conf_item.setForeground(QColor("#FF3B30"))
            else:
                conf_item.setForeground(QColor("#FF9500"))
            self.results_table.setItem(idx, 6, conf_item)
        
        self.execute_btn.setEnabled(len(recommendations) > 0)
        
        # Increment scan counter
        current_count = int(self.stat_scans_completed.value_label.text())
        self.stat_scans_completed.update_value(str(current_count + 1))
    
    def _on_analysis_error(self, error: str):
        self._log(f"❌ Analysis error: {error}")
        self.analyze_btn.setEnabled(True)
        QMessageBox.warning(self, "Analysis Error", f"AI analysis failed:\n{error}\n\nUsing rule-based fallback.")
    
    def _execute_plan(self):
        if not self.analysis_results:
            return
        
        recommendations = self.analysis_results.get("recommendations", [])
        
        # Filter based on checked items
        selected_recommendations = []
        for i, rec in enumerate(recommendations):
            if i < self.results_table.rowCount():
                checkbox = self.results_table.item(i, 0)
                if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                    selected_recommendations.append(rec)
        
        if not selected_recommendations:
            QMessageBox.warning(self, "No Selection", "Please select at least one group to clean up.")
            return
        
        total_files = sum(len(r.get("remove_files", [])) for r in selected_recommendations)
        space_mb = sum(
            sum(Path(f).stat().st_size for f in r.get("remove_files", []) if Path(f).exists())
            for r in selected_recommendations
        ) / (1024 * 1024)
        
        reply = QMessageBox.question(
            self,
            "Confirm Cleanup",
            f"<b>This will move {total_files} files to backup.</b><br><br>"
            f"Space to be freed: <b>{space_mb:.2f} MB</b><br><br>"
            f"Files will be moved to <code>~/.image_organizer_backup</code><br>"
            f"You can restore them later if needed.<br><br>"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._log("🗑️ Executing cleanup plan...")
            
            try:
                agent = DuplicateAgent()
                result = agent.execute_recommendations(
                    selected_recommendations,
                    dry_run=False,
                )
                
                self._log(f"✅ Cleanup complete!")
                self._log(f"📁 Files moved: {result['files_removed']}")
                self._log(f"💾 Space freed: {format_size(result['space_freed'])}")
                
                # Update space saved display
                space_saved_mb = result['space_freed'] / (1024 * 1024)
                current_saved = float(self.space_saved_label.text().replace(" MB", "").replace(",", ""))
                self.space_saved_label.setText(f"{current_saved + space_saved_mb:.1f} MB")
                
                if result["errors"]:
                    self._log(f"⚠️ Errors: {len(result['errors'])}")
                
                QMessageBox.information(
                    self,
                    "Cleanup Complete",
                    f"<b>Successfully moved {result['files_removed']} files.</b><br><br>"
                    f"Space freed: <b>{format_size(result['space_freed'])}</b><br>"
                    f"Backup location: <code>~/.image_organizer_backup</code>"
                )
                
                # Reset state
                self.scan_result = None
                self.analysis_results = None
                self.execute_btn.setEnabled(False)
                self.analyze_btn.setEnabled(False)
                self.results_table.setRowCount(0)
                self.summary_label.setText("📈 Cleanup complete! Start a new scan to continue.")
                
                # Update dashboard
                self.stat_duplicates_found.update_value("0")
                self.stat_space_recoverable.update_value("0 MB")
                
            except Exception as e:
                self._log(f"❌ Cleanup error: {e}")
                QMessageBox.critical(self, "Error", f"Cleanup failed:\n{e}")


def run_gui():
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
