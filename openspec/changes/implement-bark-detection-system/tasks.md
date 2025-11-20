# Implementation Tasks

## Task List

### 1. Project Structure and Configuration Setup
**Deliverable**: Basic project structure with configuration management

- [x] Create project directory structure (`bark_detector/` package)
- [x] Create `requirements.txt` with dependencies (sounddevice, numpy, paho-mqtt, python-dotenv)
- [x] Create `.env.example` with all configuration parameters and documentation
- [x] Create `bark_detector/__init__.py` package file
- [x] Create `bark_detector/config.py` module for configuration loading and validation
- [x] Implement configuration loading from .env file with python-dotenv
- [x] Implement parameter validation (required fields, numeric ranges, format checks)
- [x] Implement configuration logging with password masking
- [x] Test configuration loading with valid and invalid .env files

**Validation**:
- Running `python -m bark_detector.config` displays loaded config with masked passwords
- Invalid configuration produces clear error messages
- Missing required parameters fail with helpful error

**Dependencies**: None (can start immediately)

---

### 2. Audio Capture Module Implementation
**Deliverable**: Working audio capture from USB microphone

- [x] Create `bark_detector/audio.py` module
- [x] Implement audio device enumeration using sounddevice
- [x] Implement Blue Snowball device detection by USB ID (0d8c:0005)
- [x] Implement fallback to default device with warning
- [x] Implement continuous audio capture at 44100 Hz, mono, 1024 sample chunks
- [x] Implement audio stream callback for processing chunks
- [x] Implement error handling for buffer overruns (log and continue)
- [x] Implement device disconnection detection and retry logic
- [x] Add logging for device selection and capture status
- [x] Create test script to verify audio capture works

**Validation**:
- List audio devices and identify Blue Snowball
- Capture audio continuously for 1 minute without crashes
- Verify graceful handling of device disconnect/reconnect
- Test with missing device produces appropriate error

**Dependencies**: Task 1 (needs configuration for sample rate, device ID)

---

### 3. Bark Detection Algorithm Implementation
**Deliverable**: Working bark detection with configurable parameters

- [x] Create `bark_detector/detector.py` module
- [x] Implement RMS amplitude calculation from audio samples
- [x] Implement dB conversion: `20 * log10(RMS / reference)`
- [x] Implement threshold detection with configurable dB level
- [x] Implement minimum duration check (sustained sound requirement)
- [x] Implement cooldown period tracking between detections
- [x] Implement peak dB level tracking during detection window
- [x] Add detailed logging (INFO for detections, DEBUG for per-chunk levels)
- [x] Create BarkEvent data class with timestamp and peak_db fields
- [x] Test detection with recorded audio or live test sounds

**Validation**:
- Clapping or making loud sounds triggers detections
- Brief noises under min_duration are ignored
- Cooldown period prevents rapid repeat detections
- Logged dB levels match expected ranges (40-80 dB typical)
- Adjusting threshold in .env changes detection sensitivity

**Dependencies**: Task 2 (needs audio chunks as input)

---

### 4. MQTT Client Integration
**Deliverable**: MQTT publishing with retry and Home Assistant discovery

- [x] Create `bark_detector/mqtt_client.py` module
- [x] Implement MQTT client initialization with paho-mqtt
- [x] Implement connection with username/password authentication
- [x] Implement exponential backoff retry (1s, 2s, 4s, 8s, max 60s)
- [x] Implement connection status callback logging
- [x] Implement message publishing to configured topic
- [x] Implement message queue (max 100) for disconnection periods
- [x] Implement queued message publishing on reconnection
- [x] Format bark events as JSON with timestamp, peak_db, device fields
- [x] Implement Home Assistant MQTT discovery message publishing
- [x] Add graceful disconnect on shutdown
- [x] Test MQTT with mosquitto_sub or Home Assistant

**Validation**:
- Connect to MQTT broker successfully
- Publish test message appears in mosquitto_sub
- Disconnect broker, verify retry with backoff
- Reconnect broker, verify queued messages are published
- Home Assistant auto-discovers sensor entity
- Published JSON payload is valid and contains expected fields

**Dependencies**: Task 3 (needs bark events to publish)

---

### 5. Main Application Loop and Signal Handling
**Deliverable**: Complete application with graceful shutdown

