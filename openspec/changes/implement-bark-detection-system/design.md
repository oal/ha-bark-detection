# Design: Bark Detection System

## Architecture Overview

```
┌─────────────────┐
│  Blue Snowball  │
│   USB Mic       │
└────────┬────────┘
         │ Audio Input
         ▼
┌─────────────────────────────────────────┐
│  Bark Detection Service (Python)        │
│  ┌────────────────────────────────────┐ │
│  │  Audio Capture (PyAudio/sounddevice)│ │
│  └──────────────┬──────────────────────┘ │
│                 │                         │
│  ┌──────────────▼──────────────────────┐ │
│  │  Decibel Burst Detector              │ │
│  │  - Calculate dB level                │ │
│  │  - Detect threshold crossings        │ │
│  │  - Filter by duration                │ │
│  │  - Cooldown between events           │ │
│  └──────────────┬──────────────────────┘ │
│                 │                         │
│  ┌──────────────▼──────────────────────┐ │
│  │  MQTT Publisher (paho-mqtt)          │ │
│  │  - Connection management             │ │
│  │  - Retry with backoff                │ │
│  │  - Message publishing                │ │
│  └──────────────┬──────────────────────┘ │
│                 │                         │
│  ┌──────────────▼──────────────────────┐ │
│  │  Configuration (.env)                │ │
│  │  Logging (stdout/stderr)             │ │
│  └─────────────────────────────────────┘ │
└──────────────────┬──────────────────────┘
                   │ MQTT Messages
                   ▼
         ┌─────────────────┐
         │  MQTT Broker    │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ Home Assistant  │
         │  MQTT Sensor    │
         └─────────────────┘
```

## Component Design

### 1. Audio Capture Module
**Responsibility**: Capture continuous audio stream from USB microphone

**Library Choice**: `sounddevice` + `numpy`
- **Why**: Simple, Pythonic API with good cross-platform support
- **Alternative considered**: `pyaudio` - more complex, requires PortAudio compilation
- **Configuration**:
  - Sample rate: 16000 Hz (sufficient for bark detection)
  - Channels: 1 (mono)
  - Chunk size: 1024 samples (~64ms chunks at 16kHz)

**Device Selection**:
- Use USB device ID (0d8c:0005) to identify Blue Snowball
- Fallback to default input device with warning log

### 2. Bark Detection Algorithm
**Responsibility**: Analyze audio chunks and detect bark patterns

**Algorithm**: Decibel Burst Detection
```
For each audio chunk:
  1. Calculate RMS (Root Mean Square) amplitude
  2. Convert to decibels: dB = 20 * log10(RMS / reference)
  3. If dB > threshold AND not in cooldown:
     - If sustained for min_duration:
       - Trigger bark detection event
       - Record peak dB level
       - Start cooldown period
```

**Configurable Parameters**:
- `BARK_THRESHOLD_DB`: Minimum dB level to consider (default: 60 dB)
- `MIN_BARK_DURATION_MS`: Minimum sustained duration (default: 100 ms)
- `COOLDOWN_PERIOD_MS`: Time between detections (default: 500 ms)

**Why Simple Detection**:
- Requirements explicitly state "don't need fancy detection"
- Barks are characterized by short, loud bursts
- Fast, low CPU usage, no ML model overhead
- Easy to tune with configurable thresholds

### 3. MQTT Publisher Module
**Responsibility**: Send bark detection events to Home Assistant

**Library**: `paho-mqtt`
- Industry standard MQTT client library
- Built-in reconnection support
- Low overhead

**Connection Strategy**:
- Connect on startup with retry (exponential backoff: 1s, 2s, 4s, 8s, max 60s)
- Keep connection alive with automatic reconnection
- Continue detection even if MQTT is disconnected (log warnings)
- Queue messages during disconnection (max queue size: 100)

**Message Format**:
```json
{
  "timestamp": "2025-11-20T15:30:45.123Z",
  "peak_db": 72.5,
  "device": "bark_detector"
}
```

**MQTT Topic**: `homeassistant/sensor/bark_detector/state`
- Compatible with Home Assistant MQTT discovery
- State updates on each bark event

**Home Assistant Discovery**:
Send discovery message on startup to register sensor:
```json
Topic: homeassistant/sensor/bark_detector/config
Payload: {
  "name": "Dog Bark Detector",
  "state_topic": "homeassistant/sensor/bark_detector/state",
  "unit_of_measurement": "events",
  "value_template": "{{ value_json.timestamp }}",
  "json_attributes_topic": "homeassistant/sensor/bark_detector/state"
}
```

