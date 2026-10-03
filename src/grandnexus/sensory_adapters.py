"""Minimal recorded-input adapters for vision and audio MVPs."""
from __future__ import annotations

from pathlib import Path

from .hardware_contracts import PerceptionEvent


class RecordedVisionAdapter:
    def observe(self, image_path: str | Path, description: str, confidence: float = 0.5) -> PerceptionEvent:
        path = Path(image_path)
        return PerceptionEvent('vision', {'path': str(path), 'description': description}, confidence, f'vision:{path.name}')


class RecordedAudioAdapter:
    def transcribe(self, audio_path: str | Path, transcript: str, confidence: float = 0.5, language: str = 'und') -> PerceptionEvent:
        path = Path(audio_path)
        return PerceptionEvent('audio', {'path': str(path), 'transcript': transcript, 'language': language}, confidence, f'audio:{path.name}')
