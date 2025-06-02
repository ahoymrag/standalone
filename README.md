# Modern Music Player

A feature-rich desktop music player built with PyQt6, supporting music playback, podcasts, and news updates.

## Features

- Modern dark-themed UI
- Music playback with playlist support
- Podcast integration
- News updates
- System tray integration
- Global media controls
- Mini-player mode
- Theme customization

## Requirements

- Python 3.8 or higher
- VLC Media Player (for audio playback)
- PyQt6 and other dependencies listed in requirements.txt

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

```bash
python main.py
```

## Project Structure

```
├── main.py              # Application entry point
├── requirements.txt     # Project dependencies
├── src/                # Source code
│   ├── ui/            # UI components
│   ├── core/          # Core functionality
│   ├── data/          # Data management
│   └── utils/         # Utility functions
├── resources/         # Application resources
│   ├── icons/        # Application icons
│   ├── styles/       # CSS stylesheets
│   └── themes/       # Theme definitions
└── tests/            # Test files
```

## License

MIT License 