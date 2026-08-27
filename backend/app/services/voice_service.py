from __future__ import annotations


class VoiceService:
    def __init__(self) -> None:
        self.supported_features = ["speech_to_text", "text_to_speech", "voice_commands"]

    def transcribe(self, audio_bytes: bytes) -> str:
        return "transcribed audio placeholder"

    def synthesize(self, text: str) -> bytes:
        return text.encode("utf-8")
