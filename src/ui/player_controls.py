from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QPushButton, 
                             QSlider, QLabel, QVBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

class PlayerControls(QWidget):
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    previous_clicked = pyqtSignal()
    volume_changed = pyqtSignal(int)
    position_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("player-controls")
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        
        # Progress bar and time labels
        progress_layout = QHBoxLayout()
        self.time_label = QLabel("0:00")
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.total_time_label = QLabel("0:00")
        
        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.total_time_label)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.previous_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(100)
        
        controls_layout.addWidget(self.previous_btn)
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.next_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(self.volume_slider)
        
        # Add layouts to main layout
        main_layout.addLayout(progress_layout)
        main_layout.addLayout(controls_layout)
        
        # Connect signals
        self.play_btn.clicked.connect(self.toggle_play)
        self.previous_btn.clicked.connect(self.previous_clicked)
        self.next_btn.clicked.connect(self.next_clicked)
        self.volume_slider.valueChanged.connect(self.volume_changed)
        self.progress_slider.valueChanged.connect(self.position_changed)
        
        # Apply styles
        self.setStyleSheet("""
            QWidget#player-controls {
                background-color: #252525;
                border-top: 1px solid #333333;
            }
            QPushButton {
                color: #ffffff;
                background-color: transparent;
                border: none;
                padding: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-radius: 3px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 4px;
                background: #404040;
                margin: 2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #5c5c5c;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QLabel {
                color: #ffffff;
                padding: 0 5px;
            }
        """)
        
    def toggle_play(self):
        if self.play_btn.text() == "▶":
            self.play_btn.setText("⏸")
            self.play_clicked.emit()
        else:
            self.play_btn.setText("▶")
            self.pause_clicked.emit()
            
    def set_position(self, position):
        self.progress_slider.setValue(position)
        
    def set_duration(self, duration):
        self.progress_slider.setMaximum(duration)
        
    def set_time_labels(self, current, total):
        self.time_label.setText(self.format_time(current))
        self.total_time_label.setText(self.format_time(total))
        
    def format_time(self, milliseconds):
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}" 