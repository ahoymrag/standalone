import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from src.ui.sidebar import Sidebar
from src.ui.player_controls import PlayerControls
from src.ui.content_area import ContentArea
from src.core.player import MusicPlayer
from src.core.playlist import PlaylistManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern Music Player")
        self.setMinimumSize(1000, 600)
        
        # Initialize core components
        self.player = MusicPlayer()
        self.playlist_manager = PlaylistManager()
        
        # Set up the main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Add main content area
        self.content_area = ContentArea()
        content_layout.addWidget(self.content_area)
        
        # Add player controls at the bottom
        self.player_controls = PlayerControls()
        content_layout.addWidget(self.player_controls)
        
        main_layout.addWidget(content_widget)
        
        # Connect player signals
        self.player_controls.play_clicked.connect(self.player.play)
        self.player_controls.pause_clicked.connect(self.player.pause)
        self.player_controls.volume_changed.connect(self.player.set_volume)
        self.player_controls.position_changed.connect(self.player.set_position)
        
        # Connect player to controls
        self.player.position_changed.connect(self.player_controls.set_position)
        self.player.duration_changed.connect(self.player_controls.set_duration)
        self.player.state_changed.connect(self._on_player_state_changed)
        
        # Connect sidebar navigation
        self.sidebar.nav_buttons[0].clicked.connect(self.content_area.show_music_library)
        
        # Connect music library
        self.content_area.music_library.track_selected.connect(self._on_track_selected)
        
        # Set window properties
        self.setWindowFlags(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                color: #ffffff;
                background-color: #1e1e1e;
            }
        """)
        
    def _on_player_state_changed(self, is_playing):
        if is_playing:
            self.player_controls.play_btn.setText("⏸")
        else:
            self.player_controls.play_btn.setText("▶")
            
    def _on_track_selected(self, track_path: str):
        """Handle track selection from music library."""
        self.player.load(track_path)
        self.player.play()
        
    def scan_music_directory(self, directory: str):
        """Scan a directory for music files and add them to the library."""
        music_files = self.playlist_manager.scan_directory(directory)
        self.content_area.music_library.clear()
        for file_path in music_files:
            self.content_area.music_library.add_track(file_path)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Use Fusion style for better cross-platform appearance
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 