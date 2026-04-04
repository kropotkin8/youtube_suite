"""Servicio de diarizaci?n usando pyannote.audio"""
import logging
from typing import Dict, List, Any, Optional
from pyannote.audio import Pipeline
import torch

from youtube_suite.config.settings import get_settings

logger = logging.getLogger(__name__)

# Pipeline global (se carga una vez)
_diarization_pipeline: Optional[Pipeline] = None


def get_diarization_pipeline() -> Pipeline:
    """Obtiene o crea el pipeline de diarizaci?n (singleton)"""
    global _diarization_pipeline
    
    if _diarization_pipeline is None:
        s = get_settings()
        if not s.hf_token:
            raise ValueError(
                "HF_TOKEN no configurado. "
                "Configura tu token de Hugging Face en el archivo .env o como variable de entorno."
            )

        device = "cuda" if torch.cuda.is_available() and s.diarization_device == "cuda" else "cpu"
        logger.info(f"Cargando pipeline de diarizaci?n en {device}...")

        try:
            _diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=s.hf_token,
            )
            _diarization_pipeline.to(torch.device(device))
            logger.info("Pipeline de diarizaci?n cargado exitosamente")
        except Exception as e:
            logger.error(f"Error al cargar pipeline de diarizaci?n: {str(e)}")
            raise
    
    return _diarization_pipeline


def diarize_audio(audio_path: str) -> List[Dict[str, Any]]:
    """
    Identifica qui?n habla cu?ndo en el audio
    
    Args:
        audio_path: Ruta al archivo de audio
    
    Returns:
        Lista de segmentos con informaci?n de locutor
        Cada segmento tiene: start, end, speaker
    """
    try:
        if not get_settings().hf_token:
            logger.warning("HF_TOKEN no configurado, saltando diarizaci?n")
            return []
        
        pipeline = get_diarization_pipeline()
        
        logger.info("Ejecutando diarizaci?n...")
        diarization = pipeline(audio_path)
        
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "start": turn.start,
                "end": turn.end,
                "speaker": speaker
            })
        
        logger.info(f"Diarizaci?n completada: {len(segments)} segmentos, {len(set(s['speaker'] for s in segments))} locutores")
        return segments
        
    except Exception as e:
        logger.error(f"Error en diarizaci?n: {str(e)}")
        # No fallar completamente si la diarizaci?n falla
        logger.warning("Continuando sin informaci?n de diarizaci?n")
        return []


def assign_speakers_to_segments(
    transcription_segments: List[Dict[str, Any]],
    diarization_segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Asigna informaci?n de locutor a los segmentos de transcripci?n
    
    Args:
        transcription_segments: Segmentos de transcripci?n con timestamps
        diarization_segments: Segmentos de diarizaci?n con informaci?n de locutor
    
    Returns:
        Segmentos de transcripci?n con informaci?n de locutor asignada
    """
    if not diarization_segments:
        return transcription_segments
    
    # Crear un mapeo temporal de timestamps a speakers
    speaker_map = {}
    for diar_seg in diarization_segments:
        start = diar_seg["start"]
        end = diar_seg["end"]
        speaker = diar_seg["speaker"]
        
        # Asignar speaker a cada segundo (aproximaci?n simple)
        for t in range(int(start), int(end) + 1):
            speaker_map[t] = speaker
    
    # Asignar speaker a cada segmento de transcripci?n
    for seg in transcription_segments:
        # Usar el timestamp medio del segmento
        mid_time = int((seg["start"] + seg["end"]) / 2)
        if mid_time in speaker_map:
            seg["speaker"] = speaker_map[mid_time]
        
        # Tambi?n asignar a palabras si existen
        if "words" in seg and seg["words"]:
            for word in seg["words"]:
                word_time = int((word["start"] + word["end"]) / 2)
                if word_time in speaker_map:
                    word["speaker"] = speaker_map[word_time]
    
    return transcription_segments

