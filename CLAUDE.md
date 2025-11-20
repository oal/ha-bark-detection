# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## Project Overview

This is a Python-based real-time bark detection system that monitors audio from a USB microphone and publishes detection events to Home Assistant via MQTT. It uses decibel burst analysis (not ML models) for lightweight, reliable detection.

## Development Commands

### Setup and Installation
```bash
# Install dependencies (uses uv package manager)
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your settings (MQTT broker, microphone settings, thresholds)
```

### Running the Application
```bash
# Run directly (for testing/development)
uv run python -m bark_detector.main

# Run in debug mode (shows real-time audio levels and stats)
uv run python -m bark_detector.main --debug

# Install as systemd service
./systemd/install_service.sh

# Service management
systemctl --user start bark-detector
systemctl --user stop bark-detector
systemctl --user status bark-detector
journalctl --user -u bark-detector -f
```

### Testing Individual Modules
```bash
# Test configuration loading
uv run python -m bark_detector.config

# Test audio capture (10 second capture test)
uv run python -m bark_detector.audio

# Test bark detector (live audio test)
uv run python -m bark_detector.detector

# Test MQTT publisher (sends 3 test events)
uv run python -m bark_detector.mqtt_client
```

### Useful Development Tools
```bash
# List available audio devices and their indices
uv run python -c "import sounddevice as sd; print(sd.query_devices())"

# Test MQTT broker connection
mosquitto_sub -h <broker-ip> -t "homeassistant/#" -v
```

## Architecture

### Module Structure
The codebase follows a clean modular architecture with clear separation of concerns:

- **`bark_detector/main.py`**: Entry point and orchestration
  - Integrates all components (audio, detection, MQTT)
  - Handles signal handling (SIGINT, SIGTERM) for graceful shutdown
  - Provides statistics tracking (runtime, chunks processed, barks detected)

- **`bark_detector/audio.py`**: Audio capture via USB microphone
  - Uses `sounddevice` library (requires PortAudio system library)
  - Implements device discovery by USB ID with fallback to default input
  - Thread-safe queue-based audio streaming with callback architecture
  - Supports context manager pattern for resource cleanup

- **`bark_detector/detector.py`**: Core bark detection algorithm
  - Implements RMS amplitude → dBFS conversion
  - Uses threshold + sustained duration logic (not ML)
  - State machine: tracks consecutive chunks above threshold
  - Cooldown period prevents multiple triggers per bark
  - Debug mode provides real-time visual feedback with 🔴/🟡/🟢 indicators and periodic statistics

- **`bark_detector/mqtt_client.py`**: MQTT publishing with HA integration
  - Paho MQTT client with automatic reconnection + exponential backoff
  - Message queue (deque) during disconnection with overflow handling
  - Home Assistant auto-discovery via special config topic
  - Graceful shutdown with queue flushing

- **`bark_detector/config.py`**: Configuration management
  - Loads from `.env` file using python-dotenv
  - Validates all parameters with range checking
  - Custom exceptions (`ConfigurationError`, `AudioDeviceError`) for clear error handling

### Key Design Patterns

**Audio Pipeline Flow:**
```
USB Mic → sounddevice callback → Queue → Main loop → Detector → MQTT Publisher
```

**Detection Algorithm:**
1. Calculate RMS amplitude from audio chunk
2. Convert to dBFS (digital audio scale: 0 = max, negative = quieter)
3. Track consecutive chunks above threshold
4. Emit `BarkEvent` when sustained duration is met (if not in cooldown)
5. Reset state and start cooldown period

**Configuration Scale (dBFS):**
- Important: Uses dBFS (decibels Full Scale) where 0 is maximum and all real audio is **negative**
- Typical bark range: -10 to -40 dBFS
- Use `--debug` flag to see real-time levels for calibration

### Error Handling & Reliability

- **Retry Logic**: Audio device initialization and MQTT connection both use configurable retry with exponential backoff
- **Graceful Degradation**: Service continues without MQTT if connection fails (logs events only)
- **Resource Cleanup**: Always performed in `finally` blocks and signal handlers
- **Systemd Integration**: Service configured with `Restart=always` for automatic recovery

## Configuration

All configuration via `.env` file. Key parameters:

- **`MICROPHONE_DEVICE_ID`**: USB device ID (e.g., "0d8c:0005" for Blue Snowball)
- **`SAMPLE_RATE`**: Sample rate in Hz (16000, 44100, or 48000 depending on hardware)
- **`BARK_THRESHOLD_DB`**: Detection threshold in dBFS (typically -30 to -40)
- **`MIN_BARK_DURATION_MS`**: Minimum sustained duration to count as bark (100-200ms)
- **`COOLDOWN_PERIOD_MS`**: Cooldown between detections (500ms typical)
- **`MQTT_BROKER`**: MQTT broker hostname/IP (required)
- **`MQTT_USERNAME`/`MQTT_PASSWORD`**: Authentication credentials
- **`LOG_LEVEL`**: DEBUG, INFO, WARNING, or ERROR

## Dependencies

### System-Level (Required)
- **PortAudio**: Required by `sounddevice` library
  - Ubuntu/Debian: `sudo apt-get install portaudio19-dev`
  - Arch Linux: `sudo pacman -S portaudio`
  - macOS: `brew install portaudio`

### Python Packages (in pyproject.toml)
- `sounddevice`: Audio capture from USB devices
- `numpy`: Audio processing (RMS calculations)
- `paho-mqtt`: MQTT client
- `python-dotenv`: Environment configuration

## Troubleshooting

### Common Issues

**OSError: PortAudio library not found**
- Install system PortAudio library (see Dependencies above)
- Restart service after installing

**Service keeps restarting**
- Check logs: `journalctl --user -u bark-detector -n 50`
- Common causes: missing `.env`, MQTT unreachable, audio device not found

**Audio device not found**
- List devices: `uv run python -c "import sounddevice as sd; print(sd.query_devices())"`
- Update `MICROPHONE_DEVICE_ID` in `.env`

**Too sensitive / not sensitive enough**
- Run with `--debug` to see real-time audio levels
- Adjust `BARK_THRESHOLD_DB` (more negative = less sensitive)
- Tune `MIN_BARK_DURATION_MS` (longer = fewer false positives)
