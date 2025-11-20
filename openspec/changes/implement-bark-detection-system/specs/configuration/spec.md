# Configuration Management Capability

## ADDED Requirements

### Requirement: Load configuration from .env file
The system SHALL read all configuration parameters from a .env file in the project root.

#### Scenario: Load configuration from .env file
**Given** a .env file exists in the project root directory
**And** the file contains configuration parameters
**When** the service starts
**Then** the system shall load all parameters from the .env file
**And** log "Configuration loaded from .env" at INFO level

#### Scenario: Use .env file from current directory when running standalone
**Given** the service is run directly with `python -m bark_detector.main`
**And** a .env file exists in the current working directory
**When** the service starts
**Then** the system shall load configuration from that .env file
**And** log the path to the loaded .env file

#### Scenario: Fail with clear error when .env file is missing
**Given** no .env file exists in the expected location
**When** the service starts
**Then** the system shall log an error "Configuration file .env not found"
**And** provide instructions to copy .env.example to .env
**And** exit with exit code 1

### Requirement: Provide example configuration file
The system SHALL include a documented example configuration file.

#### Scenario: Include .env.example with all parameters
**Given** the project repository
**Then** a .env.example file shall be present in the root directory
**And** include all configurable parameters with example values
**And** include comments explaining each parameter
**And** include information about required vs optional parameters
**And** include valid default values that work for typical setups

### Requirement: Validate configuration parameters
The system SHALL validate all configuration parameters and provide clear error messages for invalid values.

#### Scenario: Validate numeric parameter ranges
**Given** the .env file contains `BARK_THRESHOLD_DB=150`
**When** loading configuration
**Then** the system shall log a warning "BARK_THRESHOLD_DB value 150 is unusually high, expected range 40-100"
**And** continue with the configured value (allow override despite warning)

#### Scenario: Reject invalid numeric formats
**Given** the .env file contains `MQTT_PORT=not_a_number`
**When** loading configuration
**Then** the system shall log an error "Invalid MQTT_PORT: must be a number between 1 and 65535"
**And** exit with exit code 1

#### Scenario: Validate required parameters are present
**Given** the .env file is missing `MQTT_BROKER`
**When** loading configuration
**Then** the system shall log an error "Required parameter MQTT_BROKER is not set"
**And** exit with exit code 1

### Requirement: Log active configuration at startup
The system SHALL log the active configuration at startup for troubleshooting.

#### Scenario: Log active configuration on startup
**Given** the service has loaded configuration successfully
**When** initialization completes
**Then** the system shall log all active configuration parameters at INFO level
**And** mask sensitive values (passwords, tokens) showing only "***"
**And** include both configured values and applied defaults
**And** format as "Configuration: PARAM_NAME=value"

#### Scenario: Mask sensitive configuration in logs
**Given** the configuration includes `MQTT_PASSWORD=secret123`
**When** logging the active configuration
**Then** the log entry shall show "MQTT_PASSWORD=***"
**And** not expose the actual password value

### Requirement: Configuration changes require restart
The system SHALL require service restart to apply configuration changes.

#### Scenario: Configuration changes require restart
**Given** the service is running with current configuration
**When** the .env file is modified
**Then** the system shall continue using the old configuration
**And** not automatically reload the configuration
**And** require a service restart to apply changes
**And** log a note at startup "Configuration changes require service restart"

### Requirement: Environment variable override support
The system SHALL allow environment variables to override .env file values.

#### Scenario: Override .env parameter with environment variable
**Given** the .env file contains `MQTT_BROKER=localhost`
**And** the environment variable `MQTT_BROKER=homeassistant.local` is set
**When** the service starts
**Then** the system shall use "homeassistant.local" as the MQTT broker
**And** log "MQTT_BROKER overridden by environment variable"

#### Scenario: Environment variables take precedence over .env
**Given** both .env file and environment variables provide the same parameter
**When** loading configuration
**Then** the system shall use the environment variable value
**And** log which parameters were overridden at DEBUG level
