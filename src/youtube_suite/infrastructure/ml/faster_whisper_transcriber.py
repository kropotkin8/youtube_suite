from __future__ import annotations

from pathlib import Path

from faster_whisper import WhisperModel

from youtube_suite.domain.ports import ASRSegment, TranscriptionPort


class FasterWhisperTranscriber(TranscriptionPort):
    def __init__(
        self,
        model_size: str = "medium",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "es",
    ) -> None:
        """Load the faster-whisper model and configure inference defaults.

        Args:
            model_size: Whisper model variant (e.g. ``"small"``, ``"medium"``, ``"large-v2"``).
            device: Inference device — ``"cpu"`` or ``"cuda"``.
            compute_type: Quantisation type passed to CTranslate2 (e.g. ``"int8"``, ``"float16"``).
            language: BCP-47 language code used during transcription (e.g. ``"es"``).
        """
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.language = language

    def transcribe(self, audio_path: Path) -> tuple[list[ASRSegment], str]:
        """Transcribe an audio file and return time-stamped segments plus full text.

        Args:
            audio_path: Path to the audio file to transcribe (WAV or MP3).

        Returns:
            Tuple of (list of ``ASRSegment`` objects, concatenated full transcript text).
        """
        segments_iter, _info = self.model.transcribe(
            str(audio_path),
            language=self.language,
        )
        segments: list[ASRSegment] = []
        parts: list[str] = []
        for seg in segments_iter:
            text = (seg.text or "").strip()
            if not text:
                continue
            segments.append(ASRSegment(start=float(seg.start), end=float(seg.end), text=text))
            parts.append(text)
        return segments, " ".join(parts)
