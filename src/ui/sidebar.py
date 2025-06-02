from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        self.nav_buttons = []  # Store navigation buttons
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)
        
        # Logo/Title
        title = QLabel("Music Player")
        title.setObjectName("sidebar-title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Navigation buttons
        nav_buttons = [
            ("Music", "music"),
            ("Podcasts", "podcast"),
            ("News", "news"),
            ("Playlists", "playlist"),
            ("Settings", "settings")
        ]
        
        for text, icon_name in nav_buttons:
            btn = QPushButton(text)
            btn.setObjectName(f"nav-{icon_name}")
            btn.setCheckable(True)
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        layout.addStretch()
        
        # Apply styles
        self.setStyleSheet("""
            QWidget#sidebar {
                background-color: #252525;
                border-right: 1px solid #333333;
            }
            QLabel#sidebar-title {
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton {
                color: #ffffff;
                background-color: transparent;
                border: none;
                padding: 10px;
                text-align: left;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
            QPushButton:checked {
                background-color: #404040;
            }
        """) 