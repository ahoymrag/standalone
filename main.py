import sys
import os
import json
import tempfile
import numpy as np
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QListWidget, 
                            QProgressBar, QMessageBox, QStackedWidget, QFrame,
                            QScrollArea, QSizePolicy, QSlider, QLineEdit,
                            QFileDialog, QListWidgetItem)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QUrl, QPoint, QPointF, QRectF
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QLinearGradient, QPalette, QPen, QDesktopServices, QMouseEvent, QKeyEvent
import pygame
from google.cloud import storage
from dotenv import load_dotenv
import requests
import threading
import librosa
import soundfile as sf

# Initialize pygame mixer
pygame.mixer.init()

class Surfer:
    def __init__(self, x, y):
        self.pos = QPointF(x, y)
        self.vel = QPointF(0, 0)
        self.acc = QPointF(0, 0)
        self.size = 20
        self.color = QColor("#FFD700")  # Gold color
        self.rotation = 0
        self.keys_pressed = set()
        self.max_speed = 5
        self.trail = []  # Store recent positions for trail effect
        self.max_trail_length = 10

    def update(self, width, height):
        # Reset acceleration
        self.acc = QPointF(0, 0)
        
        # Apply forces based on keys
        if 'W' in self.keys_pressed:
            self.acc += QPointF(0, -0.2)
        if 'S' in self.keys_pressed:
            self.acc += QPointF(0, 0.2)
        if 'A' in self.keys_pressed:
            self.acc += QPointF(-0.2, 0)
            self.rotation = -30
        if 'D' in self.keys_pressed:
            self.acc += QPointF(0.2, 0)
            self.rotation = 30
        
        # Update velocity and position
        self.vel += self.acc
        self.vel = self.vel * 0.95  # Damping
        self.pos += self.vel
        
        # Keep surfer within bounds
        self.pos.setX(max(self.size, min(width - self.size, self.pos.x())))
        self.pos.setY(max(self.size, min(height - self.size, self.pos.y())))
        
        # Update trail
        self.trail.append(QPointF(self.pos))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)
        
        # Reset rotation if no A/D keys
        if 'A' not in self.keys_pressed and 'D' not in self.keys_pressed:
            self.rotation = 0

    def draw(self, painter):
        # Draw trail
        for i, pos in enumerate(self.trail):
            alpha = int(255 * (i / len(self.trail)))
            trail_color = QColor(self.color)
            trail_color.setAlpha(alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(trail_color)
            size = self.size * (i / len(self.trail))
            painter.drawEllipse(pos, size, size)

        # Draw surfer
        painter.save()
        painter.translate(self.pos)
        painter.rotate(self.rotation)
        
        # Draw body
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.color)
        painter.drawEllipse(QRectF(-self.size/2, -self.size/2, self.size, self.size))
        
        # Draw face
        painter.setBrush(QColor("#000000"))
        painter.drawEllipse(QRectF(-self.size/4, -self.size/4, self.size/2, self.size/2))
        
        painter.restore()

class Particle:
    def __init__(self, x, y):
        self.pos = QPointF(x, y)
        self.vel = QPointF(0, 0)
        self.acc = QPointF(0, 0)
        self.size = np.random.uniform(2, 5)
        self.color = QColor("#e94560")
        self.color.setAlpha(150)
        self.max_speed = 5
        self.audio_force = 0

    def apply_force(self, force):
        self.acc += force

    def update(self):
        self.vel += self.acc
        self.vel = self.vel * 0.95  # Damping
        self.pos += self.vel
        self.acc *= 0
        self.audio_force *= 0.95  # Decay audio force

    def edges(self, width, height):
        if self.pos.x() < 0:
            self.pos.setX(0)
            self.vel.setX(-self.vel.x() * 0.8)
        elif self.pos.x() > width:
            self.pos.setX(width)
            self.vel.setX(-self.vel.x() * 0.8)
        if self.pos.y() < 0:
            self.pos.setY(0)
            self.vel.setY(-self.vel.y() * 0.8)
        elif self.pos.y() > height:
            self.pos.setY(height)
            self.vel.setY(-self.vel.y() * 0.8)

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

class VisualizationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.particles = []
        self.mouse_pos = QPointF(0, 0)
        self.mouse_pressed = False
        self.spectrum = np.zeros(50)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_visualization)
        self.timer.start(16)  # ~60 FPS for smooth animation
        
        # Initialize particles and surfer
        self.init_particles()
        self.surfer = Surfer(self.width()/2, self.height()/2)
        
        # Enable key tracking
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def init_particles(self):
        self.particles = []
        for _ in range(100):
            x = np.random.uniform(0, self.width())
            y = np.random.uniform(0, self.height())
            self.particles.append(Particle(x, y))

    def keyPressEvent(self, event: QKeyEvent):
        key = event.text().upper()
        if key in ['W', 'A', 'S', 'D']:
            self.surfer.keys_pressed.add(key)
            self.update()

    def keyReleaseEvent(self, event: QKeyEvent):
        key = event.text().upper()
        if key in ['W', 'A', 'S', 'D']:
            self.surfer.keys_pressed.discard(key)
            self.update()

    def mousePressEvent(self, event: QMouseEvent):
        self.mouse_pressed = True
        self.mouse_pos = QPointF(event.position())

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.mouse_pressed = False

    def mouseMoveEvent(self, event: QMouseEvent):
        self.mouse_pos = QPointF(event.position())

    def update_visualization(self):
        if pygame.mixer.music.get_busy():
            try:
                array = pygame.mixer.Sound.get_raw()
                if array:
                    spectrum = np.abs(np.fft.rfft(array))
                    spectrum = spectrum / np.max(spectrum)
                    self.spectrum = np.interp(np.linspace(0, len(spectrum), 50),
                                            np.arange(len(spectrum)), spectrum)
            except:
                pass

        # Update surfer
        self.surfer.update(self.width(), self.height())

        # Update particles
        for particle in self.particles:
            # Apply audio force
            if pygame.mixer.music.get_busy():
                idx = int((particle.pos.x() / self.width()) * len(self.spectrum))
                idx = min(max(idx, 0), len(self.spectrum) - 1)
                force = self.spectrum[idx] * 0.5
                particle.audio_force = force
                particle.apply_force(QPointF(0, -force * 2))  # Push up with audio

            # Apply mouse force
            if self.mouse_pressed:
                mouse_force = QPointF(self.mouse_pos - particle.pos)
                distance = mouse_force.manhattanLength()
                if distance < 100:
                    strength = (1 - distance/100) * 0.5
                    mouse_force = mouse_force * strength
                    particle.apply_force(mouse_force)

            # Apply surfing effect
            wave_force = QPointF(
                np.sin(particle.pos.y() * 0.02 + self.timer.interval() * 0.001) * 0.1,
                np.cos(particle.pos.x() * 0.02 + self.timer.interval() * 0.001) * 0.1
            )
            particle.apply_force(wave_force)

            # Apply surfer force to nearby particles
            surfer_force = QPointF(self.surfer.pos - particle.pos)
            distance = surfer_force.manhattanLength()
            if distance < 50:
                strength = (1 - distance/50) * 0.3
                surfer_force = surfer_force * strength
                particle.apply_force(surfer_force)

            particle.update()
            particle.edges(self.width(), self.height())

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background with gradient
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(26, 26, 46, 100))
        gradient.setColorAt(1, QColor(22, 33, 62, 100))
        painter.fillRect(self.rect(), gradient)

        # Draw particles
        for particle in self.particles:
            # Draw glow
            glow_color = QColor(particle.color)
            glow_color.setAlpha(50)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow_color)
            painter.drawEllipse(particle.pos, particle.size * 2, particle.size * 2)

            # Draw particle
            painter.setBrush(particle.color)
            painter.drawEllipse(particle.pos, particle.size, particle.size)

        # Draw surfer
        self.surfer.draw(painter)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.particles:  # Only initialize if particles don't exist
            self.init_particles()
            self.surfer = Surfer(self.width()/2, self.height()/2)

class TimeSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid rgba(255, 255, 255, 0.2);
                height: 8px;
                background: rgba(255, 255, 255, 0.1);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #e94560;
                border: none;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #e94560;
                border-radius: 4px;
            }
        """)
        self.setTracking(True)

class VolumeSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setMaximum(100)
        self.setValue(100)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid rgba(255, 255, 255, 0.2);
                height: 4px;
                background: rgba(255, 255, 255, 0.1);
                margin: 2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #e94560;
                border: none;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #e94560;
                border-radius: 2px;
            }
        """)
        self.setTracking(True)

class DownloadsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Your Downloads")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(header)
        
        # Open folder button
        open_folder_btn = GlassButton("Open Downloads Folder")
        open_folder_btn.clicked.connect(self.open_downloads_folder)
        layout.addWidget(open_folder_btn)
        
        # Downloads list
        self.downloads_list = QListWidget()
        self.downloads_list.setStyleSheet("""
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
        """)
        layout.addWidget(self.downloads_list)
        
        self.refresh_downloads_list()

    def refresh_downloads_list(self):
        self.downloads_list.clear()
        downloads_dir = Path("downloads")
        if downloads_dir.exists():
            for file in downloads_dir.glob("*.mp3"):
                item = QListWidgetItem(file.stem)
                item.setData(Qt.ItemDataRole.UserRole, str(file))
                self.downloads_list.addItem(item)

    def open_downloads_folder(self):
        downloads_path = Path("downloads").absolute()
        if downloads_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(downloads_path)))
        else:
            QMessageBox.warning(self, "Warning", "Downloads folder not found!")

class PodcastCard(GlassFrame):
    def __init__(self, podcast, parent=None):
        super().__init__(parent)
        self.podcast = podcast
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Cover Art (now clickable)
        cover_label = QLabel()
        pixmap = QPixmap()
        try:
            img_data = requests.get(podcast['cover_art']).content
            pixmap.loadFromData(img_data)
        except:
            pixmap = QPixmap(100, 100)
            pixmap.fill(QColor("#333"))
        cover_label.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        cover_label.setFixedSize(80, 80)
        cover_label.setCursor(Qt.CursorShape.PointingHandCursor)  # Show pointer cursor on hover
        cover_label.mousePressEvent = lambda e: self.play_podcast()  # Make clickable
        layout.addWidget(cover_label)

        # Info
        info_layout = QVBoxLayout()
        title = QLabel(podcast['title'])
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        info_layout.addWidget(title)
        host = QLabel(f"Host: <b>{podcast['host']}</b>")
        host.setStyleSheet("color: #e94560;")
        info_layout.addWidget(host)
        # Badges
        badge_layout = QHBoxLayout()
        if podcast.get('featured'):
            badge = QLabel("Featured")
            badge.setStyleSheet("background: rgba(233,69,96,0.3); color: #e94560; border-radius: 8px; padding: 2px 8px; font-size: 12px;")
            badge_layout.addWidget(badge)
        if podcast.get('recent'):
            badge = QLabel("Recent")
            badge.setStyleSheet("background: rgba(255,255,255,0.2); color: #fff; border-radius: 8px; padding: 2px 8px; font-size: 12px;")
            badge_layout.addWidget(badge)
        badge_layout.addStretch()
        info_layout.addLayout(badge_layout)
        layout.addLayout(info_layout)

        # Duration
        duration = QLabel(podcast.get('duration', ''))
        duration.setStyleSheet("color: #fff; background: rgba(255,255,255,0.1); border-radius: 6px; padding: 2px 8px;")
        layout.addWidget(duration)

        self.setFixedHeight(100)

    def play_podcast(self):
        # Get the main window instance
        main_window = self.window()
        if isinstance(main_window, AhoyIndieMedia):
            # Set current podcast info for the player
            main_window.current_podcast = self.podcast
            # Download and play the podcast
            main_window.download_and_play(self.podcast['mp3url'])
            # Update the track list to show the podcast
            main_window.track_list.clear()
            main_window.track_list.addItem(f"{self.podcast['title']} - {self.podcast['host']}")
            main_window.track_list.setCurrentRow(0)

