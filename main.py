import sys
import os
import json
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QListWidget, 
                            QProgressBar, QMessageBox, QStackedWidget, QFrame,
                            QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QLinearGradient, QPalette
import pygame
from google.cloud import storage
from dotenv import load_dotenv
import requests
import threading

# Initialize pygame mixer
pygame.mixer.init()

class GlassFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)

class GlassButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                color: white;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)

class MusicDownloader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, local_path):
        super().__init__()
        self.url = url
        self.local_path = local_path

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            downloaded = 0

            os.makedirs(os.path.dirname(self.local_path), exist_ok=True)
            
            with open(self.local_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    if total_size:
                        progress = int((downloaded / total_size) * 100)
                        self.progress.emit(progress)
            
            self.finished.emit(self.local_path)
        except Exception as e:
            self.error.emit(str(e))

class AhoyIndieMedia(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ahoy Indie Media")
        self.setMinimumSize(1200, 800)
        
        # Set window icon
        self.setWindowIcon(QIcon(self.create_favicon()))
        
        # Initialize storage client
        load_dotenv()
        self.storage_client = storage.Client()
        self.bucket_name = "ahoy-song-collection"
        
        # Load music data
        self.load_music_data()
        
        # Setup UI
        self.setup_ui()
        
        # Initialize player state
        self.current_track = None
        self.is_playing = False
        self.downloaded_tracks = set()
        self.temp_files = []
        self.load_downloaded_tracks()

        # Set window background
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #1a1a2e, stop:1 #16213e);
            }
            QLabel {
                color: white;
            }
            QListWidget {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                color: white;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #e94560;
            }
        """)

    def create_favicon(self):
        # Create a red square favicon
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#e94560"))
        return pixmap

    def load_music_data(self):
        with open('data/tempRefData/music.json', 'r') as f:
            self.music_data = json.load(f)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Left sidebar
        sidebar = GlassFrame()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        
        # Logo
        logo_label = QLabel("AHOY")
        logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #e94560;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(logo_label)
        
        # Navigation buttons
        nav_buttons = [
            ("Dashboard", self.show_dashboard),
            ("Library", self.show_library),
            ("Playlists", self.show_playlists),
            ("Downloads", self.show_downloads)
        ]
        
        for text, callback in nav_buttons:
            btn = GlassButton(text)
            btn.clicked.connect(callback)
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # Main content area
        self.content_stack = QStackedWidget()
        
        # Dashboard page
        dashboard = QWidget()
        dashboard_layout = QVBoxLayout(dashboard)
        
        # Featured section
        featured_label = QLabel("Featured")
        featured_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        dashboard_layout.addWidget(featured_label)
        
        featured_scroll = QScrollArea()
        featured_scroll.setWidgetResizable(True)
        featured_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        featured_scroll.setStyleSheet("border: none;")
        
        featured_content = QWidget()
        featured_content_layout = QHBoxLayout(featured_content)
        featured_content_layout.setSpacing(20)
        
        for playlist in self.music_data['playlists']:
            if playlist['featured']:
                playlist_widget = self.create_playlist_widget(playlist)
                featured_content_layout.addWidget(playlist_widget)
        
        featured_scroll.setWidget(featured_content)
        dashboard_layout.addWidget(featured_scroll)
        
        # Recent tracks
        recent_label = QLabel("Recent Tracks")
        recent_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        dashboard_layout.addWidget(recent_label)
        
        self.track_list = QListWidget()
        self.populate_track_list()
        dashboard_layout.addWidget(self.track_list)
        
        self.content_stack.addWidget(dashboard)
        
        # Add other pages (Library, Playlists, Downloads)
        for _ in range(3):
            page = QWidget()
            self.content_stack.addWidget(page)
        
        main_layout.addWidget(self.content_stack)

        # Player controls at bottom
        player_frame = GlassFrame()
        player_layout = QHBoxLayout(player_frame)
        
        self.play_button = GlassButton("Play")
        self.play_button.clicked.connect(self.toggle_play)
        self.download_button = GlassButton("Download")
        self.download_button.clicked.connect(self.download_current_track)
        
        player_layout.addWidget(self.play_button)
        player_layout.addWidget(self.download_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        player_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(player_frame)

    def create_playlist_widget(self, playlist):
        widget = GlassFrame()
        layout = QVBoxLayout(widget)
        
        cover_label = QLabel()
        pixmap = QPixmap()
        pixmap.loadFromData(requests.get(playlist['coverImage']).content)
        cover_label.setPixmap(pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio))
        
        title_label = QLabel(playlist['title'])
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold;")
        
        desc_label = QLabel(playlist['description'])
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(cover_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        return widget

    def populate_track_list(self):
        for song in self.music_data['songs']:
            item_text = f"{song['title']} - {song['artist']}"
            self.track_list.addItem(item_text)

    def show_dashboard(self):
        self.content_stack.setCurrentIndex(0)

    def show_library(self):
        self.content_stack.setCurrentIndex(1)

    def show_playlists(self):
        self.content_stack.setCurrentIndex(2)

    def show_downloads(self):
        self.content_stack.setCurrentIndex(3)

    def download_and_play(self, url):
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file.close()
            
            response = requests.get(url, stream=True)
            with open(temp_file.name, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.temp_files.append(temp_file.name)
            
            pygame.mixer.music.load(temp_file.name)
            pygame.mixer.music.play()
            self.play_button.setText("Pause")
            self.is_playing = True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error playing track: {str(e)}")

    def toggle_play(self):
        if not self.track_list.currentItem():
            return

        if self.is_playing:
            pygame.mixer.music.pause()
            self.play_button.setText("Play")
            self.is_playing = False
        else:
            current_index = self.track_list.currentRow()
            song = self.music_data['songs'][current_index]
            
            local_path = f"downloads/{song['id']}.mp3"
            if os.path.exists(local_path):
                pygame.mixer.music.load(local_path)
                pygame.mixer.music.play()
                self.play_button.setText("Pause")
                self.is_playing = True
            else:
                self.download_and_play(song['mp3url'])

    def download_current_track(self):
        if not self.track_list.currentItem():
            return

        current_index = self.track_list.currentRow()
        song = self.music_data['songs'][current_index]
        
        local_path = f"downloads/{song['id']}.mp3"
        if os.path.exists(local_path):
            QMessageBox.information(self, "Already Downloaded", 
                                  "This track is already downloaded!")
            return

        self.progress_bar.show()
        self.downloader = MusicDownloader(song['mp3url'], local_path)
        self.downloader.progress.connect(self.update_progress)
        self.downloader.finished.connect(self.download_finished)
        self.downloader.error.connect(self.download_error)
        self.downloader.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def download_finished(self, path):
        self.progress_bar.hide()
        self.downloaded_tracks.add(path)
        self.save_downloaded_tracks()
        QMessageBox.information(self, "Download Complete", 
                              "Track has been downloaded successfully!")

    def download_error(self, error):
        self.progress_bar.hide()
        QMessageBox.critical(self, "Download Error", f"Error downloading track: {error}")

    def load_downloaded_tracks(self):
        try:
            with open('downloads/downloaded_tracks.json', 'r') as f:
                self.downloaded_tracks = set(json.load(f))
        except FileNotFoundError:
            self.downloaded_tracks = set()

    def save_downloaded_tracks(self):
        os.makedirs('downloads', exist_ok=True)
        with open('downloads/downloaded_tracks.json', 'w') as f:
            json.dump(list(self.downloaded_tracks), f)

    def closeEvent(self, event):
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AhoyIndieMedia()
    window.show()
    sys.exit(app.exec()) 