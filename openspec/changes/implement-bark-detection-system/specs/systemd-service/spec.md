# Systemd Service Capability

## ADDED Requirements

### Requirement: Systemd user service installation
The system SHALL provide a systemd user service for automatic startup and management.

#### Scenario: Install service to user systemd directory
**Given** the project includes an installation script
**When** the user runs `./systemd/install_service.sh`
**Then** the script shall copy `bark-detector.service` to `~/.config/systemd/user/`
**And** run `systemctl --user daemon-reload`
**And** enable the service with `systemctl --user enable bark-detector.service`
**And** start the service with `systemctl --user start bark-detector.service`
**And** report success status to the user
**And** display instructions for checking service status

#### Scenario: Service file uses correct paths and configuration
**Given** the systemd service file `bark-detector.service`
**Then** the service shall set `Type=simple`
**And** set `Restart=always`
**And** set `RestartSec=10`
**And** set `WorkingDirectory` to the project root absolute path
**And** set `ExecStart` to run `python -m bark_detector.main`
**And** set `WantedBy=default.target` for user session startup

#### Scenario: Service starts automatically on user login
**Given** the service is installed and enabled
**When** the user logs into their Linux session
**Then** the systemd user manager shall automatically start the bark-detector service
**And** the service shall begin detecting barks without manual intervention

### Requirement: Service logging integration
The system SHALL integrate with systemd journal for centralized logging.

#### Scenario: Log to stdout for systemd capture
**Given** the service is running under systemd
**When** the application logs a message
**Then** the system shall write to stdout (INFO, DEBUG) or stderr (WARNING, ERROR)
**And** systemd shall capture the output to the journal
**And** users can view logs with `journalctl --user -u bark-detector.service`

#### Scenario: Support log filtering by level
**Given** the service has logged messages at various levels
**When** the user runs `journalctl --user -u bark-detector.service -p warning`
**Then** only WARNING and ERROR messages shall be displayed
**And** INFO and DEBUG messages shall be filtered out

#### Scenario: Include service metadata in log entries
**Given** the service is running under systemd
**When** log entries are written to the journal
**Then** each entry shall include the service name "bark-detector.service"
**And** include the systemd unit name in metadata
**And** include the user ID running the service

### Requirement: Service failure and restart handling
The system SHALL handle failures gracefully with automatic restart.

#### Scenario: Restart service on crash
**Given** the bark-detector service is running
**When** the Python process crashes with an unhandled exception
**Then** systemd shall detect the failure
**And** wait 10 seconds (RestartSec)
**And** automatically restart the service
**And** log the restart event to the journal

#### Scenario: Limit restart rate to prevent tight loops
**Given** the service fails repeatedly
**When** the service has failed 5 times within 30 seconds
**Then** systemd shall apply rate limiting
**And** delay subsequent restarts according to systemd's rate limit policy
**And** log rate limit events to the journal

#### Scenario: Exit with error code on fatal configuration errors
**Given** the service starts with invalid configuration
**When** configuration validation fails
**Then** the application shall exit with code 1
**And** systemd shall log the failure
**And** attempt to restart after the configured delay
**And** the user can diagnose the issue via `journalctl --user -u bark-detector.service`

### Requirement: Standalone execution support
The system SHALL support direct execution without systemd for testing and debugging.

#### Scenario: Run application directly from command line
**Given** the user is in the project root directory
**And** the .env file is present
**When** the user runs `python -m bark_detector.main`
**Then** the application shall start in foreground mode
**And** log all messages to the terminal
**And** respond to Ctrl+C for graceful shutdown
**And** detect barks and publish to MQTT as normal

#### Scenario: Graceful shutdown on SIGINT
**Given** the application is running in foreground mode
**When** the user presses Ctrl+C (SIGINT)
**Then** the application shall catch the signal
**And** log "Shutting down gracefully..."
**And** disconnect from MQTT cleanly
**And** close audio capture
**And** exit with code 0

#### Scenario: Graceful shutdown on SIGTERM
**Given** the application is running as a systemd service
**When** systemd sends SIGTERM (on service stop)
**Then** the application shall catch the signal
**And** perform the same graceful shutdown as SIGINT
**And** exit within 10 seconds
**And** allow systemd to proceed with stopping the service

### Requirement: Service management commands documentation
The system SHALL provide clear documentation for service management.

#### Scenario: README includes service management commands
**Given** the project README.md file
**Then** it shall document installation with `./systemd/install_service.sh`
**And** document starting with `systemctl --user start bark-detector`
**And** document stopping with `systemctl --user stop bark-detector`
**And** document status check with `systemctl --user status bark-detector`
**And** document log viewing with `journalctl --user -u bark-detector -f`
**And** document disabling with `systemctl --user disable bark-detector`
**And** document uninstallation steps

#### Scenario: Installation script provides feedback
**Given** the user runs the installation script
**When** each installation step completes
**Then** the script shall print a success message for that step
**And** print the final status "Service installed and started successfully"
**And** print next steps for the user (check status, view logs)
**And** print troubleshooting tips if any step fails