- [x] Create `bark_detector/main.py` entry point
- [x] Initialize configuration loader
- [x] Initialize audio capture module
- [x] Initialize bark detector
- [x] Initialize MQTT client
- [x] Create main loop that processes audio chunks and detects barks
- [x] Wire detector output to MQTT publisher
- [x] Implement signal handlers for SIGINT (Ctrl+C) and SIGTERM
- [x] Implement graceful shutdown sequence (stop audio, disconnect MQTT, cleanup)
- [x] Add startup logging with version and configuration summary
- [x] Add error handling for fatal startup errors
- [x] Test standalone execution with `python -m bark_detector.main`

**Validation**:
- Start service, verify all modules initialize
- Detect bark, verify MQTT message published to Home Assistant
- Press Ctrl+C, verify graceful shutdown logs
- Check Home Assistant shows bark sensor with data
- Test with invalid config produces helpful error and exits

**Dependencies**: Tasks 1-4 (integrates all components)

---

### 6. Systemd Service Configuration
**Deliverable**: User systemd service for automatic startup

- [x] Create `systemd/` directory
- [x] Create `systemd/bark-detector.service` file
- [x] Configure service type, restart policy, working directory, exec start
- [x] Set appropriate environment variables in service file if needed
- [x] Create `systemd/install_service.sh` installation script
- [x] Implement service file copy to `~/.config/systemd/user/`
- [x] Implement daemon-reload, enable, and start commands
- [x] Add success/failure reporting to installation script
- [x] Test installation script on clean system
- [x] Verify service starts automatically on login
- [x] Test service restart after crash

**Validation**:
- Run install script, verify service starts
- Check `systemctl --user status bark-detector` shows active
- View logs with `journalctl --user -u bark-detector -f`
- Reboot system, verify service starts on login
- Kill service process, verify systemd restarts it

**Dependencies**: Task 5 (needs working application)

---

### 7. Documentation and Testing
**Deliverable**: Complete README and testing guide

- [x] Create comprehensive `README.md` with project overview
- [x] Document hardware requirements (Blue Snowball microphone)
- [x] Document software requirements (Python 3.8+, systemd, MQTT broker)
- [x] Document installation steps (dependencies, .env setup, service install)
- [x] Document configuration parameters in detail
- [x] Document service management commands
- [x] Document troubleshooting common issues
- [x] Document testing procedure for verifying detection
- [x] Add example Home Assistant automation using bark sensor
- [x] Create manual testing checklist
- [x] Test complete installation flow on fresh system
- [x] Test integration with Home Assistant

**Validation**:
- Follow README on fresh system to complete installation
- All configuration parameters are documented
- Troubleshooting section covers common issues
- Testing section enables verification of detection

**Dependencies**: Tasks 5-6 (needs complete application)

---

### 8. Final Integration Testing and Polish
**Deliverable**: Production-ready bark detection system

- [x] Test complete workflow: install → configure → detect → verify in HA
- [x] Test with various threshold values to find good defaults
- [x] Test multi-hour operation for stability
- [x] Verify log levels are appropriate (not too verbose, not too quiet)
- [x] Test error scenarios: no microphone, no MQTT, invalid config
- [x] Verify systemd service restart behavior
- [x] Test graceful shutdown during active detection
- [x] Optimize any performance issues
- [x] Add any missing error messages or logging
- [x] Final code review and cleanup
- [x] Update .env.example with tuned default values

**Validation**:
- System runs continuously for 24 hours without issues
- All error scenarios produce helpful messages
- Home Assistant shows accurate bark detection data
- Service restarts automatically after crashes
- Documentation covers all features

**Dependencies**: Task 7 (final validation of complete system)

---

## Implementation Notes

### Parallelization Opportunities
- Tasks 1-2 can partially overlap (config module can be tested independently)
- Task 7 (documentation) can be started early and updated as implementation progresses

### Critical Path
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

The tasks are mostly sequential as each builds on the previous, but documentation (Task 7) can be drafted in parallel with implementation.

### Testing Strategy
Each task includes specific validation steps. Integration testing happens in Tasks 5 and 8. Manual testing is required throughout since this involves hardware (microphone) and external services (MQTT/Home Assistant).

### Risk Mitigation
- **Microphone compatibility**: Test early with actual Blue Snowball (Task 2)
- **Detection accuracy**: Iterate on parameters in Task 3 before integration
- **MQTT reliability**: Test network failure scenarios thoroughly in Task 4
- **Systemd complexity**: Test service installation on clean user account (Task 6)
