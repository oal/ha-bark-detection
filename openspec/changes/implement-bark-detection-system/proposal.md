# Change: Implement Bark Detection System

## Why
Enable automated monitoring of dog barking behavior throughout the day by detecting barking events and reporting them to Home Assistant, providing visibility into pet behavior when away from home.

## What Changes
- Add Python bark detection service with audio capture from Blue Snowball USB microphone (ID 0d8c:0005)
- Add decibel burst detection algorithm (simple threshold-based detection for short, loud sounds)
- Add MQTT client integration publishing bark events to Home Assistant topic
- Add .env configuration management for detection parameters and MQTT settings
- Add systemd user service for continuous operation with automatic restart
- Add standalone execution support for testing and debugging
- Add comprehensive logging and error handling

## Impact
- Affected specs: audio-capture, bark-detection, mqtt-integration, configuration, systemd-service (all new)
- Affected code: New Python package `bark_detector/` with modules for audio, detection, MQTT, config, and main entry point
- External dependencies: sounddevice, numpy, paho-mqtt, python-dotenv
- System requirements: Python 3.8+, USB audio device access, MQTT broker connectivity
- Risk mitigation: Configurable thresholds for false positives, retry logic for MQTT failures, systemd auto-restart for crashes
