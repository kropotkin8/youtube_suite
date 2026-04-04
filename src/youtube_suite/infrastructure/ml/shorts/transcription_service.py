"""Servicio de transcripción usando Whisper + WhisperX"""
import whisper
import whisperx
import torch
import logging
from typing import Dict, List, Any
from pathlib import Path

from youtube_suite.config.settings import get_settings

logger = logging.getLogger(__name__)


def transcribe_with_whisperx(audio_path: str, language: str = "es") -> Dict[str, Any]:
    """
    Transcribe audio usando Whisper y refina timestamps con WhisperX
    
    Args:
        audio_path: Ruta al archivo de audio
        language: Código de idioma (es, en, etc.)
    
    Returns:
        Diccionario con transcripción y timestamps a nivel de palabra
    """
    try:
        s = get_settings()
        whisper_model = s.whisper_model
        whisperx_device = s.whisperx_device
        device = "cuda" if torch.cuda.is_available() and whisperx_device == "cuda" else "cpu"
        logger.info(f"Usando dispositivo: {device}, modelo: {whisper_model}")

        # Paso 1: Transcripción base con Whisper
        logger.info("Cargando modelo Whisper...")
        model = whisper.load_model(whisper_model, device=device)
        
        logger.info("Transcribiendo audio...")
        result = model.transcribe(
            audio_path,
            language=language,
            verbose=False
        )
        
        # Paso 2: Alineamiento forzado con WhisperX para timestamps precisos
        logger.info("Refinando timestamps con WhisperX...")
        model_a, metadata = whisperx.load_align_model(
            language_code=language,
            device=device
        )
        
        aligned_result = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio_path,
            device=device,
            return_char_alignments=False
        )
        
        # Extraer información útil
        full_text = result["text"].strip()
        segments = []
        
        for segment in aligned_result["segments"]:
            words = []
            if "words" in segment:
                for word_info in segment["words"]:
                    words.append({
                        "word": word_info.get("word", ""),
                        "start": word_info.get("start", 0.0),
                        "end": word_info.get("end", 0.0)
                    })
            
            segments.append({
                "text": segment.get("text", "").strip(),
                "start": segment.get("start", 0.0),
                "end": segment.get("end", 0.0),
                "words": words
            })
        
        return {
            "full_text": full_text,
            "segments": segments,
            "language": result.get("language", language),
            "duration": segments[-1]["end"] if segments else 0.0
        }
        
    except Exception as e:
        logger.error(f"Error en transcripción: {str(e)}")
        raise RuntimeError(f"Error en transcripción: {str(e)}")

