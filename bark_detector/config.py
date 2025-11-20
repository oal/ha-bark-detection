# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Configuration management for bark detection system.

Loads configuration from .env file and validates all parameters.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing required parameters."""
    pass


class Config:
    """Configuration container with validation."""

    def __init__(self):
        """Load and validate configuration from .env file."""
        # Load .env file from project root
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Try current working directory
            load_dotenv()

        # Load and validate all configuration parameters
        self._load_microphone_config()
        self._load_detection_config()
        self._load_mqtt_config()
        self._load_logging_config()

    def _load_microphone_config(self):
        """Load and validate microphone configuration."""
        self.microphone_device_id = os.getenv("MICROPHONE_DEVICE_ID", "0d8c:0005")

        self.sample_rate = self._get_int_env(
            "SAMPLE_RATE",
            default=16000,
            min_val=8000,
            max_val=48000,
            description="sample rate"
        )

    def _load_detection_config(self):
        """Load and validate bark detection parameters."""
        self.bark_threshold_db = self._get_float_env(
            "BARK_THRESHOLD_DB",
            default=-30.0,
            min_val=-60.0,
            max_val=0.0,
            description="bark threshold (dBFS)"
        )

        self.min_bark_duration_ms = self._get_int_env(
            "MIN_BARK_DURATION_MS",
            default=100,
            min_val=10,
            max_val=1000,
            description="minimum bark duration (ms)"
        )

        self.cooldown_period_ms = self._get_int_env(
            "COOLDOWN_PERIOD_MS",
            default=500,
            min_val=100,
            max_val=5000,
            description="cooldown period (ms)"
        )

    def _load_mqtt_config(self):
        """Load and validate MQTT configuration."""
        self.mqtt_broker = self._get_required_env("MQTT_BROKER")

        self.mqtt_port = self._get_int_env(
            "MQTT_PORT",
            default=1883,
            min_val=1,
            max_val=65535,
            description="MQTT port"
        )

        self.mqtt_username = os.getenv("MQTT_USERNAME")
        self.mqtt_password = os.getenv("MQTT_PASSWORD")

        self.mqtt_topic = os.getenv(
            "MQTT_TOPIC",
            "homeassistant/sensor/bark_detector/state"
        )

        self.mqtt_client_id = os.getenv("MQTT_CLIENT_ID", "bark_detector")

    def _load_logging_config(self):
        """Load and validate logging configuration."""
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()

        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if log_level_str not in valid_levels:
            raise ConfigurationError(
                f"Invalid LOG_LEVEL '{log_level_str}'. "
                f"Must be one of: {', '.join(valid_levels)}"
            )

        self.log_level = getattr(logging, log_level_str)

    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise ConfigurationError(
                f"Missing required configuration parameter: {key}\n"
                f"Please set {key} in your .env file"
            )
        return value

    def _get_int_env(
        self,
        key: str,
        default: int,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None,
        description: str = "value"
    ) -> int:
        """Get integer environment variable with validation."""
        value_str = os.getenv(key)

        if value_str is None:
            return default

        try:
            value = int(value_str)
        except ValueError:
            raise ConfigurationError(
                f"Invalid {description}: {key}={value_str}\n"
                f"Expected an integer value"
            )

        if min_val is not None and value < min_val:
            raise ConfigurationError(
                f"Invalid {description}: {key}={value}\n"
                f"Value must be at least {min_val}"
            )

        if max_val is not None and value > max_val:
            raise ConfigurationError(
                f"Invalid {description}: {key}={value}\n"
                f"Value must be at most {max_val}"
            )

        return value

    def _get_float_env(
        self,
        key: str,
        default: float,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        description: str = "value"
    ) -> float:
        """Get float environment variable with validation."""
        value_str = os.getenv(key)

        if value_str is None:
            return default

        try:
            value = float(value_str)
        except ValueError:
            raise ConfigurationError(
                f"Invalid {description}: {key}={value_str}\n"
                f"Expected a numeric value"
            )

        if min_val is not None and value < min_val:
            raise ConfigurationError(
                f"Invalid {description}: {key}={value}\n"
                f"Value must be at least {min_val}"
            )

        if max_val is not None and value > max_val:
            raise ConfigurationError(
                f"Invalid {description}: {key}={value}\n"
                f"Value must be at most {max_val}"
            )

        return value

    def log_config(self, logger: logging.Logger):
        """Log configuration with password masking."""
        logger.info("Configuration loaded:")
        logger.info(f"  Microphone Device ID: {self.microphone_device_id}")
        logger.info(f"  Sample Rate: {self.sample_rate} Hz")
        logger.info(f"  Bark Threshold: {self.bark_threshold_db} dBFS")
        logger.info(f"  Min Bark Duration: {self.min_bark_duration_ms} ms")
        logger.info(f"  Cooldown Period: {self.cooldown_period_ms} ms")
        logger.info(f"  MQTT Broker: {self.mqtt_broker}:{self.mqtt_port}")
        logger.info(f"  MQTT Username: {self.mqtt_username or '(none)'}")
        logger.info(f"  MQTT Password: {'***' if self.mqtt_password else '(none)'}")
        logger.info(f"  MQTT Topic: {self.mqtt_topic}")
        logger.info(f"  MQTT Client ID: {self.mqtt_client_id}")
        logger.info(f"  Log Level: {logging.getLevelName(self.log_level)}")


def load_config() -> Config:
    """
    Load and validate configuration.

    Returns:
        Config: Validated configuration object

    Raises:
        ConfigurationError: If configuration is invalid or missing required parameters
    """
    try:
        return Config()
    except ConfigurationError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)


# Module test functionality
if __name__ == "__main__":
    """Test configuration loading and display."""
    # Setup basic logging for test
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    logger = logging.getLogger(__name__)

    print("Testing configuration loading...")
    print()

    try:
        config = Config()
        print("✓ Configuration loaded successfully")
        print()
        config.log_config(logger)
    except ConfigurationError as e:
        print(f"✗ Configuration failed: {e}")
        sys.exit(1)
