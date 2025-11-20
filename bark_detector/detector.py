"""
Bark detection algorithm module.

Implements decibel burst detection for identifying barking events
using RMS amplitude analysis and threshold-based detection.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class BarkEvent:
    """
    Represents a detected bark event.

    Attributes:
        timestamp: ISO 8601 formatted timestamp of detection
        peak_db: Peak decibel level during the event
        device: Device identifier (for MQTT payload)
    """
    timestamp: str
    peak_db: float
    device: str = "bark_detector"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "peak_db": round(self.peak_db, 1),
            "device": self.device
        }


class BarkDetector:
    """
    Detects barking using decibel burst analysis.

    Analyzes audio chunks and identifies barking patterns based on:
    - Decibel threshold crossing
    - Minimum sustained duration
    - Cooldown period between detections
    """

    def __init__(
        self,
        threshold_db: float = 60.0,
        min_duration_ms: int = 100,
        cooldown_ms: int = 500,
        sample_rate: int = 44100,
        chunk_size: int = 1024,
        debug_mode: bool = False
    ):
        """
        Initialize bark detector.

        Args:
            threshold_db: Minimum dB level to trigger detection
            min_duration_ms: Minimum sustained duration for valid bark
            cooldown_ms: Cooldown period between detections
            sample_rate: Audio sample rate in Hz
            chunk_size: Number of samples per chunk
            debug_mode: Enable detailed debug logging and statistics
        """
        self.threshold_db = threshold_db
        self.min_duration_ms = min_duration_ms
        self.cooldown_ms = cooldown_ms
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.debug_mode = debug_mode

        # Calculate derived parameters
        self.chunk_duration_ms = (chunk_size / sample_rate) * 1000
        self.min_duration_chunks = max(1, int(min_duration_ms / self.chunk_duration_ms))

        # Detection state
        self.last_detection_time: Optional[float] = None
        self.above_threshold_count = 0
        self.current_peak_db: Optional[float] = None

        # Debug statistics tracking
        self.stats_min_db: Optional[float] = None
        self.stats_max_db: Optional[float] = None
        self.stats_sum_db: float = 0.0
        self.stats_count: int = 0
        self.last_stats_time: float = time.time()
        self.stats_interval_sec: float = 10.0  # Report stats every 10 seconds

        logger.info(f"Bark detector initialized:")
        logger.info(f"  Threshold: {threshold_db} dBFS")
        logger.info(f"  Min duration: {min_duration_ms} ms "
                   f"({self.min_duration_chunks} chunks)")
        logger.info(f"  Cooldown: {cooldown_ms} ms")
        logger.info(f"  Chunk duration: {self.chunk_duration_ms:.1f} ms")
        if debug_mode:
            logger.info(f"  Debug mode: ENABLED (stats every {self.stats_interval_sec:.0f}s)")

        # Add helpful note about dBFS scale
        if threshold_db >= 0:
            logger.warning(f"⚠️  Threshold is {threshold_db} dBFS (positive value)")
            logger.warning(f"    Digital audio uses dBFS: 0 = maximum, negative = quieter")
            logger.warning(f"    Typical barks are -10 to -40 dBFS. Use negative values!")

    def _calculate_db(self, audio_chunk: np.ndarray) -> float:
        """
        Calculate decibel level from audio chunk.

        Args:
            audio_chunk: Audio samples as numpy array

        Returns:
            Decibel level (dB)
        """
        # Calculate RMS (Root Mean Square) amplitude
        rms = np.sqrt(np.mean(audio_chunk ** 2))

        # Convert to decibels (reference = 1.0 for normalized audio)
        # Add small epsilon to avoid log(0)
        db = 20 * np.log10(rms + 1e-10)

        return db

    def _is_in_cooldown(self) -> bool:
        """
        Check if detector is in cooldown period.

        Returns:
            True if in cooldown, False otherwise
        """
        if self.last_detection_time is None:
            return False

        elapsed_ms = (time.time() - self.last_detection_time) * 1000
        return elapsed_ms < self.cooldown_ms

    def _update_statistics(self, db: float):
        """
        Update debug statistics and report periodically.

        Args:
            db: Current decibel level
        """
        if not self.debug_mode:
            return

        # Update statistics
        if self.stats_min_db is None or db < self.stats_min_db:
            self.stats_min_db = db
        if self.stats_max_db is None or db > self.stats_max_db:
            self.stats_max_db = db
        self.stats_sum_db += db
        self.stats_count += 1

        # Check if it's time to report statistics
        current_time = time.time()
        elapsed_sec = current_time - self.last_stats_time

        if elapsed_sec >= self.stats_interval_sec:
            avg_db = self.stats_sum_db / self.stats_count if self.stats_count > 0 else 0
            logger.info(f"📊 Stats (last {elapsed_sec:.1f}s): "
                       f"Min={self.stats_min_db:.1f}dBFS, "
                       f"Max={self.stats_max_db:.1f}dBFS, "
                       f"Avg={avg_db:.1f}dBFS, "
                       f"Samples={self.stats_count}")

            # Reset statistics for next interval
            self.stats_min_db = None
            self.stats_max_db = None
            self.stats_sum_db = 0.0
            self.stats_count = 0
            self.last_stats_time = current_time

    def process_chunk(self, audio_chunk: np.ndarray) -> Optional[BarkEvent]:
        """
        Process audio chunk and detect bark events.

        Args:
            audio_chunk: Audio samples as numpy array

        Returns:
            BarkEvent if bark detected, None otherwise
        """
        # Calculate decibel level
        db = self._calculate_db(audio_chunk)

        # Update statistics if in debug mode
        self._update_statistics(db)

        # Debug mode: real-time dB output with visual indicator
        if self.debug_mode:
            # Calculate how close to threshold (for visual indicator)
            diff_from_threshold = db - self.threshold_db

            # Create visual indicator
            if db > self.threshold_db:
                indicator = "🔴"  # Above threshold
                status = f"+{diff_from_threshold:.1f}dB"
            elif diff_from_threshold > -10:
                indicator = "🟡"  # Close to threshold (within 10 dB)
                status = f"{diff_from_threshold:.1f}dB"
            else:
                indicator = "🟢"  # Well below threshold
                status = f"{diff_from_threshold:.1f}dB"

            logger.info(f"{indicator} {db:.1f}dBFS [{status}] | "
                       f"Threshold: {self.threshold_db}dBFS | "
                       f"Count: {self.above_threshold_count}")

        logger.debug(f"Chunk dB: {db:.1f}, Threshold: {self.threshold_db}, "
                    f"Above count: {self.above_threshold_count}")

        # Check if above threshold
        if db > self.threshold_db:
            # Track peak level
            if self.current_peak_db is None or db > self.current_peak_db:
                self.current_peak_db = db

            # Increment sustained count
            self.above_threshold_count += 1

            # Check if sustained for minimum duration and not in cooldown
            if (self.above_threshold_count >= self.min_duration_chunks and
                not self._is_in_cooldown()):

                # Bark detected!
                event = BarkEvent(
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    peak_db=self.current_peak_db
                )

                logger.info(f"🐕 Bark detected! Peak: {self.current_peak_db:.1f} dBFS, "
                          f"Duration: {self.above_threshold_count} chunks "
                          f"({self.above_threshold_count * self.chunk_duration_ms:.0f} ms)")

                # Reset state and start cooldown
                self.last_detection_time = time.time()
                self.above_threshold_count = 0
                self.current_peak_db = None

                return event

        else:
            # Below threshold - reset counter
            if self.above_threshold_count > 0:
                # Log failed detection attempts in debug mode
                if self.debug_mode:
                    duration_ms = self.above_threshold_count * self.chunk_duration_ms
                    required_ms = self.min_duration_chunks * self.chunk_duration_ms
                    logger.info(f"⚠️  Detection attempt failed: "
                              f"Peak={self.current_peak_db:.1f}dBFS, "
                              f"Duration={duration_ms:.0f}ms "
                              f"(required: {required_ms:.0f}ms, "
                              f"short by {required_ms - duration_ms:.0f}ms)")
                logger.debug(f"Sound dropped below threshold after "
                           f"{self.above_threshold_count} chunks")
            self.above_threshold_count = 0
            self.current_peak_db = None

        return None

    def reset(self):
        """Reset detector state."""
        self.last_detection_time = None
        self.above_threshold_count = 0
        self.current_peak_db = None
        logger.info("Detector state reset")


# Module test functionality
if __name__ == "__main__":
    """Test bark detection with live audio."""
    import sys
    from bark_detector.config import Config
    from bark_detector.audio import AudioCapture

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    logger.info("Testing bark detection...")
    logger.info("Make loud sounds near the microphone to trigger detection")
    logger.info("Press Ctrl+C to stop")

    try:
        # Load configuration
        config = Config()

        # Create audio capture
        capture = AudioCapture(
            device_id=config.microphone_device_id,
            sample_rate=config.sample_rate,
            chunk_size=1024
        )

        # Create bark detector
        detector = BarkDetector(
            threshold_db=config.bark_threshold_db,
            min_duration_ms=config.min_bark_duration_ms,
            cooldown_ms=config.cooldown_period_ms,
            sample_rate=config.sample_rate,
            chunk_size=1024
        )

        # Initialize and start capture
        capture.initialize_device()
        capture.start()

        logger.info("Listening for barks... (make loud sounds to test)")

        bark_count = 0

        # Process audio chunks
        while True:
            chunk = capture.get_audio_chunk(timeout=1.0)
            if chunk is not None:
                event = detector.process_chunk(chunk)
                if event:
                    bark_count += 1
                    logger.info(f"✓ Bark #{bark_count}: {event.peak_db:.1f} dB at {event.timestamp}")

    except KeyboardInterrupt:
        logger.info(f"\nTest stopped. Total barks detected: {bark_count}")
        capture.stop()
        sys.exit(0)

    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        capture.stop()
        sys.exit(1)
