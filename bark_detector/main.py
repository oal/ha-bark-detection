"""
Main entry point for bark detection service.

Integrates audio capture, bark detection, and MQTT publishing
into a complete monitoring service with graceful shutdown support.
"""

import logging
import signal
import sys
import time
from typing import Optional

from bark_detector import __version__
from bark_detector.config import Config, ConfigurationError
from bark_detector.audio import AudioCapture, AudioDeviceError
from bark_detector.detector import BarkDetector
from bark_detector.mqtt_client import MQTTPublisher


# Global flag for shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals (SIGINT, SIGTERM)."""
    global shutdown_requested
    signal_names = {signal.SIGINT: "SIGINT", signal.SIGTERM: "SIGTERM"}
    signal_name = signal_names.get(signum, str(signum))
    logger.info(f"\n{signal_name} received, shutting down gracefully...")
    shutdown_requested = True


def setup_logging(log_level: int):
    """
    Setup logging configuration.

    Args:
        log_level: Logging level (from logging module)
    """
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def main():
    """Main application entry point."""
    global shutdown_requested

    # Load configuration first (before logging setup)
    try:
        config = Config()
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # Setup logging with configured level
    setup_logging(config.log_level)

    global logger
    logger = logging.getLogger(__name__)

    # Display startup banner
    logger.info("=" * 60)
    logger.info(f"Bark Detection Service v{__version__}")
    logger.info("=" * 60)

    # Log configuration
    config.log_config(logger)
    logger.info("=" * 60)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize components
    audio_capture: Optional[AudioCapture] = None
    bark_detector: Optional[BarkDetector] = None
    mqtt_publisher: Optional[MQTTPublisher] = None

    try:
        # Initialize audio capture
        logger.info("Initializing audio capture...")
        audio_capture = AudioCapture(
            device_id=config.microphone_device_id,
            sample_rate=config.sample_rate,
            chunk_size=1024,
            channels=1
        )
        audio_capture.initialize_device()

        # Initialize bark detector
        logger.info("Initializing bark detector...")
        bark_detector = BarkDetector(
            threshold_db=config.bark_threshold_db,
            min_duration_ms=config.min_bark_duration_ms,
            cooldown_ms=config.cooldown_period_ms,
            sample_rate=config.sample_rate,
            chunk_size=1024
        )

        # Initialize MQTT publisher
        logger.info("Initializing MQTT publisher...")
        mqtt_publisher = MQTTPublisher(
            broker=config.mqtt_broker,
            port=config.mqtt_port,
            username=config.mqtt_username,
            password=config.mqtt_password,
            client_id=config.mqtt_client_id,
            topic=config.mqtt_topic
        )

        # Connect to MQTT broker
        if not mqtt_publisher.connect(retry_count=5):
            logger.error("Failed to connect to MQTT broker after multiple attempts")
            logger.warning("Continuing without MQTT (events will be logged only)")
            mqtt_publisher = None

        # Start audio capture
        logger.info("Starting audio capture...")
        audio_capture.start()

        logger.info("=" * 60)
        logger.info("🐕 Bark detection service is running!")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)

        # Main processing loop
        bark_count = 0
        chunk_count = 0
        start_time = time.time()

        while not shutdown_requested:
            # Get audio chunk with timeout
            audio_chunk = audio_capture.get_audio_chunk(timeout=1.0)

            if audio_chunk is None:
                # Timeout - check if we should continue
                if not audio_capture.is_running():
                    logger.error("Audio capture stopped unexpectedly")
                    break
                continue

            chunk_count += 1

            # Process chunk with detector
            bark_event = bark_detector.process_chunk(audio_chunk)

            if bark_event:
                bark_count += 1

                # Publish to MQTT if connected
                if mqtt_publisher and mqtt_publisher.is_connected():
                    mqtt_publisher.publish_bark(bark_event)
                    logger.info(f"Bark #{bark_count} detected and published: "
                              f"{bark_event.peak_db:.1f} dB")
                else:
                    logger.info(f"Bark #{bark_count} detected: "
                              f"{bark_event.peak_db:.1f} dB (MQTT not available)")

        # Shutdown sequence
        logger.info("=" * 60)
        logger.info("Shutting down...")

        # Display statistics
        runtime = time.time() - start_time
        logger.info(f"Statistics:")
        logger.info(f"  Runtime: {runtime:.1f} seconds ({runtime/60:.1f} minutes)")
        logger.info(f"  Audio chunks processed: {chunk_count}")
        logger.info(f"  Barks detected: {bark_count}")
        if bark_count > 0:
            logger.info(f"  Average: {bark_count / (runtime/60):.2f} barks/minute")

        # Stop audio capture
        if audio_capture:
            logger.info("Stopping audio capture...")
            audio_capture.stop()

        # Disconnect MQTT
        if mqtt_publisher:
            queued = mqtt_publisher.get_queue_size()
            if queued > 0:
                logger.info(f"Flushing {queued} queued MQTT messages...")
                time.sleep(2)  # Give time for queue to flush
            mqtt_publisher.disconnect()

        logger.info("=" * 60)
        logger.info("✓ Bark detection service stopped gracefully")
        logger.info("=" * 60)

        return 0

    except AudioDeviceError as e:
        logger.error(f"Audio device error: {e}")
        logger.error("Please check that your microphone is connected and accessible")
        return 1

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 0

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

    finally:
        # Ensure cleanup happens even on errors
        if audio_capture and audio_capture.is_running():
            audio_capture.stop()
        if mqtt_publisher and mqtt_publisher.is_connected():
            mqtt_publisher.disconnect()


if __name__ == "__main__":
    sys.exit(main())
