import asyncio
import logging
import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from velo_core.config import get_settings
from velo_core.websocket.manager import manager
from velo_core.models.schemas import (
    WakeWordDetectedMessage,
    NotchStateMessage,
    ActivationMessage,
    TranscriptionMessage,
    NotificationMessage,
    NotificationSentiment,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wake-Word Detector
# Uses Porcupine if access key is set, falls back to openWakeWord otherwise.
# ---------------------------------------------------------------------------

class WakeWordDetector:
    def __init__(self, access_key: str = "", keyword: str = "hi velo"):
        self.access_key = access_key.strip()
        self.keyword = keyword
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._backend: str = "none"

    def start(self, on_detected: Callable[[], None]):
        self._main_loop = asyncio.get_running_loop()

        if self.access_key:
            self._try_porcupine(on_detected)
        else:
            self._try_openwakeword(on_detected)

    # ---- Porcupine --------------------------------------------------------
    def _try_porcupine(self, on_detected: Callable[[], None]):
        try:
            import pvporcupine
            self._porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=["hi velo"],
            )
            self._backend = "porcupine"
            logger.info("Wake-word backend: Porcupine ✅")
            self._running = True
            self._thread = threading.Thread(
                target=self._porcupine_loop, args=(on_detected,), daemon=True
            )
            self._thread.start()
        except Exception as e:
            logger.warning(f"Porcupine failed ({e}), falling back to openWakeWord")
            self._try_openwakeword(on_detected)

    def _porcupine_loop(self, on_detected: Callable[[], None]):
        try:
            with sd.InputStream(
                samplerate=self._porcupine.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self._porcupine.frame_length,
            ) as stream:
                while self._running:
                    pcm = stream.read(self._porcupine.frame_length)[0].flatten()
                    result = self._porcupine.process(pcm)
                    if result >= 0:
                        logger.info("Wake word detected! (Porcupine)")
                        asyncio.run_coroutine_threadsafe(
                            self._on_wake_word(), self._main_loop
                        )
                        on_detected()
        except Exception as e:
            logger.error(f"Porcupine listener error: {e}")

    # ---- openWakeWord -----------------------------------------------------
    def _try_openwakeword(self, on_detected: Callable[[], None]):
        try:
            from openwakeword.model import Model
            self._oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
            self._backend = "openwakeword"
            logger.info("Wake-word backend: openWakeWord ✅ (using hey_jarvis as proxy for Hi Velo)")
            self._running = True
            self._thread = threading.Thread(
                target=self._oww_loop, args=(on_detected,), daemon=True
            )
            self._thread.start()
        except Exception as e:
            logger.warning(
                f"openWakeWord not available ({e}). Wake word disabled.\n"
                "  → Set PORCUPINE_ACCESS_KEY in velo_core/.env, OR\n"
                "  → Install: pip install openwakeword"
            )
            self._backend = "none"

    def _oww_loop(self, on_detected: Callable[[], None]):
        CHUNK = 1280  # 80 ms @ 16 kHz
        THRESHOLD = 0.5
        try:
            with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=CHUNK) as stream:
                while self._running:
                    pcm, _ = stream.read(CHUNK)
                    pcm_flat = pcm.flatten()
                    prediction = self._oww_model.predict(pcm_flat)
                    score = max(prediction.values()) if prediction else 0.0
                    if score > THRESHOLD:
                        logger.info(f"Wake word detected! (openWakeWord, score={score:.2f})")
                        asyncio.run_coroutine_threadsafe(
                            self._on_wake_word(), self._main_loop
                        )
                        on_detected()
                        # Brief cooldown to avoid duplicate triggers
                        import time
                        time.sleep(2.0)
        except Exception as e:
            logger.error(f"openWakeWord listener error: {e}")

    # -----------------------------------------------------------------------
    async def _on_wake_word(self):
        await manager.broadcast(WakeWordDetectedMessage())
        await manager.broadcast(ActivationMessage(phrase="Hi Velo"))
        await manager.broadcast(NotchStateMessage(state="activation"))
        # After 1.5 s show listening state
        await asyncio.sleep(1.5)
        await manager.broadcast(NotchStateMessage(state="listening"))

    def stop(self):
        self._running = False
        if hasattr(self, "_porcupine") and self._porcupine:
            self._porcupine.delete()


# ---------------------------------------------------------------------------
# STT Engine  (faster-whisper, CPU int8)
# ---------------------------------------------------------------------------

