# Dog Bark Detection System for Home Assistant

A lightweight, real-time bark detection system that monitors audio from a USB microphone and reports barking events to Home Assistant via MQTT. Uses simple decibel threshold analysis for fast, reliable detection without requiring machine learning models.

## Features

- Real-time bark detection using decibel burst analysis
- MQTT integration with Home Assistant auto-discovery
- Configurable thresholds for sensitivity tuning
- Automatic reconnection and retry logic for reliability
- Systemd service for continuous operation with auto-restart
- Low resource usage (< 5% CPU, < 50 MB RAM)
- Comprehensive logging with configurable levels

## Hardware Requirements

- USB Microphone: Blue Snowball or any USB audio device
- Linux system with Python 3.8+, USB audio access, and network connectivity

## Installation

### 1. Clone and Install Dependencies

```bash
cd ~/Projects
git clone <repository-url>
cd ha-bark-detection
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv if needed
uv sync
```

### 2. Configure

```bash
cp .env.example .env
nano .env  # Edit configuration
```

### 3. Test

```bash
uv run python -m bark_detector.main
```

### 4. Install Service

```bash
./systemd/install_service.sh
```

## Usage

```bash
systemctl --user start bark-detector
systemctl --user status bark-detector
journalctl --user -u bark-detector -f
```

## Documentation

See [README.md](README.md) for full documentation including:
- Configuration reference
- Troubleshooting guide
- Home Assistant integration
- Example automations

## License

[Add your license here]
