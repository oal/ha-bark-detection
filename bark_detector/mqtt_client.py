"""
MQTT client module for publishing bark detection events.

Handles MQTT connection, reconnection with exponential backoff,
message queueing, and Home Assistant MQTT discovery.
"""

import json
import logging
import time
from typing import Optional, List
from collections import deque
import paho.mqtt.client as mqtt
from bark_detector.detector import BarkEvent


logger = logging.getLogger(__name__)


class MQTTPublisher:
    """
    Publishes bark detection events to MQTT broker.

    Features:
    - Automatic reconnection with exponential backoff
    - Message queueing during disconnection
    - Home Assistant MQTT discovery support
    - Connection status tracking
    """

    def __init__(
        self,
        broker: str,
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: str = "bark_detector",
        topic: str = "homeassistant/sensor/bark_detector/state",
        max_queue_size: int = 100
    ):
        """
        Initialize MQTT publisher.

        Args:
            broker: MQTT broker hostname or IP
            port: MQTT broker port
            username: MQTT username (optional)
            password: MQTT password (optional)
            client_id: MQTT client ID
            topic: MQTT topic for publishing events
            max_queue_size: Maximum number of queued messages
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id
        self.topic = topic
        self.max_queue_size = max_queue_size

        # Connection state
        self.connected = False
        self.client: Optional[mqtt.Client] = None
        self.message_queue: deque = deque(maxlen=max_queue_size)

        # Reconnection parameters
        self.reconnect_delay = 1.0  # Start with 1 second
        self.max_reconnect_delay = 60.0  # Max 60 seconds
        self.reconnect_multiplier = 2.0

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connection is established."""
        if rc == 0:
            self.connected = True
            logger.info(f"✓ Connected to MQTT broker {self.broker}:{self.port}")

            # Reset reconnection delay on successful connection
            self.reconnect_delay = 1.0

            # Publish Home Assistant discovery message
            self._publish_discovery()

            # Publish any queued messages
            self._flush_queue()

        else:
            self.connected = False
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client ID",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error code {rc}")
            logger.error(f"✗ MQTT connection failed: {error_msg}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback when connection is lost."""
        self.connected = False
        if rc == 0:
            logger.info("MQTT client disconnected gracefully")
        else:
            logger.warning(f"MQTT connection lost (code {rc}), will attempt to reconnect")

    def _on_publish(self, client, userdata, mid):
        """Callback when message is published."""
        logger.debug(f"Message {mid} published successfully")

    def _publish_discovery(self):
        """Publish Home Assistant MQTT discovery message."""
        discovery_topic = "homeassistant/sensor/bark_detector/config"

        discovery_payload = {
            "name": "Dog Bark Detector",
            "state_topic": self.topic,
            "device_class": "timestamp",
            "value_template": "{{ value_json.timestamp }}",
            "json_attributes_topic": self.topic,
            "icon": "mdi:dog",
            "unique_id": "bark_detector_01",
            "device": {
                "identifiers": ["bark_detector"],
                "name": "Bark Detector",
                "model": "Decibel Burst Detector",
                "manufacturer": "Custom"
            }
        }

        try:
            result = self.client.publish(
                discovery_topic,
                json.dumps(discovery_payload),
                qos=1,
                retain=True
            )
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✓ Published Home Assistant discovery to {discovery_topic}")
            else:
                logger.warning(f"Failed to publish discovery message (rc={result.rc})")
        except Exception as e:
            logger.error(f"Error publishing discovery message: {e}")

    def _flush_queue(self):
        """Publish all queued messages."""
        if not self.message_queue:
            return

        queue_size = len(self.message_queue)
        logger.info(f"Publishing {queue_size} queued messages...")

        published = 0
        while self.message_queue and self.connected:
            event = self.message_queue.popleft()
            if self._publish_event(event):
                published += 1

        logger.info(f"✓ Published {published}/{queue_size} queued messages")

    def _publish_event(self, event: BarkEvent) -> bool:
        """
        Publish a single bark event.

        Args:
            event: BarkEvent to publish

        Returns:
            True if published successfully, False otherwise
        """
        try:
            payload = json.dumps(event.to_dict())
            result = self.client.publish(self.topic, payload, qos=1)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published event: {payload}")
                return True
            else:
                logger.warning(f"Failed to publish event (rc={result.rc})")
                return False

        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            return False

    def connect(self, retry_count: int = 5) -> bool:
        """
        Connect to MQTT broker with retries.

        Args:
            retry_count: Number of connection attempts

        Returns:
            True if connected successfully, False otherwise
        """
        logger.info(f"Connecting to MQTT broker {self.broker}:{self.port}...")

        # Create MQTT client
        self.client = mqtt.Client(client_id=self.client_id)

        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish

        # Set authentication if provided
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        # Attempt connection with exponential backoff
        for attempt in range(1, retry_count + 1):
            try:
                logger.info(f"Connection attempt {attempt}/{retry_count}...")
                self.client.connect(self.broker, self.port, keepalive=60)

                # Start network loop in separate thread
                self.client.loop_start()

                # Wait for connection callback (with timeout)
                timeout = 5.0
                start_time = time.time()
                while not self.connected and (time.time() - start_time) < timeout:
                    time.sleep(0.1)

                if self.connected:
                    return True

                logger.warning(f"Connection attempt {attempt} timed out")

            except Exception as e:
                logger.error(f"Connection attempt {attempt} failed: {e}")

            # Exponential backoff delay
            if attempt < retry_count:
                delay = min(
                    self.reconnect_delay * (self.reconnect_multiplier ** (attempt - 1)),
                    self.max_reconnect_delay
                )
                logger.info(f"Retrying in {delay:.1f} seconds...")
                time.sleep(delay)

        logger.error(f"Failed to connect after {retry_count} attempts")
        return False

    def publish_bark(self, event: BarkEvent):
        """
        Publish bark detection event.

        If not connected, queues the event for later delivery.

        Args:
            event: BarkEvent to publish
        """
        if self.connected:
            success = self._publish_event(event)
            if not success:
                # Queue for retry if publish failed
                self._queue_event(event)
        else:
            logger.warning("Not connected to MQTT, queueing event")
            self._queue_event(event)

    def _queue_event(self, event: BarkEvent):
        """Add event to queue."""
        if len(self.message_queue) >= self.max_queue_size:
            dropped = self.message_queue.popleft()
            logger.warning(f"Message queue full, dropped oldest event: {dropped.timestamp}")

        self.message_queue.append(event)
        logger.debug(f"Event queued ({len(self.message_queue)}/{self.max_queue_size})")

    def disconnect(self):
        """Disconnect from MQTT broker gracefully."""
        if self.client:
            logger.info("Disconnecting from MQTT broker...")
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("✓ MQTT client disconnected")

    def is_connected(self) -> bool:
        """Check if connected to MQTT broker."""
        return self.connected

    def get_queue_size(self) -> int:
        """Get number of queued messages."""
        return len(self.message_queue)


# Module test functionality
if __name__ == "__main__":
    """Test MQTT publisher functionality."""
    import sys
    from bark_detector.config import Config

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    logger.info("Testing MQTT publisher...")

    try:
        # Load configuration
        config = Config()

        # Create MQTT publisher
        publisher = MQTTPublisher(
            broker=config.mqtt_broker,
            port=config.mqtt_port,
            username=config.mqtt_username,
            password=config.mqtt_password,
            client_id=config.mqtt_client_id,
            topic=config.mqtt_topic
        )

        # Connect to broker
        if not publisher.connect(retry_count=3):
            logger.error("✗ Failed to connect to MQTT broker")
            sys.exit(1)

        # Publish test events
        logger.info("Publishing test bark events...")

        for i in range(3):
            event = BarkEvent(
                timestamp=f"2025-11-20T16:00:{i:02d}.000Z",
                peak_db=65.0 + i * 2.5,
                device="test_detector"
            )
            publisher.publish_bark(event)
            logger.info(f"✓ Published test event {i+1}: {event.peak_db} dB")
            time.sleep(1)

        # Wait a bit for messages to be delivered
        time.sleep(2)

        # Check queue
        queue_size = publisher.get_queue_size()
        if queue_size > 0:
            logger.warning(f"{queue_size} messages still in queue")
        else:
            logger.info("✓ All messages delivered")

        # Disconnect
        publisher.disconnect()

        logger.info("✓ MQTT publisher test completed successfully")
        logger.info("Check your MQTT broker/Home Assistant to verify messages")

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        publisher.disconnect()
        sys.exit(0)

    except Exception as e:
        logger.error(f"✗ MQTT publisher test failed: {e}", exc_info=True)
        sys.exit(1)
