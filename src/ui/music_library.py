from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QListWidgetItem, QLabel, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path

class MusicLibrary(QWidget):
    track_selected = pyqtSignal(str)  # Emitted when a track is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Music Library")
        title.setObjectName("library-title")
        add_button = QPushButton("Add Music")
        add_button.clicked.connect(self._on_add_music)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(add_button)
        
        # Library view
        self.library_list = QListWidget()
        self.library_list.itemDoubleClicked.connect(self._on_track_selected)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.library_list)
        
        # Apply styles
        self.setStyleSheet("""
            QLabel#library-title {
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton {
                color: #ffffff;
                background-color: #404040;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QListWidget {
                background-color: #252525;
                border: none;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:selected {
                background-color: #404040;
            }
            QListWidget::item:hover {
                background-color: #333333;
            }
        """)
        
    def add_track(self, track_path: str):
        """Add a track to the library view."""
        item = QListWidgetItem(Path(track_path).name)
        item.setData(Qt.ItemDataRole.UserRole, track_path)
        self.library_list.addItem(item)
        
    def clear(self):
        """Clear the library view."""
        self.library_list.clear()
        
    def _on_add_music(self):
        """Handle add music button click."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Music Directory",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            # Emit signal to notify parent to scan directory
            self.parent().scan_music_directory(directory)
            
    def _on_track_selected(self, item: QListWidgetItem):
        """Handle track selection."""
        track_path = item.data(Qt.ItemDataRole.UserRole)
        self.track_selected.emit(track_path) 