class PodcastsPage(QWidget):
    def __init__(self, podcasts_data, parent=None):
        super().__init__(parent)
        self.podcasts_data = podcasts_data
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Search bar (placeholder)
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Search podcasts by title, host, or tag...")
        search_bar.setStyleSheet("background: rgba(255,255,255,0.1); color: white; border-radius: 8px; padding: 8px;")
        layout.addWidget(search_bar)

        # Category filter (placeholder)
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter by category:")
        filter_label.setStyleSheet("color: #fff;")
        filter_layout.addWidget(filter_label)
        for cat in self.podcasts_data.get('categories', []):
            btn = QPushButton(cat['label'])
            btn.setStyleSheet("background: rgba(255,255,255,0.15); color: #e94560; border-radius: 8px; padding: 4px 12px;")
            btn.setEnabled(False)  # Placeholder for now
            filter_layout.addWidget(btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Featured/recent section (placeholder)
        featured_label = QLabel("Featured & Recent")
        featured_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e94560;")
        layout.addWidget(featured_label)
        featured_scroll = QScrollArea()
        featured_scroll.setWidgetResizable(True)
        featured_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        featured_scroll.setStyleSheet("border: none;")
        
        featured_content = QWidget()
        featured_content_layout = QHBoxLayout(featured_content)
        featured_content_layout.setSpacing(20)
        
        for podcast in self.podcasts_data.get('podcasts', []):
            if podcast.get('featured') or podcast.get('recent'):
                card = PodcastCard(podcast)
                featured_content_layout.addWidget(card)
        
        featured_scroll.setWidget(featured_content)
        featured_scroll.setFixedHeight(120)
        featured_scroll.setStyleSheet("border: none;")
        layout.addWidget(featured_scroll)

        # All podcasts list
        all_label = QLabel("All Podcasts")
        all_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #fff;")
        layout.addWidget(all_label)
        podcasts_list = QVBoxLayout()
        for podcast in self.podcasts_data.get('podcasts', []):
            card = PodcastCard(podcast)
            podcasts_list.addWidget(card)
        podcasts_list.addStretch()
        layout.addLayout(podcasts_list)

class AhoyIndieMedia(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ahoy Indie Media")
        self.setMinimumSize(1200, 800)
        
        # Initialize batch tracking
        self.current_batch_id = str(uuid.uuid4())[:8]  # Generate a unique 8-character batch ID
        self.batch_start_time = datetime.now()
        
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

        # Initialize playback timer
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_playback_position)
        self.playback_timer.start(1000)  # Update every second

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
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                color: white;
                padding: 5px;
            }
        """)

    def create_favicon(self):
        # Create a red square favicon
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#e94560"))
        return pixmap

    def load_music_data(self):
        with open('data/music_library.json', 'r') as f:
            self.music_data = json.load(f)

    def setup_ui(self):
        # Ensure progress bar exists first
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        
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
            ("Downloads", self.show_downloads),
            ("Podcasts", self.show_podcasts)
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
        
        # Featured section (only if playlists exist)
        if 'playlists' in self.music_data:
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
                if playlist.get('featured'):
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
        
        # Add other pages
        self.content_stack.addWidget(QWidget())  # Library page
        self.content_stack.addWidget(QWidget())  # Playlists page
        self.downloads_page = DownloadsPage()
        self.content_stack.addWidget(self.downloads_page)
        self.podcasts_page = PodcastsPage(self.load_podcasts_data())
        self.content_stack.addWidget(self.podcasts_page)
        
        main_layout.addWidget(self.content_stack)

        # Player controls at bottom
        player_frame = GlassFrame()
        player_layout = QVBoxLayout(player_frame)
        
        # Visualization
        self.visualization = VisualizationWidget()
        player_layout.addWidget(self.visualization)
        
        # Music player card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(30, 30, 40, 0.18); /* subtle glass effect, no strong color */
                border-radius: 20px;
                border: 1px solid rgba(255,255,255,0.10);
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 24, 32, 24)
        card_layout.setSpacing(16)
        
        # Song info
        self.track_title = QLabel("Song Name")
        self.track_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        self.track_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.track_artist = QLabel("Artist Name • Album Name")
        self.track_artist.setStyleSheet("font-size: 14px; color: #e0e0e0;")
        self.track_artist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.track_title)
        card_layout.addWidget(self.track_artist)
        
        # Timeline slider
        timeline_layout = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet("color: #fff; font-size: 12px;")
        self.time_slider = TimeSlider()
        self.time_slider.sliderMoved.connect(self.seek_position)
        self.total_time_label = QLabel("3:45")
        self.total_time_label.setStyleSheet("color: #fff; font-size: 12px;")
        timeline_layout.addWidget(self.current_time_label)
        timeline_layout.addWidget(self.time_slider)
        timeline_layout.addWidget(self.total_time_label)
        card_layout.addLayout(timeline_layout)
        
        # Unified glassy button style
        glassy_btn_style = """
            QPushButton {
                background: rgba(255,255,255,0.18);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 12px;
                color: white;
                font-size: 18px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.28);
                color: #e94560;
            }
            QPushButton:pressed {
                background: rgba(255,255,255,0.35);
            }
        """
        
        # Controls row
        controls_row = QHBoxLayout()
        controls_row.setSpacing(18)
        
        # Shuffle
        self.shuffle_button = GlassButton("🔀")
        self.shuffle_button.setFixedSize(32,32)
        self.shuffle_button.setStyleSheet(glassy_btn_style)
        controls_row.addWidget(self.shuffle_button)
        
        # Previous
        self.prev_button = GlassButton("⏮")
        self.prev_button.setFixedSize(40,40)
        self.prev_button.setStyleSheet(glassy_btn_style)
        self.prev_button.clicked.connect(self.previous_track)
        controls_row.addWidget(self.prev_button)
        
        # Play/Pause
        self.play_button = GlassButton("▶️")
        self.play_button.setFixedSize(56,56)
        self.play_button.setStyleSheet(glassy_btn_style + "font-size: 24px;")
        self.play_button.clicked.connect(self.toggle_play)
        controls_row.addWidget(self.play_button)
        
        # Next
        self.next_button = GlassButton("⏭")
        self.next_button.setFixedSize(40,40)
        self.next_button.setStyleSheet(glassy_btn_style)
        self.next_button.clicked.connect(self.next_track)
        controls_row.addWidget(self.next_button)
        
        # Repeat
        self.repeat_button = GlassButton("🔁")
        self.repeat_button.setFixedSize(32,32)
        self.repeat_button.setStyleSheet(glassy_btn_style)
        controls_row.addWidget(self.repeat_button)
        
        card_layout.addLayout(controls_row)
        
        # Bottom row: favorite, download, up next
        bottom_row = QHBoxLayout()
        self.favorite_button = GlassButton("♥")
        self.favorite_button.setFixedSize(28,28)
        self.favorite_button.setStyleSheet(glassy_btn_style)
        bottom_row.addWidget(self.favorite_button)
        
        self.download_button = GlassButton("⬇")
        self.download_button.setFixedSize(28,28)
        self.download_button.setStyleSheet(glassy_btn_style)
        self.download_button.clicked.connect(self.download_current_track)
        bottom_row.addWidget(self.download_button)
        
        bottom_row.addStretch()
        up_next_label = QLabel("Up Next")
        up_next_label.setStyleSheet("color: #fff; font-size: 14px; font-weight: 500;")
        bottom_row.addWidget(up_next_label)
        card_layout.addLayout(bottom_row)
        
        player_layout.addWidget(card)
        
        # Download progress
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
        self.track_list.clear()
        for song in self.music_data['music_library']:
            item_text = f"{song['songTitle']} - {song['artist']}"
            self.track_list.addItem(item_text)

    def show_dashboard(self):
        self.content_stack.setCurrentIndex(0)

    def show_library(self):
        # Show the music library tab with thumbnails
        self.content_stack.setCurrentIndex(1)
        # Create or update the music library widget
        if not hasattr(self, 'music_library_widget'):
            self.music_library_widget = QWidget()
            layout = QVBoxLayout(self.music_library_widget)
            label = QLabel('Music Library')
            label.setStyleSheet('font-size: 24px; font-weight: bold; color: white;')
            layout.addWidget(label)
            self.library_list = QListWidget()
            self.library_list.setIconSize(QSize(60, 60))
            for song in self.music_data['music_library']:
                item = QListWidgetItem()
                item.setText(f"{song['songTitle']} - {song['artist']}")
                if song.get('thumbnail'):
                    pixmap = QPixmap()
                    try:
                        img_data = requests.get(song['thumbnail']).content
                        pixmap.loadFromData(img_data)
                        item.setIcon(QIcon(pixmap))
                    except:
                        pass
                self.library_list.addItem(item)
            layout.addWidget(self.library_list)
            self.content_stack.insertWidget(1, self.music_library_widget)
        else:
            self.content_stack.setCurrentWidget(self.music_library_widget)

    def show_playlists(self):
        self.content_stack.setCurrentIndex(2)

    def show_downloads(self):
        self.content_stack.setCurrentIndex(3)

    def show_podcasts(self):
        self.content_stack.setCurrentIndex(4)

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
            # Update track info for podcast or song
            if hasattr(self, 'current_podcast'):
                self.update_track_info(
                    self.current_podcast['title'],
                    f"Host: {self.current_podcast['host']}",
                    self.current_podcast.get('cover_art')
                )
            elif hasattr(self, 'music_data') and self.track_list.currentItem():
                idx = self.track_list.currentRow()
                song = self.music_data['music_library'][idx]
                self.update_track_info(song['songTitle'], song['artist'], song.get('thumbnail'))
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
            song = self.music_data['music_library'][current_index]
            
            local_path = f"downloads/{song['id']}.mp3"
            if os.path.exists(local_path):
                pygame.mixer.music.load(local_path)
                pygame.mixer.music.play()
                self.play_button.setText("Pause")
                self.is_playing = True
            else:
                self.download_and_play(song['mp3url'])

    def generate_download_filename(self, song):
        """Generate a clean filename for downloads"""
        # Clean the artist and title names to be filesystem-friendly
        artist = "".join(c for c in song['artist'] if c.isalnum() or c in (' ', '-', '_')).strip()
        title = "".join(c for c in song['songTitle'] if c.isalnum() or c in (' ', '-', '_')).strip()
        
        # Format: Artist - Title.mp3
        return f"{artist} - {title}.mp3"

    def download_current_track(self):
        if not self.track_list.currentItem():
            return

        current_index = self.track_list.currentRow()
        song = self.music_data['music_library'][current_index]
        
        # Generate the new filename
        filename = self.generate_download_filename(song)
        local_path = os.path.join("downloads", filename)
        
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
        self.downloads_page.refresh_downloads_list()
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

    def update_playback_position(self):
        if self.is_playing:
            try:
                pos = pygame.mixer.music.get_pos() / 1000  # Convert to seconds
                self.current_time_label.setText(self.format_time(pos))
            except:
                pass

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"

    def set_volume(self, value):
        pygame.mixer.music.set_volume(value / 100)

    def previous_track(self):
        if self.track_list.currentRow() > 0:
            self.track_list.setCurrentRow(self.track_list.currentRow() - 1)
            self.play_current_track()

    def next_track(self):
        if self.track_list.currentRow() < self.track_list.count() - 1:
            self.track_list.setCurrentRow(self.track_list.currentRow() + 1)
            self.play_current_track()

    def play_current_track(self):
        if self.track_list.currentItem():
            current_index = self.track_list.currentRow()
            song = self.music_data['music_library'][current_index]
            local_path = f"downloads/{song['id']}.mp3"
            if os.path.exists(local_path):
                pygame.mixer.music.load(local_path)
            else:
                self.download_and_play(song['mp3url'])
                return
            pygame.mixer.music.play()
            self.play_button.setText("Pause")
            self.is_playing = True
            # Update track info
            self.update_track_info(song['songTitle'], song['artist'], song.get('thumbnail'))
            # Update total time
            try:
                duration = librosa.get_duration(path=local_path)
                self.total_time_label.setText(self.format_time(duration))
                self.time_slider.setMaximum(int(duration))
            except:
                pass

    def start_new_batch(self):
        """Start a new download batch with a new ID"""
        self.current_batch_id = str(uuid.uuid4())[:8]
        self.batch_start_time = datetime.now()

    def load_podcasts_data(self):
        with open('data/podcasts_library.json', 'r') as f:
            return json.load(f)

    def seek_position(self, position):
        """Handle timeline dragging"""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.set_pos(position)
            self.current_time_label.setText(self.format_time(position))

    def skip_time(self, seconds):
        """Skip forward or backward by specified seconds"""
        if pygame.mixer.music.get_busy():
            current_pos = pygame.mixer.music.get_pos() / 1000  # Convert to seconds
            new_pos = max(0, current_pos + seconds)
            pygame.mixer.music.set_pos(new_pos)
            self.current_time_label.setText(self.format_time(new_pos))

    def update_thumbnail(self, url=None):
        """Update the thumbnail image"""
        if url:
            try:
                response = requests.get(url)
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                self.thumbnail_label.setPixmap(pixmap.scaled(
                    60, 60, 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            except:
                # Set default thumbnail if loading fails
                self.thumbnail_label.setPixmap(QPixmap(60, 60))
        else:
            # Clear thumbnail
            self.thumbnail_label.setPixmap(QPixmap(60, 60))

    def toggle_playback_speed(self):
        """Toggle between different playback speeds"""
        speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        current_speed = float(self.speed_button.text().replace('x', ''))
        current_index = speeds.index(current_speed)
        next_index = (current_index + 1) % len(speeds)
        new_speed = speeds[next_index]
        
        self.speed_button.setText(f"{new_speed}x")
        if pygame.mixer.music.get_busy():
            # Note: pygame doesn't support playback speed directly
            # This is a placeholder for when we implement a different audio backend
            pass

    def toggle_mute(self):
        """Toggle mute state"""
        if not hasattr(self, 'previous_volume'):
            self.previous_volume = self.volume_slider.value()
            self.volume_slider.setValue(0)
            self.volume_button.setText("🔇")
        else:
            self.volume_slider.setValue(self.previous_volume)
            self.volume_button.setText("🔊")
            delattr(self, 'previous_volume')

    def update_track_info(self, title, artist=None, cover_url=None):
        """Update track information display"""
        self.track_title.setText(title)
        if artist:
            self.track_artist.setText(artist)
        else:
            self.track_artist.setText("")
        self.update_thumbnail(cover_url)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AhoyIndieMedia()
    window.show()
    sys.exit(app.exec()) 