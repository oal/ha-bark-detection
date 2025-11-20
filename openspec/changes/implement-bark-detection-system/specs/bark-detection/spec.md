# Bark Detection Capability

## ADDED Requirements

### Requirement: Decibel burst detection algorithm
The system SHALL detect barking using a simple decibel-based burst detection algorithm.

#### Scenario: Detect bark when audio exceeds threshold
**Given** audio capture is active
**And** the bark threshold is configured to 60 dB
**And** the minimum bark duration is 100 ms
**When** an audio signal exceeds 60 dB for at least 100 ms
**Then** the system shall trigger a bark detection event
**And** record the peak decibel level during the event
**And** record the timestamp of the detection
**And** log the detection at INFO level with timestamp and peak dB

#### Scenario: Ignore brief noise spikes below minimum duration
**Given** audio capture is active
**And** the minimum bark duration is configured to 100 ms
**When** an audio signal exceeds the threshold for only 50 ms
**Then** the system shall not trigger a bark detection event
**And** continue monitoring without logging the spike

#### Scenario: Apply cooldown period between detections
**Given** a bark has just been detected
**And** the cooldown period is configured to 500 ms
**When** another loud sound occurs within 500 ms
**Then** the system shall not trigger a second bark detection event
**And** wait until the cooldown period expires before detecting again

#### Scenario: Correctly calculate decibel level from audio samples
**Given** an audio chunk is captured
**When** calculating the decibel level
**Then** the system shall calculate RMS (Root Mean Square) amplitude from samples
**And** convert to decibels using the formula: dB = 20 * log10(RMS / reference)
**And** use a reference value of 1.0 for normalized audio

### Requirement: Configurable detection parameters
The system SHALL allow tuning of detection sensitivity through configuration parameters.

#### Scenario: Load bark threshold from configuration
**Given** the .env file contains `BARK_THRESHOLD_DB=65`
**When** the bark detector initializes
**Then** the system shall use 65 dB as the detection threshold
**And** log the configured threshold at startup

#### Scenario: Load minimum duration from configuration
**Given** the .env file contains `MIN_BARK_DURATION_MS=150`
**When** the bark detector initializes
**Then** the system shall require 150 ms sustained sound for detection
**And** log the configured minimum duration at startup

#### Scenario: Load cooldown period from configuration
**Given** the .env file contains `COOLDOWN_PERIOD_MS=1000`
**When** the bark detector initializes
**Then** the system shall wait 1000 ms between detections
**And** log the configured cooldown period at startup

#### Scenario: Use default values when parameters are not configured
**Given** the .env file does not contain bark detection parameters
**When** the bark detector initializes
**Then** the system shall use default threshold of 60 dB
**And** use default minimum duration of 100 ms
**And** use default cooldown period of 500 ms
**And** log that default values are being used

### Requirement: Detection accuracy logging
The system SHALL log detection metrics to enable tuning and troubleshooting.

#### Scenario: Log detailed detection information
**Given** a bark is detected
**When** the detection event is logged
**Then** the log entry shall include the ISO 8601 timestamp
**And** include the peak decibel level rounded to 1 decimal place
**And** include the duration the sound exceeded the threshold
**And** use INFO log level for successful detections

#### Scenario: Log debug information for fine-tuning
**Given** the log level is set to DEBUG
**When** processing each audio chunk
**Then** the system shall log the current decibel level
**And** log whether the level exceeds the threshold
**And** log the remaining cooldown time if in cooldown period
