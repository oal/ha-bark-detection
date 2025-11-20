# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Audio capture module for bark detection.

Handles audio device enumeration, USB microphone detection,
and continuous audio stream capture using sounddevice.
"""

import logging
import time
from typing import Optional, Callable
import sounddevice as sd
import numpy as np
from queue import Queue, Empty


logger = logging.getLogger(__name__)


class AudioDeviceError(Exception):
    """Raised when audio device initialization or capture fails."""
    pass


class AudioCapture:
    """
    Manages audio capture from USB microphone.

    Handles device detection, stream setup, and continuous audio capture
    with automatic error recovery.
    """

    def __init__(
        self,
        device_id: str,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        channels: int = 1
    ):
        """
        Initialize audio capture.

        Args:
            device_id: USB device ID (e.g., "0d8c:0005" for Blue Snowball)
            sample_rate: Audio sample rate in Hz (default: 16000)
            chunk_size: Number of samples per chunk (default: 1024)
            channels: Number of audio channels (default: 1 for mono)
        """
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.device_index: Optional[int] = None
        self.stream: Optional[sd.InputStream] = None
        self.audio_queue: Queue = Queue(maxsize=100)
        self._running = False

    def find_device(self) -> Optional[int]:
        """
        Find audio device by USB ID.

        Returns:
            Device index if found, None otherwise
        """
        try:
            devices = sd.query_devices()
            logger.debug(f"Available audio devices: {len(devices)}")

            for idx, device in enumerate(devices):
                logger.debug(f"  [{idx}] {device['name']}: "
                           f"in={device['max_input_channels']}, "
                           f"out={device['max_output_channels']}")

                # Check if device name contains USB ID or is an input device
                device_name = device['name'].lower()
                if (self.device_id.lower() in device_name or
                    'blue' in device_name and 'snowball' in device_name):
                    if device['max_input_channels'] > 0:
                        logger.info(f"Found target device: [{idx}] {device['name']}")
                        return idx

            logger.warning(
                f"USB device {self.device_id} not found. "
                f"Available devices: {len(devices)}"
            )
            return None

        except Exception as e:
            logger.error(f"Error querying audio devices: {e}")
            return None

    def get_default_input_device(self) -> Optional[int]:
        """
        Get default input device as fallback.

        Returns:
            Default input device index if available, None otherwise
        """
        try:
            default_device = sd.default.device[0]  # Input device
            if default_device is not None:
                device_info = sd.query_devices(default_device)
                logger.warning(
                    f"Using default input device as fallback: "
                    f"[{default_device}] {device_info['name']}"
                )
                return default_device
            return None
        except Exception as e:
            logger.error(f"Error getting default device: {e}")
            return None

    def initialize_device(self, retry_count: int = 3, retry_delay: float = 2.0):
        """
        Initialize audio device with retries.

        Args:
            retry_count: Number of retry attempts
            retry_delay: Delay between retries in seconds

        Raises:
            AudioDeviceError: If device initialization fails after retries
        """
        for attempt in range(retry_count):
            logger.info(f"Initializing audio device (attempt {attempt + 1}/{retry_count})...")

            # Try to find target device
            self.device_index = self.find_device()

            # Fall back to default if target not found
            if self.device_index is None:
                self.device_index = self.get_default_input_device()

            if self.device_index is not None:
                # Verify device capabilities
                try:
                    device_info = sd.query_devices(self.device_index)
                    logger.info(f"Selected device: {device_info['name']}")
                    logger.info(f"  Sample rate: {self.sample_rate} Hz")
                    logger.info(f"  Channels: {self.channels}")
                    logger.info(f"  Chunk size: {self.chunk_size} samples "
                              f"({self.chunk_size / self.sample_rate * 1000:.1f} ms)")
                    return
                except Exception as e:
                    logger.error(f"Error querying device {self.device_index}: {e}")
                    self.device_index = None

            if attempt < retry_count - 1:
                logger.warning(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)

        raise AudioDeviceError(
            f"Failed to initialize audio device after {retry_count} attempts. "
            f"Please ensure a microphone is connected and accessible."
        )

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info,
        status: sd.CallbackFlags
    ):
        """
        Callback for audio stream processing.

        Called by sounddevice for each audio chunk.

        Args:
            indata: Audio data as numpy array
            frames: Number of frames
            time_info: Timing information
            status: Status flags
        """
        if status:
            if status.input_overflow:
                logger.warning("Audio buffer overflow - some audio may be lost")
            else:
                logger.warning(f"Audio callback status: {status}")

        # Copy audio data to queue for processing
        try:
            # Convert to float32 and flatten to 1D if needed
            audio_chunk = indata.copy().flatten()
            self.audio_queue.put_nowait(audio_chunk)
        except Exception as e:
            logger.error(f"Error in audio callback: {e}")

    def start(self):
        """
        Start audio capture stream.

        Raises:
            AudioDeviceError: If stream cannot be started
        """
        if self._running:
            logger.warning("Audio capture already running")
            return

        if self.device_index is None:
            raise AudioDeviceError("Device not initialized. Call initialize_device() first.")

        try:
            self.stream = sd.InputStream(
                device=self.device_index,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                callback=self._audio_callback,
                dtype='float32'
            )
            self.stream.start()
            self._running = True
            logger.info("Audio capture started")

        except Exception as e:
            raise AudioDeviceError(f"Failed to start audio stream: {e}")

    def stop(self):
        """Stop audio capture stream."""
        if not self._running:
            return

        self._running = False

        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                logger.info("Audio capture stopped")
            except Exception as e:
                logger.error(f"Error stopping audio stream: {e}")
            finally:
                self.stream = None

    def get_audio_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        Get next audio chunk from queue.

        Args:
            timeout: Timeout in seconds to wait for chunk

        Returns:
            Audio chunk as numpy array, or None if timeout
        """
        try:
            return self.audio_queue.get(timeout=timeout)
        except Empty:
            return None

    def is_running(self) -> bool:
        """Check if audio capture is running."""
        return self._running

    def __enter__(self):
        """Context manager entry."""
        self.initialize_device()
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Module test functionality
if __name__ == "__main__":
    """Test audio capture functionality."""
    import sys

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    logger.info("Testing audio capture...")
    logger.info("Press Ctrl+C to stop")

    try:
        # Load config for sample rate
        from bark_detector.config import Config
        config = Config()

        # Create audio capture instance
        capture = AudioCapture(
            device_id=config.microphone_device_id,
            sample_rate=config.sample_rate,
            chunk_size=1024
        )

        # Initialize device
        capture.initialize_device()

        # Start capture
        capture.start()

        # Capture for 10 seconds
        logger.info("Capturing audio for 10 seconds...")
        chunks_received = 0
        start_time = time.time()

        while time.time() - start_time < 10.0:
            chunk = capture.get_audio_chunk(timeout=0.5)
            if chunk is not None:
                chunks_received += 1
                # Calculate RMS level for monitoring
                rms = np.sqrt(np.mean(chunk ** 2))
                db = 20 * np.log10(rms + 1e-10)  # Add small value to avoid log(0)
                logger.info(f"Chunk {chunks_received}: {len(chunk)} samples, "
                          f"RMS={rms:.6f}, dB={db:.1f}")

        logger.info(f"✓ Received {chunks_received} audio chunks")
        logger.info(f"✓ Average rate: {chunks_received / 10:.1f} chunks/second")

        # Stop capture
        capture.stop()

        logger.info("✓ Audio capture test completed successfully")

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        capture.stop()
        sys.exit(0)

    except Exception as e:
        logger.error(f"✗ Audio capture test failed: {e}", exc_info=True)
        sys.exit(1)
