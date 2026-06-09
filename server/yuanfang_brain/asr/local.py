"""Local ASR using whisper.cpp via pywhispercpp (Metal GPU acceleration)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class LocalASR:
    """ whisper.cpp ASR with Metal GPU acceleration on Mac M-series."""

    def __init__(self, model_name: str = "tiny"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        """Lazy-load the whisper model."""
        if self._model is not None:
            return self._model
        try:
            import pywhispercpp
            from pywhispercpp.model import Whisper
            model_path = self._download_model()
            self._model = Whisper(model_path)
            logger.info(f"Loaded whisper model: {self.model_name}")
            return self._model
        except ImportError:
            logger.warning("pywhispercpp not available, local ASR disabled")
            raise

    def _download_model(self) -> Path:
        """Download tiny model if not present."""
        import os
        model_dir = Path(os.path.expanduser("~/.cache/whisper"))
        model_dir.mkdir(parents=True, exist_ok=True)
        model_file = model_dir / f"{self.model_name}.bin"
        if model_file.exists():
            return model_file
        # Download via hf_hub or official whisper models
        from urllib.request import urlretrieve
        url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{self.model_name}.bin"
        logger.info(f"Downloading {self.model_name} model from {url}...")
        urlretrieve(url, model_file)
        return model_file

    async def transcribe(self, audio_pcm: bytes, sample_rate: int = 16000) -> str:
        """Transcribe PCM audio bytes to text (synchronous, runs in thread)."""
        import os
        loop = __import__("asyncio").get_running_loop()

        def _do():
            model = self._load_model()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_pcm)
                f.flush()
                fname = f.name
            try:
                result = model.transcribe(fname, language="zh")
                text = "".join([s.text for s in result]).strip()
                return text
            finally:
                os.unlink(fname)

        return await loop.run_in_executor(None, _do)

    async def transcribe_stream(
        self, audio_chunks: AsyncGenerator[bytes, None], sample_rate: int = 16000
    ) -> AsyncGenerator[str, None]:
        """Stream transcription yielding partial results as audio comes in."""
        # For streaming, accumulate chunks then transcribe when silence detected
        buffer = b""
        async for chunk in audio_chunks:
            buffer += chunk
            if len(buffer) >= sample_rate * 2:  # At least 2 seconds buffered
                text = await self.transcribe(buffer, sample_rate)
                if text:
                    yield text
                buffer = b""
