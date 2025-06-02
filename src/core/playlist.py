import os
import json
from pathlib import Path
from typing import List, Dict, Optional

class PlaylistManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.playlists_file = self.data_dir / "playlists.json"
        self.playlists: Dict[str, List[str]] = {}
        self._ensure_data_dir()
        self._load_playlists()
        
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_playlists(self):
        """Load playlists from JSON file."""
        if self.playlists_file.exists():
            try:
                with open(self.playlists_file, 'r') as f:
                    self.playlists = json.load(f)
            except json.JSONDecodeError:
                self.playlists = {}
        else:
            self.playlists = {}
            
    def _save_playlists(self):
        """Save playlists to JSON file."""
        with open(self.playlists_file, 'w') as f:
            json.dump(self.playlists, f, indent=2)
            
    def create_playlist(self, name: str) -> bool:
        """Create a new playlist."""
        if name in self.playlists:
            return False
        self.playlists[name] = []
        self._save_playlists()
        return True
        
    def delete_playlist(self, name: str) -> bool:
        """Delete a playlist."""
        if name not in self.playlists:
            return False
        del self.playlists[name]
        self._save_playlists()
        return True
        
    def add_to_playlist(self, playlist_name: str, track_path: str) -> bool:
        """Add a track to a playlist."""
        if playlist_name not in self.playlists:
            return False
        if track_path not in self.playlists[playlist_name]:
            self.playlists[playlist_name].append(track_path)
            self._save_playlists()
        return True
        
    def remove_from_playlist(self, playlist_name: str, track_path: str) -> bool:
        """Remove a track from a playlist."""
        if playlist_name not in self.playlists:
            return False
        if track_path in self.playlists[playlist_name]:
            self.playlists[playlist_name].remove(track_path)
            self._save_playlists()
        return True
        
    def get_playlist(self, name: str) -> Optional[List[str]]:
        """Get all tracks in a playlist."""
        return self.playlists.get(name)
        
    def get_all_playlists(self) -> Dict[str, List[str]]:
        """Get all playlists."""
        return self.playlists.copy()
        
    def scan_directory(self, directory: str) -> List[str]:
        """Scan a directory for music files."""
        music_files = []
        valid_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.m4a'}
        
        for root, _, files in os.walk(directory):
            for file in files:
                if Path(file).suffix.lower() in valid_extensions:
                    music_files.append(os.path.join(root, file))
                    
        return music_files 