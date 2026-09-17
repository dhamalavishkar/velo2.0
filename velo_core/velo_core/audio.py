import asyncio
import base64
import logging
import threading
from typing import Callable, Optional

import numpy as np
import pvporcupine
import sounddevice as sd
from faster_whisper import WhisperModel

from velo_core.config import get_settings
from velo_core.websocket.manager import manager
from velo_core.models.schemas import (
    WakeWordDetectedMessage, 
    NotchStateMessage,
    ActivationMessage,
    NotificationMessage,
    NotificationSentiment,
)

logger = logging.getLogger(__name__)


class WakeWordDetector:
    def __init__(self, access_key: str, keyword: str = "hi velo"):
        self.access_key = access_key
        self.keyword = keyword
        self.porcupine = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self, on_detected: Callable[[], None]):
        if not self.access_key:
            logger.warning("Porcupine access key not set, wake word detection disabled")
            return

        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=[self.keyword],
            )
            logger.info(f"Wake word detector initialized for: {self.keyword}")
        except Exception as e:
            logger.error(f"Failed to initialize Porcupine: {e}")
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, args=(on_detected,), daemon=True)
        self._thread.start()

    def _listen_loop(self, on_detected: Callable[[], None]):
        try:
            with sd.InputStream(
                samplerate=self.porcupine.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.porcupine.frame_length,
            ) as stream:
                while self._running:
                    pcm = stream.read(self.porcupine.frame_length)[0].flatten()
                    result = self.porcupine.process(pcm)
                    if result >= 0:
                        logger.info("Wake word detected!")
                        asyncio.run_coroutine_threadsafe(
                            self._on_wake_word(), asyncio.get_event_loop()
                        )
                        on_detected()
        except Exception as e:
            logger.error(f"Wake word listener error: {e}")

    async def _on_wake_word(self):
        await manager.broadcast(WakeWordDetectedMessage())
        await manager.broadcast(ActivationMessage(phrase="Hi Velo"))
        await manager.broadcast(NotchStateMessage(state="listening"))

    def stop(self):
        self._running = False
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None


class STTEngine:
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.model: Optional[WhisperModel] = None
        self._running = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._thread: Optional[threading.Thread] = None

    def load_model(self):
        try:
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
            )
            logger.info(f"Loaded Whisper model: {self.model_size}")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")

    def start(self, on_transcription: Callable[[str, bool], None]):
        if not self.model:
            self.load_model()
        if not self.model:
            return

        self._running = True
        self._thread = threading.Thread(target=self._process_loop, args=(on_transcription,), daemon=True)
        self._thread.start()

    def add_audio(self, audio_data: bytes):
        """Add audio chunk from WebSocket."""
        try:
            self._audio_queue.put_nowait(audio_data)
        except asyncio.QueueFull:
            pass

    def _process_loop(self, on_transcription: Callable[[str, bool], None]):
        buffer = bytearray()
        silence_threshold = 0.01
        silence_duration = 0
        max_silence = 30  # frames

        with sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype="int16",
            blocksize=512,
        ) as stream:
            while self._running:
                # Get audio from stream
                pcm = stream.read(512)[0].flatten()
                buffer.extend(pcm.tobytes())

                # Check for silence
                audio_level = np.abs(pcm).mean() / 32768.0
                if audio_level < silence_threshold:
                    silence_duration += 1
                else:
                    silence_duration = 0

                # Process when we have enough audio and silence detected
                if len(buffer) >= 16000 * 2 and silence_duration >= max_silence:
                    audio_data = bytes(buffer)
                    buffer.clear()
                    silence_duration = 0

                    # Transcribe in thread pool
                    asyncio.run_coroutine_threadsafe(
                        self._transcribe(audio_data, on_transcription),
                        asyncio.get_event_loop(),
                    )

    async def _transcribe(self, audio_data: bytes, on_transcription: Callable[[str, bool], None]):
        if not self.model:
            return

        try:
            # Convert to float32 for faster-whisper
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

            segments, info = self.model.transcribe(
                audio_np,
                language="en",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            full_text = ""
            for segment in segments:
                full_text += segment.text + " "
                # Send partial
                on_transcription(segment.text.strip(), False)

            if full_text.strip():
                on_transcription(full_text.strip(), True)

        except Exception as e:
            logger.error(f"Transcription error: {e}")

    def stop(self):
        self._running = False


class AudioDaemon:
    def __init__(self):
        self.settings = get_settings()
        self.wake_word = WakeWordDetector(
            self.settings.porcupine_access_key,
            "hi velo",
        )
        self.stt = STTEngine(self.settings.whisper_model)
        self._listening = False

    def start(self):
        self.wake_word.start(self._on_wake_word)
        self.stt.start(self._on_transcription)
        logger.info("Audio daemon started")

    def _on_wake_word(self):
        self._listening = True
        logger.info("Started listening for speech...")

    def _on_transcription(self, text: str, final: bool):
        if not self._listening and not final:
            return

        asyncio.run_coroutine_threadsafe(
            manager.broadcast(NotchStateMessage(state="expanded")),
            asyncio.get_event_loop(),
        )
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(NotchStateMessage(type="transcription", text=text, final=final)),
            asyncio.get_event_loop(),
        )

        if final and text.strip():
            # Process through agent
            from velo_core.websocket.handlers import _handler
            if _handler:
                asyncio.run_coroutine_threadsafe(
                    _handler.process_user_input(text.strip()),
                    asyncio.get_event_loop(),
                )
            self._listening = False

    def add_audio_chunk(self, audio_data: bytes):
        if self._listening:
            self.stt.add_audio(audio_data)

    def send_notification(self, summary: str, sentiment: NotificationSentiment):
        """Send a notification to the notch UI."""
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(NotificationMessage(summary=summary, sentiment=sentiment)),
            asyncio.get_event_loop(),
        )

    def stop(self):
        self.wake_word.stop()
        self.stt.stop()


audio_daemon = AudioDaemon()