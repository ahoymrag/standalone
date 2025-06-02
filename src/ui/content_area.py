from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QStackedWidget
from PyQt6.QtCore import Qt
from .music_library import MusicLibrary

class ContentArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("content-area")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Create stacked widget for different views
        self.stacked_widget = QStackedWidget()
        
        # Create music library view
        self.music_library = MusicLibrary(self)
        self.stacked_widget.addWidget(self.music_library)
        
        # Create welcome view
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        
        welcome_label = QLabel("Welcome to Music Player")
        welcome_label.setObjectName("welcome-label")
        welcome_layout.addWidget(welcome_label)
        
        placeholder = QLabel(
            "Your music library will appear here.\n"
            "Use the sidebar to navigate between different sections."
        )
        placeholder.setObjectName("placeholder-text")
        welcome_layout.addWidget(placeholder)
        
        welcome_layout.addStretch()
        self.stacked_widget.addWidget(welcome_widget)
        
        # Add stacked widget to layout
        layout.addWidget(self.stacked_widget)
        
        # Apply styles
        self.setStyleSheet("""
            QWidget#content-area {
                background-color: #1e1e1e;
            }
            QLabel#welcome-label {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
            }
            QLabel#placeholder-text {
                color: #888888;
                font-size: 14px;
            }
            QStackedWidget {
                background-color: transparent;
            }
        """)
        
    def show_music_library(self):
        """Switch to music library view."""
        self.stacked_widget.setCurrentWidget(self.music_library)
        
    def show_welcome(self):
        """Switch to welcome view."""
        self.stacked_widget.setCurrentIndex(1)
        
    def scan_music_directory(self, directory: str):
        """Scan a directory for music files and add them to the library."""
        # This method will be implemented in the main window
        pass 