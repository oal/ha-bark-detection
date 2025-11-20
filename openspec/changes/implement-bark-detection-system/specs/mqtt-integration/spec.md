# MQTT Integration Capability

## ADDED Requirements

### Requirement: MQTT message publishing on bark detection
The system SHALL publish bark detection events to an MQTT broker for Home Assistant integration.

#### Scenario: Publish bark event to Home Assistant topic
**Given** a bark has been detected at timestamp "2025-11-20T15:30:45.123Z" with peak level 72.5 dB
**And** the MQTT client is connected to the broker
**When** the bark event is published
**Then** the system shall publish to topic "homeassistant/sensor/bark_detector/state"
**And** the message payload shall be valid JSON
**And** the payload shall contain field "timestamp" with value "2025-11-20T15:30:45.123Z"
**And** the payload shall contain field "peak_db" with value 72.5
**And** the payload shall contain field "device" with value "bark_detector"
**And** log the published message at INFO level

#### Scenario: Use configured MQTT topic
**Given** the .env file contains `MQTT_TOPIC=custom/bark/events`
**When** a bark event is published
**Then** the system shall publish to topic "custom/bark/events"
**And** log the topic being used at startup

### Requirement: MQTT connection management with retry logic
The system SHALL establish and maintain MQTT connection with automatic reconnection.

#### Scenario: Connect to MQTT broker on startup
**Given** the bark detection service starts
**And** MQTT broker is configured as "homeassistant.local:1883"
**And** credentials are provided in configuration
**When** the MQTT client initializes
**Then** the system shall attempt to connect to the broker
**And** authenticate using the configured username and password
**And** log "MQTT connected successfully" at INFO level when connected
**And** set a unique client ID from configuration or generate one

#### Scenario: Retry connection with exponential backoff on failure
**Given** the MQTT broker is unreachable
**When** initial connection fails
**Then** the system shall wait 1 second and retry
**And** wait 2 seconds before the second retry
**And** wait 4 seconds before the third retry
**And** wait 8 seconds before the fourth retry
**And** cap maximum retry delay at 60 seconds
**And** log each connection attempt with the delay at WARNING level
**And** continue retrying indefinitely until connected

#### Scenario: Continue bark detection during MQTT disconnection
**Given** the bark detector is running
**And** the MQTT connection is lost
**When** a bark is detected
**Then** the system shall log the bark locally at INFO level
**And** queue the message for later delivery (up to 100 messages)
**And** log a warning that MQTT is disconnected
**And** continue detecting barks without interruption

#### Scenario: Publish queued messages after reconnection
**Given** the MQTT connection was lost
**And** 5 bark events were queued during disconnection
**When** the MQTT connection is restored
**Then** the system shall publish all 5 queued messages in order
**And** log "Published queued messages" at INFO level
**And** clear the message queue

#### Scenario: Discard old messages when queue is full
**Given** the MQTT connection is lost
**And** the message queue contains 100 messages (at capacity)
**When** a new bark is detected
**Then** the system shall remove the oldest message from the queue
**And** add the new message to the queue
**And** log a warning that old messages are being discarded

### Requirement: Home Assistant MQTT Discovery
The system SHALL register itself with Home Assistant using MQTT discovery protocol.

#### Scenario: Publish discovery message on startup
**Given** the MQTT client has connected successfully
**When** the service completes initialization
**Then** the system shall publish a discovery message to "homeassistant/sensor/bark_detector/config"
**And** the discovery payload shall include "name": "Dog Bark Detector"
**And** include "state_topic": "homeassistant/sensor/bark_detector/state"
**And** include "unit_of_measurement": "events"
**And** include "value_template": "{{ value_json.timestamp }}"
**And** include "json_attributes_topic": "homeassistant/sensor/bark_detector/state"
**And** set the retain flag to true for the discovery message
**And** log "Published Home Assistant discovery message" at INFO level

#### Scenario: Re-publish discovery message after reconnection
**Given** the MQTT connection was lost and has reconnected
**When** connection is restored
**Then** the system shall re-publish the discovery message
**And** log "Re-published discovery message after reconnect" at INFO level

### Requirement: MQTT configuration validation
The system SHALL validate MQTT configuration before attempting connection.

#### Scenario: Validate required MQTT parameters
**Given** the service is starting
**When** loading MQTT configuration
**Then** the system shall verify `MQTT_BROKER` is present and non-empty
**And** verify `MQTT_PORT` is a valid port number (1-65535)
**And** verify `MQTT_USERNAME` is present if authentication is required
**And** verify `MQTT_PASSWORD` is present if authentication is required
**And** exit with error if any required parameter is missing or invalid

#### Scenario: Use default port when not specified
**Given** the .env file does not contain `MQTT_PORT`
**When** loading MQTT configuration
**Then** the system shall use default port 1883
**And** log "Using default MQTT port 1883" at INFO level

#### Scenario: Generate client ID when not configured
**Given** the .env file does not contain `MQTT_CLIENT_ID`
**When** the MQTT client initializes
**Then** the system shall generate a unique client ID as "bark_detector_{hostname}_{timestamp}"
**And** log the generated client ID at INFO level
