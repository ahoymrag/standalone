from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

class MusicPlayer(QObject):
    position_changed = pyqtSignal(int)  # Current position in milliseconds
    duration_changed = pyqtSignal(int)  # Total duration in milliseconds
    state_changed = pyqtSignal(bool)    # True if playing, False if paused
    track_changed = pyqtSignal(str)     # Current track name
    
    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.current_track = None
        
        # Connect player signals
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        
    def play(self, file_path=None):
        if file_path:
            self.load(file_path)
        self.player.play()
        
    def pause(self):
        self.player.pause()
        
    def stop(self):
        self.player.stop()
        
    def load(self, file_path):
        self.current_track = file_path
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.track_changed.emit(file_path)
        
    def set_volume(self, volume):
        self.audio_output.setVolume(volume / 100.0)  # Convert to 0-1 range
        
    def set_position(self, position):
        self.player.setPosition(position)
        
    def _on_position_changed(self, position):
        self.position_changed.emit(position)
        
    def _on_duration_changed(self, duration):
        self.duration_changed.emit(duration)
        
    def _on_state_changed(self, state):
        is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.state_changed.emit(is_playing)
        
    def get_duration(self):
        return self.player.duration()
        
    def is_playing(self):
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        
    def get_volume(self):
        return int(self.audio_output.volume() * 100)  # Convert to 0-100 range 