class STTEngine:
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None
        self._running = False
        self._listening = False
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    def load_model(self):
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            logger.info(f"✅ Whisper model loaded: {self.model_size}")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")

    def start(self, on_transcription: Callable[[str, bool], None]):
        if not self._model:
            self.load_model()
        if not self._model:
            logger.warning("STT engine not started — Whisper model unavailable")
            return
        self._running = True
        self._main_loop = asyncio.get_running_loop()
        self._thread = threading.Thread(
            target=self._record_loop, args=(on_transcription,), daemon=True
        )
        self._thread.start()

    def start_listening(self):
        self._listening = True
        logger.info("STT: now listening for speech...")

    def stop_listening(self):
        self._listening = False

    def _record_loop(self, on_transcription: Callable[[str, bool], None]):
        RATE = 16000
        CHUNK = 512
        SILENCE_THRESH = 0.008   # RMS threshold
        MAX_SILENCE_FRAMES = 40  # ~1.3 s of silence → end of utterance
        MIN_SPEECH_FRAMES = 8    # ignore very short blips

        buffer = bytearray()
        silence_frames = 0
        speech_frames = 0

        with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=CHUNK) as stream:
            while self._running:
                if not self._listening:
                    buffer.clear()
                    silence_frames = 0
                    speech_frames = 0
                    import time
                    time.sleep(0.05)
                    continue

                pcm, _ = stream.read(CHUNK)
                pcm_flat = pcm.flatten()
                rms = float(np.sqrt(np.mean(pcm_flat.astype(np.float32) ** 2))) / 32768.0
                buffer.extend(pcm_flat.tobytes())

                if rms > SILENCE_THRESH:
                    silence_frames = 0
                    speech_frames += 1
                else:
                    silence_frames += 1

                # Transcribe when we detect end-of-utterance
                if silence_frames >= MAX_SILENCE_FRAMES and speech_frames >= MIN_SPEECH_FRAMES:
                    audio_data = bytes(buffer)
                    buffer.clear()
                    silence_frames = 0
                    speech_frames = 0
                    asyncio.run_coroutine_threadsafe(
                        self._transcribe(audio_data, on_transcription), self._main_loop
                    )

    async def _transcribe(self, audio_data: bytes, on_transcription: Callable[[str, bool], None]):
        if not self._model:
            return
        try:
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _ = self._model.transcribe(
                audio_np,
                language="en",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400),
            )
            full_text = ""
            for segment in segments:
                seg_text = segment.text.strip()
                if seg_text:
                    full_text += seg_text + " "
                    on_transcription(seg_text, False)

            if full_text.strip():
                on_transcription(full_text.strip(), True)
        except Exception as e:
            logger.error(f"Transcription error: {e}")

    def stop(self):
        self._running = False
        self._listening = False


# ---------------------------------------------------------------------------
# Audio Daemon  (orchestrates wake-word + STT)
# ---------------------------------------------------------------------------

class AudioDaemon:
    def __init__(self):
        self.settings = get_settings()
        self.wake_word = WakeWordDetector(
            access_key=self.settings.porcupine_access_key,
            keyword="hi velo",
        )
        self.stt = STTEngine(self.settings.whisper_model)
        self._listening = False
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self):
        self._main_loop = asyncio.get_running_loop()
        self.wake_word.start(self._on_wake_word)
        self.stt.start(self._on_transcription)
        logger.info("✅ Audio daemon started")

    def _on_wake_word(self):
        """Called from wake-word thread when activation phrase detected."""
        self._listening = True
        self.stt.start_listening()

    def _on_transcription(self, text: str, final: bool):
        """Called from STT thread with partial / final transcription text."""
        if not text:
            return

        # Broadcast transcription to UI
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(TranscriptionMessage(text=text, final=final)),
            self._main_loop,
        )

        if final:
            self.stt.stop_listening()
            self._listening = False
            text_clean = text.strip()
            if text_clean:
                from velo_core.websocket.handlers import _handler
                if _handler:
                    asyncio.run_coroutine_threadsafe(
                        _handler.process_user_input(text_clean),
                        self._main_loop,
                    )

    def send_notification(self, summary: str, sentiment: NotificationSentiment):
        """Push a notification card to the notch UI."""
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(NotificationMessage(summary=summary, sentiment=sentiment)),
            self._main_loop,
        )

    def stop(self):
        self.wake_word.stop()
        self.stt.stop()
        logger.info("Audio daemon stopped")


audio_daemon = AudioDaemon()