### 4. Configuration Management
**Responsibility**: Load and validate configuration from .env file

**Library**: `python-dotenv`

**Configuration Parameters**:
```bash
# Microphone
MICROPHONE_DEVICE_ID=0d8c:0005
SAMPLE_RATE=16000

# Bark Detection
BARK_THRESHOLD_DB=60
MIN_BARK_DURATION_MS=100
COOLDOWN_PERIOD_MS=500

# MQTT
MQTT_BROKER=homeassistant.local
MQTT_PORT=1883
MQTT_USERNAME=bark_detector
MQTT_PASSWORD=secretpassword
MQTT_TOPIC=homeassistant/sensor/bark_detector/state
MQTT_CLIENT_ID=bark_detector

# Logging
LOG_LEVEL=INFO
```

**Validation**:
- Required parameters must be present
- Numeric values validated for reasonable ranges
- MQTT connection tested on startup

### 5. Systemd Integration
**Responsibility**: Run as user service with automatic restart

**Service Configuration**:
- Type: `simple` (foreground process)
- Restart: `always` with 10-second delay
- User service installation (`~/.config/systemd/user/`)
- Start on boot: `WantedBy=default.target`

**Installation Script**:
Provide `install_service.sh` that:
1. Copies service file to `~/.config/systemd/user/`
2. Runs `systemctl --user daemon-reload`
3. Enables service with `systemctl --user enable`
4. Starts service with `systemctl --user start`

## File Structure

```
ha-bark-detection/
├── bark_detector/
│   ├── __init__.py
│   ├── audio.py           # Audio capture
│   ├── detector.py        # Bark detection algorithm
│   ├── mqtt_client.py     # MQTT publisher
│   ├── config.py          # Configuration loader
│   └── main.py            # Entry point
├── systemd/
│   ├── bark-detector.service
│   └── install_service.sh
├── .env.example           # Example configuration
├── requirements.txt       # Python dependencies
├── README.md             # Setup and usage instructions
└── openspec/
    └── ...
```

## Error Handling Strategy

### Fatal Errors (Exit with error code):
- Missing required configuration parameters
- Unable to initialize audio device after retries
- Python dependencies not installed

### Recoverable Errors (Log and continue):
- MQTT connection failures (retry with backoff)
- Temporary audio buffer overruns (log warning)
- Invalid audio chunks (skip and continue)

### Logging Strategy:
- INFO: Service start/stop, MQTT connection status, bark detections
- WARNING: MQTT disconnections, audio warnings
- ERROR: Configuration errors, audio initialization failures
- DEBUG: Per-chunk dB levels, detection algorithm details

## Testing Considerations

### Manual Testing:
- Run `python -m bark_detector.main` directly
- Generate test sounds (claps, barks) near microphone
- Verify MQTT messages arrive in Home Assistant
- Test with MQTT broker disconnected
- Test microphone disconnection/reconnection

### Unit Testing (Future):
- Mock audio input for detector tests
- Mock MQTT client for publisher tests
- Configuration validation tests

## Performance Considerations

### CPU Usage:
- Estimated: <5% on modern CPU
- Audio processing: ~1-2%
- MQTT: <1%
- Most time spent sleeping/waiting for audio chunks

### Memory Usage:
- Estimated: <50 MB RSS
- Audio buffer: ~1 MB
- MQTT queue: <1 MB
- Python runtime: ~30-40 MB

### Latency:
- Detection latency: ~100-200ms (chunk size + processing)
- MQTT publish: <10ms (local network)
- Total: <250ms from bark to HA notification

## Security Considerations

- MQTT credentials stored in .env (file permissions: 600)
- No audio recording or storage (privacy-friendly)
- User-level service (no root privileges required)
- No external network access except MQTT broker

## Future Enhancement Opportunities

1. **ML-based Detection**: Train model to distinguish bark from other sounds
2. **Multiple Microphones**: Support array of microphones for location detection
3. **Web Dashboard**: Real-time monitoring and statistics
4. **Audio Recording**: Optional short clips for verification
5. **Smart Triggers**: Integration with HA automations (lights, notifications)
6. **Bark Classification**: Differentiate aggressive vs. playful barks
